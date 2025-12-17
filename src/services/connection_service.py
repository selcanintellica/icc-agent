"""
Connection service for handling database connection operations.

Extracts connection-related business logic from app.py following SOLID principles:
- Single Responsibility: Only handles connection operations
- Dependency Inversion: Depends on abstractions (ICCAPIClient)
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from src.api_clients.connection_api_client import ICCAPIClient
from src.utils.auth import authenticate
from src.utils.config_loader import get_config_loader

logger = logging.getLogger(__name__)


class ConnectionService:
    """
    Service for managing database connections, schemas, and tables.
    
    Encapsulates all connection-related operations with proper error handling
    and caching.
    """
    
    def __init__(self):
        """Initialize connection service with cache."""
        self._connection_id_cache: Dict[str, str] = {}
        self._config_loader = get_config_loader()
    
    async def get_connection_id(self, connection_name: str) -> Optional[str]:
        """
        Get connection ID from cache or fetch from API.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Connection ID if found, None otherwise
        """
        # Return from cache if available
        if connection_name in self._connection_id_cache:
            logger.debug(f"Connection ID for '{connection_name}' found in cache")
            return self._connection_id_cache[connection_name]
        
        try:
            # Fetch all connections and populate cache
            await self._populate_connection_cache()
            return self._connection_id_cache.get(connection_name)
            
        except Exception as e:
            logger.error(f"Error fetching connection ID for '{connection_name}': {e}")
            return None
    
    async def _populate_connection_cache(self) -> None:
        """
        Populate connection cache by fetching from API.
        
        Raises:
            Exception: If authentication or API call fails
        """
        # Authenticate
        auth_result = await authenticate()
        if not auth_result:
            logger.warning("Authentication failed")
            return
        
        userpass, token = auth_result
        auth_headers = {
            "Authorization": f"Basic {userpass}",
            "TokenKey": token
        }
        
        # Fetch connections
        api_client = ICCAPIClient(auth_headers=auth_headers)
        connections = await api_client.fetch_connections()
        
        # Populate cache
        for name, info in connections.items():
            self._connection_id_cache[name] = info.get("id")
        
        logger.info(f"Cached {len(self._connection_id_cache)} connection IDs")
    
    async def fetch_schemas(
        self, 
        connection_name: str
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        Fetch schemas for a connection.
        
        Args:
            connection_name: Name of the connection
            
        Returns:
            Tuple of (schema_options, default_schema)
            - schema_options: List of dropdown options
            - default_schema: First schema name or None
        """
        try:
            # Get connection ID
            connection_id = await self.get_connection_id(connection_name)
            if not connection_id:
                logger.warning(f"Connection ID not found for '{connection_name}'")
                return [], None
            
            # Authenticate
            auth_result = await authenticate()
            if not auth_result:
                logger.warning("Authentication failed")
                return [], None
            
            userpass, token = auth_result
            auth_headers = {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
            
            # Fetch schemas
            api_client = ICCAPIClient(auth_headers=auth_headers)
            schemas = await api_client.fetch_schemas(connection_id)
            
            # Convert to dropdown format
            schema_options = [{"label": schema, "value": schema} for schema in schemas]
            default_schema = schemas[0] if schemas else None
            
            logger.info(f"Fetched {len(schemas)} schemas for connection '{connection_name}'")
            return schema_options, default_schema
            
        except Exception as e:
            logger.error(f"Error fetching schemas for connection '{connection_name}': {e}")
            return [], None
    
    async def fetch_tables(
        self,
        connection_name: str,
        schema: str
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        Fetch tables for a connection and schema.
        
        Args:
            connection_name: Name of the connection
            schema: Schema name
            
        Returns:
            Tuple of (table_options, default_tables)
            - table_options: List of dropdown options
            - default_tables: First 2 tables or empty list
        """
        try:
            # Get connection ID
            connection_id = await self.get_connection_id(connection_name)
            if not connection_id:
                logger.warning(f"Connection ID not found for '{connection_name}'")
                return [], []
            
            # Authenticate
            auth_result = await authenticate()
            if not auth_result:
                logger.warning("Authentication failed")
                return [], []
            
            userpass, token = auth_result
            auth_headers = {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
            
            # Fetch tables
            api_client = ICCAPIClient(auth_headers=auth_headers)
            tables = await api_client.fetch_tables(connection_id, schema)
            
            # Convert to dropdown format
            table_options = [{"label": table, "value": table} for table in tables]
            default_tables = tables[:2] if len(tables) >= 2 else tables
            
            logger.info(f"Fetched {len(tables)} tables for '{connection_name}.{schema}'")
            return table_options, default_tables
            
        except Exception as e:
            logger.error(f"Error fetching tables for '{connection_name}.{schema}': {e}")
            return [], []
    
    def get_initial_config(self) -> Dict[str, Any]:
        """
        Get initial configuration for UI from static config.
        
        Returns:
            Dict with connections, schemas, tables, and default selections
        """
        connections = self._config_loader.get_available_connections()
        initial_connection = connections[0] if connections else None
        
        schemas = self._config_loader.get_schemas_for_connection(initial_connection) if initial_connection else []
        initial_schema = schemas[0] if schemas else None
        
        tables = self._config_loader.get_tables_for_schema(initial_connection, initial_schema) if (initial_connection and initial_schema) else []
        initial_tables = tables[:2] if len(tables) >= 2 else tables
        
        return {
            "connections": connections,
            "initial_connection": initial_connection,
            "schemas": schemas,
            "initial_schema": initial_schema,
            "tables": tables,
            "initial_tables": initial_tables,
            "connection_options": self._config_loader.get_connection_options(),
            "schema_options": self._config_loader.get_schema_options(initial_connection) if initial_connection else [],
            "table_options": self._config_loader.get_table_options(initial_connection, initial_schema) if (initial_connection and initial_schema) else [],
        }
    
    def clear_cache(self) -> None:
        """Clear the connection ID cache."""
        self._connection_id_cache.clear()
        logger.info("Connection cache cleared")


# Global service instance (singleton pattern)
_connection_service: Optional[ConnectionService] = None


def get_connection_service() -> ConnectionService:
    """
    Get or create the global connection service instance.
    
    Returns:
        ConnectionService: Global service instance
    """
    global _connection_service
    if _connection_service is None:
        _connection_service = ConnectionService()
        logger.info("Created global ConnectionService instance")
    return _connection_service
