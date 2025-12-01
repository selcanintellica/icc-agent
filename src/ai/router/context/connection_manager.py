"""
Connection Manager.

Handles connection-related operations following Single Responsibility Principle.
"""

from typing import Dict, Any, Optional, List


class ConnectionManager:
    """
    Manages database connections and schema information.
    
    Following SRP - only responsible for connection-related operations.
    """
    
    def __init__(
        self,
        default_connection: str = "ORACLE_10",
        default_schema: str = "SALES"
    ):
        """
        Initialize connection manager.
        
        Args:
            default_connection: Default connection name
            default_schema: Default schema name
        """
        self._connection: str = default_connection
        self._schema: str = default_schema
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._available_schemas: List[str] = []
    
    @property
    def connection(self) -> str:
        """Get current connection name."""
        return self._connection
    
    @connection.setter
    def connection(self, value: str) -> None:
        """Set current connection name."""
        self._connection = value
    
    @property
    def schema(self) -> str:
        """Get current schema name."""
        return self._schema
    
    @schema.setter
    def schema(self, value: str) -> None:
        """Set current schema name."""
        self._schema = value
    
    @property
    def connections(self) -> Dict[str, Dict[str, Any]]:
        """Get all available connections."""
        return self._connections
    
    @connections.setter
    def connections(self, value: Dict[str, Dict[str, Any]]) -> None:
        """Set available connections."""
        self._connections = value
    
    @property
    def available_schemas(self) -> List[str]:
        """Get available schemas."""
        return self._available_schemas
    
    @available_schemas.setter
    def available_schemas(self, value: List[str]) -> None:
        """Set available schemas."""
        self._available_schemas = value
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """
        Get connection ID from stored connections with fuzzy matching.
        
        Handles cases like:
        - "ORACLE_10" matches "ORACLE_10"
        - "ORACLE_10 (Oracle)" matches "ORACLE_10"
        - "oracle10" matches "ORACLE_10"
        - "oracle_10" matches "ORACLE_10"
        
        Args:
            connection_name: Name of the connection (can include db_type in parentheses)
            
        Returns:
            Connection ID string or None if not found
        """
        if not connection_name:
            return None
        
        # First try exact match
        conn = self._connections.get(connection_name)
        if conn:
            return conn.get("id")
        
        # Remove anything in parentheses (e.g., "ORACLE_10 (Oracle)" -> "ORACLE_10")
        clean_name = connection_name.split("(")[0].strip()
        conn = self._connections.get(clean_name)
        if conn:
            return conn.get("id")
        
        # Try case-insensitive match with underscores removed
        # "oracle10" or "ORACLE10" -> matches "ORACLE_10"
        normalized_input = clean_name.lower().replace("_", "").replace("-", "")
        
        for stored_name, conn_info in self._connections.items():
            normalized_stored = stored_name.lower().replace("_", "").replace("-", "")
            if normalized_input == normalized_stored:
                return conn_info.get("id")
        
        return None
    
    def get_connection_list_for_llm(self) -> str:
        """
        Format connection list for LLM to present to user.
        
        Returns:
            Formatted string with available connections
        """
        if not self._connections:
            return "No connections available."
        
        conn_list = []
        for name, info in self._connections.items():
            db_type = info.get("db_type", "Unknown")
            conn_list.append(f"• {name} ({db_type})")
        
        return "\n".join(conn_list)
    
    def get_schema_list_for_llm(self) -> str:
        """
        Format schema list for LLM to present to user.
        
        Returns:
            Formatted string with available schemas
        """
        if not self._available_schemas:
            return "No schemas available."
        
        # Format schemas in columns for better readability
        schema_list = [f"• {schema}" for schema in self._available_schemas]
        return "\n".join(schema_list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "connection": self._connection,
            "schema": self._schema,
            "connections": self._connections,
            "available_schemas": self._available_schemas
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionManager":
        """Create ConnectionManager from dictionary."""
        manager = cls(
            default_connection=data.get("connection", "ORACLE_10"),
            default_schema=data.get("schema", "SALES")
        )
        manager.connections = data.get("connections", {})
        manager.available_schemas = data.get("available_schemas", [])
        return manager
