"""
Authentication Service.

Handles authentication operations following Single Responsibility Principle.
"""

from typing import Optional, Tuple
import logging

from src.utils.auth import authenticate

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Service for handling authentication.
    
    Following SRP - only responsible for authentication operations.
    """
    
    def __init__(self):
        """Initialize authentication service."""
        self._cached_auth: Optional[Tuple[str, str]] = None
    
    async def get_auth_credentials(self, use_cache: bool = True) -> Optional[Tuple[str, str]]:
        """
        Get authentication credentials (userpass, token).
        
        Args:
            use_cache: Whether to use cached credentials if available
            
        Returns:
            Tuple of (userpass, token) or None if authentication fails
        """
        if use_cache and self._cached_auth:
            logger.debug("Using cached authentication credentials")
            return self._cached_auth
        
        logger.info("Authenticating...")
        auth_result = await authenticate()
        
        if auth_result:
            self._cached_auth = auth_result
            logger.info("Authentication successful")
            return auth_result
        else:
            logger.warning("Authentication failed")
            return None
    
    def clear_cache(self) -> None:
        """Clear cached authentication credentials."""
        self._cached_auth = None
        logger.debug("Authentication cache cleared")
    
    async def get_auth_headers(self, use_cache: bool = True) -> dict:
        """
        Get HTTP headers with authentication.

        Args:
            use_cache: Whether to use cached credentials if available

        Returns:
            Dictionary of headers with Authorization and TokenKey
        """
        auth_result = await self.get_auth_credentials(use_cache)

        if auth_result:
            userpass, token = auth_result
            return {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
        else:
            logger.warning("No authentication credentials available, returning empty headers")
            return {}

    async def populate_memory_connections(self, memory) -> bool:
        """
        Populate memory with connections from API.

        Extracted from app.py invoke_router_async function.

        Args:
            memory: Memory object to populate with connections

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Attempting to fetch connections from API")

            # Get auth headers
            auth_headers = await self.get_auth_headers()
            if not auth_headers:
                logger.warning("Cannot populate connections without authentication")
                return False

            # Import here to avoid circular dependencies
            from src.api_clients.connection_api_client import ICCAPIClient
            from src.api_clients.table_api_client import set_table_api_auth

            # Set auth for table API
            set_table_api_auth(auth_headers)

            # Fetch connections
            api_client = ICCAPIClient(auth_headers=auth_headers)
            connections = await api_client.fetch_connections()

            if connections:
                logger.info(f"Fetched {len(connections)} connections from API")
                # Populate memory
                memory.connection_manager.available_connections = connections
                logger.info("Successfully populated memory with API connections")
                return True
            else:
                logger.warning("No connections returned from API")
                return False

        except Exception as e:
            logger.error(f"Error populating connections from API: {e}")
            logger.info("Falling back to static configuration")
            return False


# Singleton instance for convenience
_auth_service_instance: Optional[AuthenticationService] = None


def get_auth_service() -> AuthenticationService:
    """
    Get singleton instance of AuthenticationService.
    
    Returns:
        AuthenticationService: Singleton instance
    """
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthenticationService()
    return _auth_service_instance
