"""
Authentication utilities for API access with retry and error handling.
"""

import logging
from typing import Optional, Tuple

import httpx

from src.utils.config import AUTH_CONFIG
from src.utils.retry import retry, RetryPresets, RetryExhaustedError
from src.errors import (
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError,
    NoCredentialsError,
    NetworkTimeoutError,
    APIUnavailableError,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Service for handling authentication with the ICC API.
    
    Provides:
    - Token-based authentication
    - Retry logic for transient failures
    - Structured error handling
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize authentication service.
        
        Args:
            config: Authentication configuration (uses AUTH_CONFIG if None)
        """
        self.config = config or AUTH_CONFIG
        self._cached_token: Optional[Tuple[str, str]] = None
    
    async def authenticate(self) -> Tuple[str, str]:
        """
        Authenticate using Basic Auth and get custom token.
        
        This follows the authentication pattern:
        1. Use Basic Auth header with base64-encoded credentials
        2. POST to /token/gettoken to get a custom token
        3. Return both userpass and token for use in API calls
        
        Returns:
            Tuple[str, str]: (userpass, token) if authentication succeeds
            
        Raises:
            NoCredentialsError: If no credentials are configured
            InvalidCredentialsError: If credentials are invalid
            NetworkTimeoutError: If request times out
            APIUnavailableError: If auth service is unavailable
            AuthenticationError: For other auth failures
        """
        userpass = self.config.get("userpass")
        
        if not userpass:
            logger.error("No authentication credentials configured")
            raise NoCredentialsError(
                message="No authentication credentials configured in AUTH_CONFIG",
                user_message="Authentication is not configured. Please contact your administrator."
            )
        
        try:
            return await self._authenticate_with_retry(userpass)
        except RetryExhaustedError as e:
            logger.error(f"Authentication failed after all retries: {e.last_exception}")
            # Convert the last exception to appropriate ICC error
            last_exc = e.last_exception
            if isinstance(last_exc, httpx.TimeoutException):
                raise NetworkTimeoutError(
                    message="Authentication request timed out after retries",
                    user_message="Authentication is taking too long. Please try again.",
                    cause=last_exc
                )
            elif isinstance(last_exc, httpx.ConnectError):
                raise APIUnavailableError(
                    message="Could not connect to authentication service",
                    user_message="Unable to connect to the authentication server. Please try again later.",
                    service_name="Authentication",
                    cause=last_exc
                )
            else:
                raise AuthenticationError(
                    error_code=ErrorCode.AUTH_FAILED,
                    message=f"Authentication failed: {str(last_exc)}",
                    user_message="Authentication failed. Please try again.",
                    cause=last_exc
                )
    
    @retry(config=RetryPresets.AUTHENTICATION)
    async def _authenticate_with_retry(self, userpass: str) -> Tuple[str, str]:
        """
        Perform authentication with automatic retry.
        
        Args:
            userpass: Base64-encoded credentials
            
        Returns:
            Tuple of (userpass, token)
        """
        headers = {
            "Authorization": f"Basic {userpass}",
            "Content-Type": "application/json"
        }
        
        token_endpoint = self.config.get("token_endpoint")
        logger.debug(f"Attempting authentication to: {token_endpoint}")
        
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            response = await client.post(token_endpoint, headers=headers)
            
            logger.debug(f"Auth response status: {response.status_code}")
            
            if response.status_code == 401:
                raise InvalidCredentialsError(
                    message="Invalid credentials - received 401 Unauthorized",
                    user_message="The provided credentials are invalid. Please check and try again."
                )
            
            if response.status_code == 403:
                raise AuthenticationError(
                    error_code=ErrorCode.AUTH_FAILED,
                    message="Access forbidden - received 403 Forbidden",
                    user_message="Access denied. Please contact your administrator."
                )
            
            if response.status_code >= 500:
                # Server error - will be retried
                raise APIUnavailableError(
                    message=f"Auth server error: {response.status_code}",
                    user_message="Authentication service is temporarily unavailable.",
                    service_name="Authentication"
                )
            
            if response.status_code != 200:
                raise AuthenticationError(
                    error_code=ErrorCode.AUTH_FAILED,
                    message=f"Authentication failed with status {response.status_code}: {response.text}",
                    user_message="Authentication failed. Please try again."
                )
            
            response_data = response.json()
            token = response_data.get("token")
            
            if not token:
                logger.error(f"No token in auth response: {response.text[:200]}")
                raise AuthenticationError(
                    error_code=ErrorCode.AUTH_TOKEN_FETCH_FAILED,
                    message="No token in authentication response",
                    user_message="Authentication succeeded but no token was received. Please try again."
                )
            
            logger.info("Authentication successful")
            self._cached_token = (userpass, token)
            return (userpass, token)
    
    def get_cached_token(self) -> Optional[Tuple[str, str]]:
        """
        Get cached authentication token if available.
        
        Returns:
            Cached (userpass, token) tuple or None
        """
        return self._cached_token
    
    def clear_cache(self) -> None:
        """Clear cached authentication token."""
        self._cached_token = None
        logger.debug("Authentication cache cleared")


# Global service instance
_auth_service: Optional[AuthenticationService] = None


def get_auth_service() -> AuthenticationService:
    """Get or create singleton authentication service."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthenticationService()
    return _auth_service


async def authenticate() -> Optional[Tuple[str, str]]:
    """
    Authenticate using Basic Auth and get custom token.
    
    This is a convenience function that wraps the AuthenticationService.
    
    Returns:
        Optional[Tuple[str, str]]: (userpass, token) if authentication succeeds, None on failure
            - userpass: Base64-encoded username:password for Authorization header
            - token: Custom token for TokenKey header
    """
    try:
        service = get_auth_service()
        return await service.authenticate()
    except NoCredentialsError:
        logger.warning("No authentication credentials configured. API calls may fail.")
        return None
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected authentication error: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


async def authenticate_or_raise() -> Tuple[str, str]:
    """
    Authenticate and raise exception on failure.
    
    Use this when authentication is required and failure should stop execution.
    
    Returns:
        Tuple[str, str]: (userpass, token)
        
    Raises:
        AuthenticationError: If authentication fails
    """
    service = get_auth_service()
    return await service.authenticate()


def get_auth_headers_sync() -> dict:
    """
    Get authentication headers synchronously from cache.
    
    Returns:
        dict: Headers with Authorization and TokenKey, or empty dict if not authenticated
    """
    service = get_auth_service()
    cached = service.get_cached_token()
    if cached:
        userpass, token = cached
        return {
            "Authorization": f"Basic {userpass}",
            "TokenKey": token
        }
    return {}
