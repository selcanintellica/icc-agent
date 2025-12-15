"""
Rule Repository.

Handles saving rules to ICC API following the same patterns as job_repository.py
"""

import os
import logging
from typing import Dict, Any, Optional

import httpx

from src.models.rule import RulePayload
from src.utils.retry import retry, RetryPresets, RetryExhaustedError
from src.errors import (
    ICCBaseError,
    HTTPError,
    NetworkTimeoutError,
    APIUnavailableError,
    AuthenticationError,
    JobCreationFailedError,
    DuplicateJobNameError,
    ErrorCode,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


class RuleRepository:
    """
    Repository for saving Rules to ICC API.
    
    Follows the same patterns as JobRepository:
    - Uses httpx AsyncClient
    - Handles authentication
    - Structured error handling with retry
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ):
        """
        Initialize Rule repository.
        
        Args:
            base_url: Base URL for ICC API
            auth_headers: Authentication headers
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("ICC_API_BASE_URL", "https://172.16.22.13:8084")
        self.auth_headers = auth_headers or {}
        self.timeout = timeout
    
    async def save_rule(self, payload: RulePayload) -> Dict[str, Any]:
        """
        Save a rule to ICC.
        
        Args:
            payload: RulePayload to save
            
        Returns:
            Dict with:
            - message: "Success" or "Error"
            - rule_id: ID of created rule (on success)
            - error: Error message (on failure)
            
        Raises:
            DuplicateJobNameError: If rule name already exists
            NetworkTimeoutError: If request times out
            APIUnavailableError: If API is unavailable
            JobCreationFailedError: If rule creation fails
        """
        endpoint = f"{self.base_url}/rule/save"
        rule_name = payload.props.name
        
        logger.info(f"Saving rule '{rule_name}' to: {endpoint}")
        logger.debug(f"Rule payload: {payload.to_api_payload()}")
        
        try:
            return await self._save_rule_with_retry(endpoint, payload)
        except RetryExhaustedError as e:
            logger.error(f"Failed to save rule after retries: {e.last_exception}")
            raise APIUnavailableError(
                message=f"Failed to save rule: {e.last_exception}",
                user_message="Unable to save the rule. Please try again later.",
                service_name="Rule API",
                cause=e.last_exception
            )
    
    @retry(config=RetryPresets.API_CALL)
    async def _save_rule_with_retry(
        self,
        endpoint: str,
        payload: RulePayload
    ) -> Dict[str, Any]:
        """Save rule with automatic retry for transient failures."""
        logger.info("[RULE_DEBUG] >>> Entering _save_rule_with_retry")
        try:
            async with httpx.AsyncClient(
                headers=self.auth_headers,
                verify=False,
                timeout=self.timeout
            ) as client:
                logger.info("[RULE_DEBUG] Sending POST request...")
                resp = await client.post(
                    endpoint,
                    json=payload.to_api_payload()
                )
                
                logger.info(f"[RULE_DEBUG] Response received - status: {resp.status_code}")
                logger.info(f"[RULE_DEBUG] Response text (first 200 chars): {resp.text[:200]}")
                
                # Handle authentication errors
                if resp.status_code == 401 or resp.status_code == 403:
                    logger.info("[RULE_DEBUG] Auth error detected")
                    raise AuthenticationError(
                        error_code=ErrorCode.AUTH_FAILED,
                        message=f"Authentication failed when saving rule: {resp.status_code}",
                        user_message="Authentication failed. Please refresh and try again."
                    )
                
                # Handle server errors (retry)
                if resp.status_code >= 500:
                    logger.info("[RULE_DEBUG] Server error detected")
                    raise APIUnavailableError(
                        message=f"Server error {resp.status_code} when saving rule",
                        user_message="The server is temporarily unavailable."
                    )
                
                # Parse response
                logger.info("[RULE_DEBUG] Parsing response...")
                try:
                    data = resp.json()
                    logger.info(f"[RULE_DEBUG] JSON parsed successfully, type: {type(data).__name__}")
                except Exception as json_err:
                    logger.info(f"[RULE_DEBUG] JSON parse failed ({json_err}), using raw text")
                    data = resp.text
                
                logger.info(f"[RULE_DEBUG] Data type: {type(data).__name__}, value: {str(data)[:100]}")
                
                # Check for success FIRST if status is 200
                if resp.status_code == 200:
                    logger.info("[RULE_DEBUG] Status 200 - extracting rule ID...")
                    # Extract rule ID from response based on type
                    rule_id = None
                    if isinstance(data, dict):
                        logger.info("[RULE_DEBUG] Data is dict, extracting id...")
                        # First try direct "id" field
                        rule_id = data.get("id")
                        if not rule_id:
                            # Then check "object" field - it might be the ID directly (string)
                            # or a nested dict with an "id" field
                            obj = data.get("object")
                            if isinstance(obj, str):
                                # "object" contains the rule ID directly
                                rule_id = obj
                            elif isinstance(obj, dict):
                                # "object" is a nested dict with "id"
                                rule_id = obj.get("id")
                    elif isinstance(data, str):
                        logger.info("[RULE_DEBUG] Data is string, using as rule ID...")
                        # API returns just the rule ID as a string
                        stripped = data.strip()
                        rule_id = stripped if stripped else None
                    elif isinstance(data, (int, float)):
                        logger.info("[RULE_DEBUG] Data is number, converting to string...")
                        # API might return numeric ID directly
                        rule_id = str(int(data))
                    else:
                        logger.info(f"[RULE_DEBUG] Unexpected data type: {type(data)}")
                    
                    logger.info(f"[RULE_DEBUG] Extracted rule_id: {rule_id}")
                    logger.info(f"[RULE_DEBUG] <<< Returning success for rule '{payload.props.name}'")
                    return {
                        "message": "Success",
                        "rule_id": rule_id,
                        "data": data
                    }
                
                # Handle error responses (non-200 status codes)
                logger.info(f"[RULE_DEBUG] Non-200 status ({resp.status_code}), handling error...")
                error_message = ""
                if isinstance(data, dict):
                    logger.info("[RULE_DEBUG] Extracting error from dict...")
                    error_message = data.get("errorMessage") or data.get("error") or ""
                elif isinstance(data, str):
                    logger.info("[RULE_DEBUG] Using string response as error message...")
                    error_message = data
                
                logger.info(f"[RULE_DEBUG] Error message: {error_message[:100] if error_message else 'empty'}")
                
                # Check for duplicate name error
                error_lower = error_message.lower() if error_message else ""
                if "already exists" in error_lower or "duplicate" in error_lower or "same name" in error_lower:
                    logger.info("[RULE_DEBUG] Duplicate name error detected")
                    raise DuplicateJobNameError(
                        job_name=payload.props.name,
                        message=f"Rule name already exists: {payload.props.name}",
                        user_message=f"A rule named '{payload.props.name}' already exists. Please choose a different name."
                    )
                
                # Other error (non-200 status code without duplicate name)
                error_msg = error_message or f"HTTP {resp.status_code}"
                logger.error(f"[RULE_DEBUG] Rule save failed: {error_msg}")
                raise JobCreationFailedError(
                    job_type="Rule",
                    message=f"Failed to save rule: {error_msg}",
                    user_message=f"Failed to create rule: {error_msg}"
                )
                    
        except httpx.TimeoutException as e:
            logger.error(f"Timeout saving rule: {e}")
            raise NetworkTimeoutError(
                message="Timeout saving rule",
                user_message="Connection to the server timed out. Please try again.",
                cause=e
            )
        except httpx.ConnectError as e:
            logger.error(f"Connection error saving rule: {e}")
            raise APIUnavailableError(
                message=f"Could not connect to save rule: {e}",
                user_message="Unable to connect to the server. Please check your connection.",
                cause=e
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error saving rule: {e.response.status_code}")
            raise HTTPError(
                message=f"HTTP {e.response.status_code} when saving rule",
                user_message="Failed to save rule. Please try again.",
                status_code=e.response.status_code,
                cause=e
            )
        except (DuplicateJobNameError, JobCreationFailedError, AuthenticationError, APIUnavailableError, NetworkTimeoutError, HTTPError):
            # Re-raise known ICC errors
            raise
        except Exception as e:
            # Catch-all for unexpected errors (like AttributeError)
            logger.error(f"[RULE_DEBUG] UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[RULE_DEBUG] Traceback:\n{traceback.format_exc()}")
            raise JobCreationFailedError(
                job_type="Rule",
                message=f"Unexpected error: {type(e).__name__}: {str(e)}",
                user_message=f"An unexpected error occurred while saving the rule. Please try again."
            )


async def save_rule(
    payload: RulePayload,
    auth_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to save a rule.
    
    Args:
        payload: RulePayload to save
        auth_headers: Optional authentication headers
        
    Returns:
        Result dictionary with message, rule_id, and data
    """
    repo = RuleRepository(auth_headers=auth_headers)
    return await repo.save_rule(payload)


if __name__ == "__main__":
    """Test script for Rule repository."""
    import asyncio
    from src.utils.auth import authenticate
    from src.models.rule import RuleBuilder
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_rule_save():
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
        
        # Create test jobs (these would be real job IDs in production)
        test_jobs = [
            {"id": "123456789", "name": "TestReadSQL", "type": "read_sql", "folder": "3023602439587835"},
            {"id": "987654321", "name": "TestSendEmail", "type": "send_email", "folder": "3023602439587835"}
        ]
        
        # Build rule payload
        try:
            payload = RuleBuilder.build(
                jobs=test_jobs,
                folder_id="3023602439587835",
                rule_name="TestRule_" + str(int(asyncio.get_event_loop().time()))
            )
            
            print(f"\nBuilt rule payload:")
            print(f"  Name: {payload.props.name}")
            print(f"  Folder: {payload.folder}")
            print(f"  Detail: {payload.detail[:100]}...")
            
            # Uncomment to actually save (needs real job IDs)
            # repo = RuleRepository(auth_headers=auth_headers)
            # result = await repo.save_rule(payload)
            # print(f"\nSave result: {result}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    asyncio.run(test_rule_save())



