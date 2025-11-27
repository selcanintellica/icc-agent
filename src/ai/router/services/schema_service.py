"""
Schema service abstraction - handles schema fetching from connections.
Implements Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class SchemaService(ABC):
    """Abstract interface for schema management."""
    
    @abstractmethod
    async def fetch_schemas(self, connection_id: str, auth_headers: Dict[str, str]) -> List[str]:
        """
        Fetch schemas for a given connection.
        
        Args:
            connection_id: The connection ID
            auth_headers: Authentication headers (Authorization, TokenKey)
            
        Returns:
            List of schema names
        """
        pass


class ICCSchemaService(SchemaService):
    """ICC-specific implementation of schema service."""
    
    async def fetch_schemas(self, connection_id: str, auth_headers: Dict[str, str]) -> List[str]:
        """Fetch schemas from ICC API."""
        from src.utils.connection_api_client import fetch_schemas_for_connection
        return await fetch_schemas_for_connection(connection_id, auth_headers=auth_headers)


class MockSchemaService(SchemaService):
    """Mock schema service for testing."""
    
    def __init__(self, mock_schemas: List[str] = None):
        self.schemas = mock_schemas or ["SCHEMA1", "SCHEMA2", "SCHEMA3"]
    
    async def fetch_schemas(self, connection_id: str, auth_headers: Dict[str, str]) -> List[str]:
        return self.schemas
