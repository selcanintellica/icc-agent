"""
Database configuration loader - reads database hierarchy from JSON config.

This module replaces the file-based schema_docs folder scanning with
JSON configuration for UI dropdowns.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default path to database configuration
CONFIG_PATH = Path(__file__).parent.parent.parent / "db_config.json"


class ConfigLoader:
    """Loads database configuration from JSON file."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the config loader.
        
        Args:
            config_path: Path to db_config.json. If None, uses default.
        """
        self.config_path = config_path or CONFIG_PATH
        self._config = None
        
        logger.info(f"🔍 ConfigLoader initialized with path: {self.config_path.absolute()}")
        
        if not self.config_path.exists():
            logger.error(f"❌ Config file does not exist: {self.config_path.absolute()}")
            raise FileNotFoundError(f"Database config not found: {self.config_path}")
        
        self._load_config()
    
    def _load_config(self):
        """Load the configuration from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            logger.info(f"✅ Config loaded successfully: {len(self._config.get('connections', []))} connections")
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in config file: {e}")
            raise
        
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            raise
    
    def reload_config(self):
        """Reload the configuration from file (useful for hot-reloading)."""
        logger.info("🔄 Reloading configuration...")
        self._load_config()
    
    def get_available_connections(self) -> List[str]:
        """
        Get list of available database connections.
        
        Returns:
            List of connection names
        """
        connections = [conn["name"] for conn in self._config.get("connections", [])]
        logger.info(f"Found connections: {connections}")
        return connections
    
    def get_schemas_for_connection(self, connection: str) -> List[str]:
        """
        Get list of schemas for a specific connection.
        
        Args:
            connection: Connection name
            
        Returns:
            List of schema names
        """
        for conn in self._config.get("connections", []):
            if conn["name"] == connection:
                schemas = [schema["name"] for schema in conn.get("schemas", [])]
                logger.info(f"Found schemas for {connection}: {schemas}")
                return schemas
        
        logger.warning(f"Connection not found: {connection}")
        return []
    
    def get_tables_for_schema(self, connection: str, schema: str) -> List[str]:
        """
        Get list of tables for a specific connection and schema.
        
        Args:
            connection: Connection name
            schema: Schema name
            
        Returns:
            List of table names
        """
        for conn in self._config.get("connections", []):
            if conn["name"] == connection:
                for sch in conn.get("schemas", []):
                    if sch["name"] == schema:
                        tables = sch.get("tables", [])
                        logger.info(f"Found tables for {connection}.{schema}: {tables}")
                        return tables
        
        logger.warning(f"Schema not found: {connection}.{schema}")
        return []
    
    def get_connection_structure(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get the complete structure of all connections, schemas, and tables.
        
        Returns:
            Nested dictionary: {connection: {schema: [tables]}}
        """
        structure = {}
        
        for conn in self._config.get("connections", []):
            conn_name = conn["name"]
            structure[conn_name] = {}
            
            for schema in conn.get("schemas", []):
                schema_name = schema["name"]
                structure[conn_name][schema_name] = schema.get("tables", [])
        
        return structure
    
    def get_connection_options(self) -> List[Dict[str, str]]:
        """
        Get connection options in format suitable for Dash dropdown.
        
        Returns:
            List of dicts with 'label' and 'value' keys
        """
        connections = self._config.get("connections", [])
        return [
            {"label": conn.get("label", conn["name"]), "value": conn["name"]} 
            for conn in connections
        ]
    
    def get_schema_options(self, connection: str) -> List[Dict[str, str]]:
        """
        Get schema options for a connection in format suitable for Dash dropdown.
        
        Args:
            connection: Connection name
            
        Returns:
            List of dicts with 'label' and 'value' keys
        """
        for conn in self._config.get("connections", []):
            if conn["name"] == connection:
                schemas = conn.get("schemas", [])
                return [
                    {"label": schema.get("label", schema["name"]), "value": schema["name"]} 
                    for schema in schemas
                ]
        
        return []
    
    def get_table_options(self, connection: str, schema: str) -> List[Dict[str, str]]:
        """
        Get table options for a schema in format suitable for Dash dropdown.
        
        Args:
            connection: Connection name
            schema: Schema name
            
        Returns:
            List of dicts with 'label' and 'value' keys
        """
        tables = self.get_tables_for_schema(connection, schema)
        return [{"label": table, "value": table} for table in tables]
    
    def get_connection_label(self, connection: str) -> str:
        """Get the display label for a connection."""
        for conn in self._config.get("connections", []):
            if conn["name"] == connection:
                return conn.get("label", connection)
        return connection
    
    def get_schema_label(self, connection: str, schema: str) -> str:
        """Get the display label for a schema."""
        for conn in self._config.get("connections", []):
            if conn["name"] == connection:
                for sch in conn.get("schemas", []):
                    if sch["name"] == schema:
                        return sch.get("label", schema)
        return schema


# Global instance
config_loader = ConfigLoader()


def get_config_loader() -> ConfigLoader:
    """Get the global config loader instance."""
    return config_loader


# Convenience functions
def get_connections() -> List[str]:
    """Get list of available connections."""
    return config_loader.get_available_connections()


def get_schemas(connection: str) -> List[str]:
    """Get list of schemas for a connection."""
    return config_loader.get_schemas_for_connection(connection)


def get_tables(connection: str, schema: str) -> List[str]:
    """Get list of tables for a schema."""
    return config_loader.get_tables_for_schema(connection, schema)
