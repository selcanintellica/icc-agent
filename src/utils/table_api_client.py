"""
API client for fetching table definitions from external API.

This module replaces the file-based schema_docs system with API calls
to fetch table definitions dynamically.

Supports mock mode via TABLE_API_MOCK environment variable for testing.
"""

import os
import logging
import requests
from typing import List, Optional, Dict
from functools import lru_cache
from src.utils.mock_table_data import get_mock_table_definition
from src.config.api_config import TABLE_API_CONFIG

logger = logging.getLogger(__name__)


class TableAPIClient:
    """Client for fetching table definitions from API."""
    
    def __init__(self, base_url: Optional[str] = None, use_mock: Optional[bool] = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the table definitions API. 
                     If None, reads from TABLE_API_BASE_URL environment variable.
            use_mock: Whether to use mock data instead of API calls.
                     If None, reads from TABLE_API_MOCK environment variable.
        """
        self.base_url = base_url or TABLE_API_CONFIG["base_url"]
        self.timeout = TABLE_API_CONFIG["timeout"]
        
        # Check if mock mode is enabled
        if use_mock is None:
            self.use_mock = TABLE_API_CONFIG["use_mock"]
        else:
            self.use_mock = use_mock
        
        if self.use_mock:
            logger.info(f"🎭 TableAPIClient initialized in MOCK mode")
        else:
            logger.info(f"🌐 TableAPIClient initialized with base URL: {self.base_url}")
    
    def fetch_table_definition(
        self, 
        connection: str, 
        schema: str, 
        table: str
    ) -> Optional[str]:
        """
        Fetch a single table definition from the API or mock data.
        
        Args:
            connection: Connection name (e.g., 'ORACLE_10')
            schema: Schema name (e.g., 'SALES')
            table: Table name (e.g., 'customers')
            
        Returns:
            String containing the table definition, or None if not found
        """
        # Use mock data if enabled
        if self.use_mock:
            logger.info(f"🎭 Using mock data for: {connection}.{schema}.{table}")
            definition = get_mock_table_definition(connection, schema, table)
            
            if definition:
                logger.info(f"✅ Mock data found for {table} ({len(definition)} chars)")
            else:
                logger.warning(f"⚠️ No mock data found for {connection}.{schema}.{table}")
            
            return definition
        
        # Real API call
        url = f"{self.base_url}/{connection}/{schema}/{table}"
        
        try:
            logger.info(f"🔍 Fetching table definition from API: {connection}.{schema}.{table}")
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Expected API response format:
            # {
            #   "connection": "ORACLE_10",
            #   "schema": "SALES",
            #   "table": "customers",
            #   "definition": "Table: customers\nSchema: SALES\n..."
            # }
            
            definition = data.get("definition", "")
            
            if definition:
                logger.info(f"✅ Successfully fetched definition for {table} ({len(definition)} chars)")
                return definition
            else:
                logger.warning(f"⚠️ Empty definition returned for {connection}.{schema}.{table}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ API timeout fetching {connection}.{schema}.{table}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API error fetching {connection}.{schema}.{table}: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching {connection}.{schema}.{table}: {str(e)}")
            return None
    
    def fetch_multiple_tables(
        self, 
        connection: str, 
        schema: str, 
        tables: List[str]
    ) -> str:
        """
        Fetch definitions for multiple tables and combine them.
        
        Args:
            connection: Connection name
            schema: Schema name
            tables: List of table names to fetch
            
        Returns:
            Combined string with all table definitions separated by newlines
        """
        definitions = []
        
        logger.info(f"📦 Fetching {len(tables)} table definitions from API")
        
        for table in tables:
            definition = self.fetch_table_definition(connection, schema, table)
            if definition:
                definitions.append(definition)
                definitions.append("\n" + "="*80 + "\n")  # Separator
        
        combined = "\n".join(definitions)
        
        logger.info(f"✅ Successfully fetched {len(definitions)//2}/{len(tables)} table definitions")
        
        return combined
    
    def fetch_multiple_tables_batch(
        self, 
        connection: str, 
        schema: str, 
        tables: List[str]
    ) -> str:
        """
        Fetch definitions for multiple tables using a batch API endpoint.
        
        This is more efficient than individual calls if the API supports it.
        Falls back to individual calls if batch endpoint is not available.
        In mock mode, always uses individual calls.
        
        Args:
            connection: Connection name
            schema: Schema name
            tables: List of table names to fetch
            
        Returns:
            Combined string with all table definitions
        """
        # In mock mode, use individual calls
        if self.use_mock:
            logger.info(f"🎭 Mock mode: using individual table fetches")
            return self.fetch_multiple_tables(connection, schema, tables)
        
        batch_url = f"{self.base_url}/batch"
        
        try:
            logger.info(f"📦 Attempting batch fetch for {len(tables)} tables")
            
            payload = {
                "connection": connection,
                "schema": schema,
                "tables": tables
            }
            
            response = requests.post(batch_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Expected batch API response format:
            # {
            #   "definitions": [
            #     {"table": "customers", "definition": "..."},
            #     {"table": "orders", "definition": "..."}
            #   ]
            # }
            
            definitions = []
            for item in data.get("definitions", []):
                definition = item.get("definition", "")
                if definition:
                    definitions.append(definition)
                    definitions.append("\n" + "="*80 + "\n")
            
            combined = "\n".join(definitions)
            
            logger.info(f"✅ Batch fetch successful: {len(definitions)//2} tables")
            return combined
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Batch API not available or failed: {str(e)}")
            logger.info("🔄 Falling back to individual API calls")
            return self.fetch_multiple_tables(connection, schema, tables)
    
    def health_check(self) -> bool:
        """
        Check if the API is reachable.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            health_url = f"{self.base_url.rsplit('/tables', 1)[0]}/health"
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except:
            return False


# Global instance
table_api_client = TableAPIClient()


def get_table_api_client() -> TableAPIClient:
    """Get the global table API client instance."""
    return table_api_client


# Convenience functions
def fetch_table_definitions(
    connection: str, 
    schema: str, 
    tables: List[str],
    use_batch: bool = True
) -> str:
    """
    Fetch table definitions from API.
    
    Args:
        connection: Connection name
        schema: Schema name
        tables: List of table names
        use_batch: Whether to use batch API if available
        
    Returns:
        Combined string with all table definitions
    """
    if use_batch:
        return table_api_client.fetch_multiple_tables_batch(connection, schema, tables)
    else:
        return table_api_client.fetch_multiple_tables(connection, schema, tables)
