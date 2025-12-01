"""
Connection Resolver Service.

Handles connection ID resolution following Single Responsibility Principle.
"""

from typing import Optional
import logging

from src.utils.connections import get_connection_id

logger = logging.getLogger(__name__)


class ConnectionResolver:
    """
    Service for resolving connection names to connection IDs.
    
    Following SRP - only responsible for connection resolution.
    """
    
    def __init__(self):
        """Initialize connection resolver."""
        pass
    
    def resolve_connection_id(self, connection_name: str) -> str:
        """
        Resolve connection name to connection ID.
        
        Falls back to connection_name if ID not found.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            str: Connection ID or original name if not found
        """
        if not connection_name:
            logger.warning("Empty connection name provided")
            return ""
        
        connection_id = get_connection_id(connection_name)
        
        if connection_id:
            logger.debug(f"Resolved '{connection_name}' → '{connection_id}'")
            return connection_id
        else:
            logger.debug(f"Connection ID not found for '{connection_name}', using name as-is")
            return connection_name
    
    def resolve_multiple(self, connection_names: list[str]) -> list[str]:
        """
        Resolve multiple connection names to IDs.
        
        Args:
            connection_names: List of connection names
            
        Returns:
            list[str]: List of resolved connection IDs
        """
        return [self.resolve_connection_id(name) for name in connection_names]


# Singleton instance
_resolver: Optional[ConnectionResolver] = None


def get_connection_resolver() -> ConnectionResolver:
    """
    Get singleton instance of ConnectionResolver.
    
    Returns:
        ConnectionResolver: Singleton instance
    """
    global _resolver
    if _resolver is None:
        _resolver = ConnectionResolver()
    return _resolver
