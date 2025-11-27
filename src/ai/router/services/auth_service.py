"""
Authentication service abstraction - handles authentication.
Implements Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional


class AuthService(ABC):
    """Abstract interface for authentication."""
    
    @abstractmethod
    async def authenticate(self) -> Optional[Tuple[str, str]]:
        """
        Authenticate and get credentials.
        
        Returns:
            Tuple of (userpass, token) or None if authentication fails
        """
        pass


class ICCAuthService(AuthService):
    """ICC-specific implementation of authentication service."""
    
    async def authenticate(self) -> Optional[Tuple[str, str]]:
        """Authenticate using ICC auth module."""
        from src.utils.auth import authenticate as auth_func
        return await auth_func()


class MockAuthService(AuthService):
    """Mock authentication service for testing."""
    
    def __init__(self, userpass: str = "mock_userpass", token: str = "mock_token"):
        self.userpass = userpass
        self.token = token
    
    async def authenticate(self) -> Optional[Tuple[str, str]]:
        return (self.userpass, self.token)
