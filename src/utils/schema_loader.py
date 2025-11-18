"""
Schema documentation loader - discovers and loads table definitions from files.

This module provides utilities to:
1. Scan the schema_docs folder to discover available connections, schemas, and tables
2. Load table definition files for SQL generation
3. Build dynamic schema contexts based on user selections

Folder Structure:
    schema_docs/
        {connection}/
            {schema}/
                {table}.txt
                
Example:
    schema_docs/
        oracle_10/
            SALES/
                customers.txt
                orders.txt
                products.txt
            HR/
                employees.txt
                departments.txt
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default path to schema documentation
# Calculate path: src/utils/schema_loader.py -> src/utils -> src -> project_root -> schema_docs
SCHEMA_DOCS_PATH = Path(__file__).parent.parent.parent / "schema_docs"


class SchemaLoader:
    """Loads and manages database schema documentation from files."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the schema loader.
        
        Args:
            base_path: Path to schema_docs folder. If None, uses default.
        """
        self.base_path = base_path or SCHEMA_DOCS_PATH
        
        logger.info(f"🔍 SchemaLoader initialized with path: {self.base_path.absolute()}")
        
        if not self.base_path.exists():
            logger.warning(f"⚠️ Schema docs path does not exist: {self.base_path.absolute()}")
            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            logger.info(f"✅ Schema docs path exists: {self.base_path.absolute()}")
    
    def get_available_connections(self) -> List[str]:
        """
        Get list of available database connections.
        
        Returns:
            List of connection names (folder names in schema_docs/)
        """
        if not self.base_path.exists():
            return []
        
        connections = [
            item.name for item in self.base_path.iterdir() 
            if item.is_dir() and not item.name.startswith('.')
        ]
        
        logger.info(f"Found connections: {connections}")
        return sorted(connections)
    
    def get_schemas_for_connection(self, connection: str) -> List[str]:
        """
        Get list of schemas for a specific connection.
        
        Args:
            connection: Connection name
            
        Returns:
            List of schema names (folder names in connection folder)
        """
        conn_path = self.base_path / connection
        
        if not conn_path.exists():
            logger.warning(f"Connection path not found: {conn_path}")
            return []
        
        schemas = [
            item.name for item in conn_path.iterdir() 
            if item.is_dir() and not item.name.startswith('.')
        ]
        
        logger.info(f"Found schemas for {connection}: {schemas}")
        return sorted(schemas)
    
    def get_tables_for_schema(self, connection: str, schema: str) -> List[str]:
        """
        Get list of tables for a specific connection and schema.
        
        Args:
            connection: Connection name
            schema: Schema name
            
        Returns:
            List of table names (filenames without .txt extension)
        """
        schema_path = self.base_path / connection / schema
        
        if not schema_path.exists():
            logger.warning(f"Schema path not found: {schema_path}")
            return []
        
        tables = [
            item.stem for item in schema_path.iterdir() 
            if item.is_file() and item.suffix == '.txt'
        ]
        
        logger.info(f"Found tables for {connection}.{schema}: {tables}")
        return sorted(tables)
    
    def load_table_definition(self, connection: str, schema: str, table: str) -> Optional[str]:
        """
        Load the full definition for a specific table.
        
        Args:
            connection: Connection name
            schema: Schema name
            table: Table name
            
        Returns:
            String containing the full table definition, or None if not found
        """
        table_file = self.base_path / connection / schema / f"{table}.txt"
        
        if not table_file.exists():
            logger.warning(f"Table definition not found: {table_file}")
            return None
        
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Loaded table definition: {connection}.{schema}.{table}")
            return content
        
        except Exception as e:
            logger.error(f"Error loading table definition {table_file}: {e}")
            return None
    
    def load_multiple_tables(self, connection: str, schema: str, tables: List[str]) -> str:
        """
        Load definitions for multiple tables and combine them.
        
        Args:
            connection: Connection name
            schema: Schema name
            tables: List of table names to load
            
        Returns:
            Combined string with all table definitions separated by newlines
        """
        definitions = []
        
        for table in tables:
            definition = self.load_table_definition(connection, schema, table)
            if definition:
                definitions.append(definition)
                definitions.append("\n" + "="*80 + "\n")  # Separator
        
        combined = "\n".join(definitions)
        
        logger.info(f"Loaded {len(definitions)//2} table definitions for {connection}.{schema}")
        return combined
    
    def get_connection_structure(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get the complete structure of all connections, schemas, and tables.
        
        Returns:
            Nested dictionary: {connection: {schema: [tables]}}
        """
        structure = {}
        
        for connection in self.get_available_connections():
            structure[connection] = {}
            
            for schema in self.get_schemas_for_connection(connection):
                tables = self.get_tables_for_schema(connection, schema)
                structure[connection][schema] = tables
        
        return structure
    
    def get_connection_options(self) -> List[Dict[str, str]]:
        """
        Get connection options in format suitable for Dash dropdown.
        
        Returns:
            List of dicts with 'label' and 'value' keys
        """
        connections = self.get_available_connections()
        return [{"label": conn, "value": conn} for conn in connections]
    
    def get_schema_options(self, connection: str) -> List[Dict[str, str]]:
        """
        Get schema options for a connection in format suitable for Dash dropdown.
        
        Args:
            connection: Connection name
            
        Returns:
            List of dicts with 'label' and 'value' keys
        """
        schemas = self.get_schemas_for_connection(connection)
        return [{"label": schema, "value": schema} for schema in schemas]
    
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


# Global instance
schema_loader = SchemaLoader()


def get_schema_loader() -> SchemaLoader:
    """Get the global schema loader instance."""
    return schema_loader


# Convenience functions
def get_connections() -> List[str]:
    """Get list of available connections."""
    return schema_loader.get_available_connections()


def get_schemas(connection: str) -> List[str]:
    """Get list of schemas for a connection."""
    return schema_loader.get_schemas_for_connection(connection)


def get_tables(connection: str, schema: str) -> List[str]:
    """Get list of tables for a schema."""
    return schema_loader.get_tables_for_schema(connection, schema)


def load_table_definitions(connection: str, schema: str, tables: List[str]) -> str:
    """Load and combine definitions for multiple tables."""
    return schema_loader.load_multiple_tables(connection, schema, tables)
