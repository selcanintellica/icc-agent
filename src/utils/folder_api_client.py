"""
Folder API Client.

Fetches available folders from ICC API for rule saving.
Follows the same patterns as connection_api_client.py
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

from src.utils.auth import authenticate
from src.utils.retry import retry, RetryPresets, RetryExhaustedError
from src.errors import (
    ICCConnectionError,
    HTTPError,
    NetworkTimeoutError,
    APIUnavailableError,
    AuthenticationError,
    ErrorCode,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


class FolderAPIClient:
    """
    Client for ICC Folder API operations with authentication and retry support.
    
    Provides:
    - Folder list fetching for rule saving
    - Automatic retry for transient failures
    - Structured error handling
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        """
        Initialize Folder API client.
        
        Args:
            base_url: Base URL for ICC API (e.g., https://172.16.22.13:8084)
            auth_headers: Optional authentication headers (Authorization and TokenKey)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("ICC_API_BASE_URL", "https://172.16.22.13:8084")
        self.auth_headers = auth_headers or {}
        self.timeout = timeout
    
    async def fetch_folders(self) -> List[Dict[str, str]]:
        """
        Fetch all available folders from ICC API.
        
        Returns:
            List of folder dictionaries:
            [
                {"id": "3023602439587835", "name": "ALL_TEMPLATES_TEST"},
                {"id": "498360417702319", "name": "DEMO"},
                ...
            ]
            
        Raises:
            NetworkTimeoutError: If request times out
            APIUnavailableError: If API is unavailable
            HTTPError: For other HTTP errors
        """
        endpoint = f"{self.base_url}/folder/explore"
        logger.info(f"Fetching folders from: {endpoint}")
        
        try:
            return await self._fetch_folders_with_retry(endpoint)
        except RetryExhaustedError as e:
            logger.error(f"Failed to fetch folders after retries: {e.last_exception}")
            raise APIUnavailableError(
                message=f"Failed to fetch folders: {e.last_exception}",
                user_message="Unable to retrieve available folders. Please try again later.",
                service_name="Folder API",
                cause=e.last_exception
            )
    
    @retry(config=RetryPresets.API_CALL)
    async def _fetch_folders_with_retry(self, endpoint: str) -> List[Dict[str, str]]:
        """Fetch folders with automatic retry."""
        try:
            async with httpx.AsyncClient(
                headers=self.auth_headers,
                verify=False,
                timeout=self.timeout
            ) as client:
                resp = await client.get(endpoint)
                
                if resp.status_code == 401 or resp.status_code == 403:
                    raise AuthenticationError(
                        error_code=ErrorCode.AUTH_FAILED,
                        message=f"Authentication failed when fetching folders: {resp.status_code}",
                        user_message="Authentication failed. Please refresh and try again."
                    )
                
                if resp.status_code >= 500:
                    raise APIUnavailableError(
                        message=f"Server error {resp.status_code} when fetching folders",
                        user_message="The server is temporarily unavailable."
                    )
                
                resp.raise_for_status()
                data = resp.json()
                
                objects = data.get('object', [])
                logger.info(f"Fetched {len(objects)} folders")
                
                return self._map_folders(objects)
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching folders: {e}")
            raise NetworkTimeoutError(
                message="Timeout fetching folders",
                user_message="Connection to the server timed out. Please try again.",
                cause=e
            )
        except httpx.ConnectError as e:
            logger.error(f"Connection error fetching folders: {e}")
            raise APIUnavailableError(
                message=f"Could not connect to fetch folders: {e}",
                user_message="Unable to connect to the server. Please check your connection.",
                cause=e
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching folders: {e.response.status_code}")
            raise HTTPError(
                message=f"HTTP {e.response.status_code} when fetching folders",
                user_message="Failed to retrieve folders. Please try again.",
                status_code=e.response.status_code,
                cause=e
            )
    
    def _map_folders(self, objects: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Map raw folder objects to simplified format.
        
        Args:
            objects: Raw folder objects from API
            
        Returns:
            List of {id, name} dictionaries
        """
        result: List[Dict[str, str]] = []
        
        for obj in objects:
            folder_id = obj.get("id")
            props = obj.get("props") or {}
            name = props.get("name")
            
            if folder_id and name:
                result.append({
                    "id": str(folder_id),
                    "name": name
                })
            else:
                logger.debug(f"Skipping folder with missing id or name: {obj}")
        
        # Sort by name for consistent display
        result.sort(key=lambda x: x["name"].lower())
        
        logger.info(f"Mapped {len(result)} valid folders")
        return result


async def fetch_folders(
    auth_headers: Optional[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    """
    Convenience function to fetch folders.
    
    Args:
        auth_headers: Optional authentication headers
        
    Returns:
        List of folder dictionaries (empty list on error)
    """
    try:
        client = FolderAPIClient(auth_headers=auth_headers)
        folders = await client.fetch_folders()
        return folders
    except AuthenticationError as e:
        logger.error(f"Authentication failed while fetching folders: {e}")
        return []
    except ICCConnectionError as e:
        logger.error(f"Connection error while fetching folders: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch folders: {type(e).__name__}: {e}", exc_info=True)
        return []


def format_folders_for_display(folders: List[Dict[str, str]]) -> str:
    """
    Format folders as a numbered list for user display.
    
    Args:
        folders: List of folder dictionaries
        
    Returns:
        Formatted string with numbered folders
    """
    if not folders:
        return "No folders available."
    
    lines = ["Select a folder to save the rule:"]
    for i, folder in enumerate(folders, 1):
        lines.append(f"  {i}. {folder['name']}")
    
    return "\n".join(lines)


def get_folder_by_selection(
    folders: List[Dict[str, str]],
    selection: str
) -> Optional[Dict[str, str]]:
    """
    Get folder by user selection (number or name).
    
    Args:
        folders: List of folder dictionaries
        selection: User's selection (1-based index or folder name)
        
    Returns:
        Folder dictionary if found, None otherwise
    """
    selection = selection.strip()
    
    # Try as number first
    if selection.isdigit():
        index = int(selection) - 1
        if 0 <= index < len(folders):
            return folders[index]
    
    # Try as name (case-insensitive)
    selection_lower = selection.lower()
    for folder in folders:
        if folder["name"].lower() == selection_lower:
            return folder
    
    # Try partial match
    for folder in folders:
        if selection_lower in folder["name"].lower():
            return folder
    
    return None


if __name__ == "__main__":
    """Test script for Folder API client."""
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_api():
        # Get authentication
        try:
            auth_result = await authenticate()
            if not auth_result:
                print("Authentication failed")
                return
            
            userpass, token = auth_result
            auth_headers = {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
        except Exception as e:
            print(f"Authentication failed: {e}")
            return
        
        client = FolderAPIClient(auth_headers=auth_headers)
        
        print("\nTesting folder fetch...")
        try:
            folders = await client.fetch_folders()
            print(f"Fetched {len(folders)} folders")
            
            # Display first 10
            print("\nFirst 10 folders:")
            for folder in folders[:10]:
                print(f"  - {folder['name']} (ID: {folder['id']})")
            
            # Test display formatting
            print("\n" + format_folders_for_display(folders[:5]))
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    asyncio.run(test_api())



