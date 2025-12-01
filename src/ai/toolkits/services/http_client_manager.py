"""
HTTP Client Manager.

Manages HTTP client creation and configuration following Single Responsibility Principle.
"""

from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging

from httpx import AsyncClient

from .auth_service import AuthenticationService, get_auth_service

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    Manages HTTP client creation with authentication.
    
    Following SRP - only responsible for HTTP client management.
    """
    
    def __init__(self, auth_service: Optional[AuthenticationService] = None):
        """
        Initialize HTTP client manager.
        
        Args:
            auth_service: Authentication service (uses singleton if None)
        """
        self.auth_service = auth_service or get_auth_service()
    
    @asynccontextmanager
    async def get_authenticated_client(
        self,
        verify: bool = False,
        use_auth_cache: bool = True,
        **client_kwargs: Any
    ):
        """
        Get an authenticated AsyncClient as async context manager.
        
        Args:
            verify: Whether to verify SSL certificates
            use_auth_cache: Whether to use cached auth credentials
            **client_kwargs: Additional kwargs for AsyncClient
            
        Yields:
            AsyncClient: Configured HTTP client with authentication
            
        Example:
            async with manager.get_authenticated_client() as client:
                response = await client.get("https://api.example.com")
        """
        headers = await self.auth_service.get_auth_headers(use_auth_cache)
        
        # Merge provided headers with auth headers
        if "headers" in client_kwargs:
            headers.update(client_kwargs.pop("headers"))
        
        logger.debug(f"Creating HTTP client with verify={verify}")
        
        async with AsyncClient(
            headers=headers,
            verify=verify,
            **client_kwargs
        ) as client:
            yield client
    
    async def create_client(
        self,
        verify: bool = False,
        use_auth_cache: bool = True,
        **client_kwargs: Any
    ) -> AsyncClient:
        """
        Create an authenticated AsyncClient (caller must close it).
        
        Args:
            verify: Whether to verify SSL certificates
            use_auth_cache: Whether to use cached auth credentials
            **client_kwargs: Additional kwargs for AsyncClient
            
        Returns:
            AsyncClient: Configured HTTP client with authentication
            
        Note:
            Caller is responsible for closing the client.
            Prefer using get_authenticated_client() context manager.
        """
        headers = await self.auth_service.get_auth_headers(use_auth_cache)
        
        # Merge provided headers with auth headers
        if "headers" in client_kwargs:
            headers.update(client_kwargs.pop("headers"))
        
        return AsyncClient(
            headers=headers,
            verify=verify,
            **client_kwargs
        )


# Factory function for backward compatibility
def create_http_client_manager(
    auth_service: Optional[AuthenticationService] = None
) -> HTTPClientManager:
    """
    Create an HTTPClientManager instance.
    
    Args:
        auth_service: Optional authentication service
        
    Returns:
        HTTPClientManager: Configured manager
    """
    return HTTPClientManager(auth_service)
