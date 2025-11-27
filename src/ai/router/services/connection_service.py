"""
Connection service abstraction - handles connection ID lookups.
Implements Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Optional


class ConnectionService(ABC):
    """Abstract interface for connection management."""
    
    @abstractmethod
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """
        Get connection ID from connection name.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Connection ID or None if not found
        """
        pass


class ICCConnectionService(ConnectionService):
    """ICC-specific implementation of connection service."""
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """Get connection ID from static connections file."""
        from src.utils.connections import get_connection_id as get_conn_id_static
        return get_conn_id_static(connection_name)


class MockConnectionService(ConnectionService):
    """Mock connection service for testing."""
    
    def __init__(self, mock_connections: dict = None):
        self.connections = mock_connections or {"ORACLE_10": "conn_123"}
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        return self.connections.get(connection_name)
