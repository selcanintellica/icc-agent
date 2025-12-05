"""
API client for fetching table definitions from external API.

This module provides table definition fetching with:
- Retry logic for transient failures
- Mock mode support for testing
- Structured error handling
"""

import os
import logging
from typing import List, Optional, Dict, Any

import requests
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError, RequestException

from src.utils.mock_table_data import get_mock_table_definition
from src.utils.retry import retry_sync_operation, RetryConfig, RetryStrategy
from src.errors import (
    NetworkTimeoutError,
    APIUnavailableError,
    HTTPError,
    TableNotFoundError,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


def format_table_definition_from_api(
    table_name: str,
    schema: str,
    connection: str,
    api_response: Dict[str, Any]
) -> str:
    """
    Transform ICC API response into SQL agent format.
    
    Converts structured JSON (columnList) into descriptive text format
    that the SQL agent expects.
    
    Args:
        table_name: Name of the table
        schema: Schema name
        connection: Connection name
        api_response: API response with columnList structure
        
    Returns:
        Formatted table definition string
    """
    column_list = api_response.get("columnList", [])
    
    if not column_list:
        return f"Table: {table_name}\nSchema: {schema}\nConnection: {connection}\n\nNo column information available."
    
    # Build the definition
    definition_parts = [
        f"Table: {table_name}",
        f"Schema: {schema}",
        f"Connection: {connection}",
        "",
        "Description:",
        f"Table containing {len(column_list)} columns.",
        "",
        "Columns:"
    ]
    
    # Add column details
    for col in column_list:
        col_name = col.get("columnName", "unknown")
        col_type = col.get("columnType", "unknown")
        col_length = col.get("columnLength", "")
        
        # Format type with length
        if col_length and col_type in ["VARCHAR2", "VARCHAR", "CHAR"]:
            type_info = f"{col_type}({col_length})"
        elif col_length and col_type == "NUMBER":
            type_info = f"{col_type}({col_length})"
        else:
            type_info = col_type
        
        definition_parts.append(f"- {col_name} ({type_info})")
    
    # Add notes about duplicates if any
    if api_response.get("duplicateColumnExists", False):
        dup_cols = api_response.get("duplicateColumnList", [])
        definition_parts.extend([
            "",
            "Notes:",
            f"- Warning: Duplicate columns detected: {', '.join(dup_cols) if dup_cols else 'see duplicateColumnList'}"
        ])
    
    definition_parts.extend([
        "",
        "Foreign Keys:",
        "Unknown (not provided by API)",
        "",
        "Example Queries:",
        f"-- Get all records from {table_name}",
        f"SELECT * FROM {schema}.{table_name};",
        "",
        f"-- Get specific columns",
        f"SELECT {', '.join([c.get('columnName', '') for c in column_list[:3]])} FROM {schema}.{table_name};"
    ])
    
    return "\n".join(definition_parts)


# Retry configuration for table API calls
TABLE_API_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    base_delay=0.5,
    max_delay=5.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter=True,
    retryable_exceptions=(
        Timeout,
        RequestsConnectionError,
        ConnectionError,
        TimeoutError,
    ),
)


class TableAPIClient:
    """
    Client for fetching table definitions from ICC API with retry support.
    
    Supports mock mode via TABLE_API_MOCK environment variable for testing.
    Uses ICC API endpoint: POST /utility/connection/{connection_id}/{schema}/{table}
    """
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        use_mock: Optional[bool] = None,
        auth_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the ICC API.
                     If None, reads from ICC_API_BASE_URL environment variable.
            use_mock: Whether to use mock data instead of API calls.
                     If None, reads from TABLE_API_MOCK environment variable.
            auth_headers: Authentication headers (Authorization, TokenKey)
        """
        self.base_url = base_url or os.getenv(
            "TABLE_API_BASE_URL",
            "https://172.16.22.13:8084/utility/table"
        )
        self.timeout = float(os.getenv("API_TIMEOUT", "30"))
        self.auth_headers = auth_headers or {}
        
        # Check if mock mode is enabled
        if use_mock is None:
            mock_env = os.getenv("TABLE_API_MOCK", "false").lower()
            self.use_mock = mock_env in ("true", "1", "yes")
        else:
            self.use_mock = use_mock
        
        if self.use_mock:
            logger.info("TableAPIClient initialized in MOCK mode")
        else:
            logger.info(f"TableAPIClient initialized with ICC API: {self.base_url}")
    
    def fetch_table_definition(
        self,
        connection_id: str,
        schema: str,
        table: str,
        connection_name: str = None
    ) -> Optional[str]:
        """
        Fetch a single table definition from ICC API or mock data.
        
        Args:
            connection_id: Connection ID from API (e.g., '955448816772621')
            schema: Schema name (e.g., 'SALES')
            table: Table name (e.g., 'customers')
            connection_name: Connection name for mock mode (e.g., 'ORACLE_10')
            
        Returns:
            String containing the formatted table definition, or None if not found
        """
        # Use mock data if enabled
        if self.use_mock:
            # Mock mode needs connection_name, not connection_id
            if not connection_name:
                connection_name = "ORACLE_10"  # Default for testing
            
            logger.info(f"Using mock data for: {connection_name}.{schema}.{table}")
            definition = get_mock_table_definition(connection_name, schema, table)
            
            if definition:
                logger.info(f"Mock data found for {table} ({len(definition)} chars)")
            else:
                logger.warning(f"No mock data found for {connection_name}.{schema}.{table}")
            
            return definition
        
        # Real ICC API call with retry
        # Endpoint format: /utility/table/{table}/{connection_id}/{schema}
        endpoint = f"{self.base_url}/{table}/{connection_id}/{schema}"
        
        try:
            return self._fetch_with_retry(endpoint, connection_id, schema, table, connection_name)
        except Exception as e:
            # Log but don't raise - return None to allow graceful degradation
            logger.error(f"Failed to fetch table definition for {connection_id}.{schema}.{table}: {e}")
            return None
    
    def _fetch_with_retry(
        self,
        endpoint: str,
        connection_id: str,
        schema: str,
        table: str,
        connection_name: str = None
    ) -> Optional[str]:
        """Fetch table definition with retry logic."""
        def do_fetch():
            return self._do_fetch_request(endpoint, connection_id, schema, table, connection_name)
        
        try:
            return retry_sync_operation(do_fetch, config=TABLE_API_RETRY_CONFIG)
        except Exception as e:
            # Handle retry exhaustion gracefully
            logger.warning(f"Table definition fetch failed after retries: {e}")
            return None
    
    def _do_fetch_request(
        self,
        endpoint: str,
        connection_id: str,
        schema: str,
        table: str,
        connection_name: str = None
    ) -> Optional[str]:
        """Execute the actual HTTP POST request to ICC API."""
        logger.info(f"Fetching table definition from ICC API: {table}/{connection_id}/{schema}")
        logger.debug(f"Endpoint: {endpoint}")
        
        try:
            response = requests.post(
                endpoint,
                headers=self.auth_headers,
                verify=False,  # ICC API uses self-signed cert
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                logger.warning(f"Table not found: {connection_id}.{schema}.{table}")
                return None
            
            if response.status_code == 401 or response.status_code == 403:
                logger.error(f"Authentication failed when fetching table definition")
                raise APIUnavailableError(
                    message=f"Authentication failed: {response.status_code}",
                    user_message="Authentication failed. Please refresh and try again."
                )
            
            if response.status_code >= 500:
                # Server error - will be retried
                raise APIUnavailableError(
                    message=f"Server error {response.status_code} from ICC API",
                    user_message="ICC API is temporarily unavailable."
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Transform ICC API response to SQL agent format
            formatted_definition = format_table_definition_from_api(
                table_name=table,
                schema=schema,
                connection=connection_name or connection_id,
                api_response=data
            )
            
            if formatted_definition:
                logger.info(f"Successfully fetched and formatted definition for {table} ({len(formatted_definition)} chars)")
                return formatted_definition
            else:
                logger.warning(f"Empty definition returned for {connection_id}.{schema}.{table}")
                return None
                
        except Timeout as e:
            logger.error(f"API timeout fetching {connection}.{schema}.{table}")
            raise NetworkTimeoutError(
                message=f"Timeout fetching table definition for {table}",
                user_message="The table definition request timed out. Please try again.",
                timeout_seconds=self.timeout,
                cause=e
            )
            
        except RequestsConnectionError as e:
            logger.error(f"Connection error fetching {connection}.{schema}.{table}: {e}")
            raise APIUnavailableError(
                message=f"Connection error fetching table definition: {e}",
                user_message="Unable to connect to the table definition service.",
                service_name="Table Definition API",
                cause=e
            )
            
        except RequestException as e:
            logger.error(f"API error fetching {connection}.{schema}.{table}: {str(e)}")
            raise HTTPError(
                message=f"HTTP error fetching table definition: {e}",
                user_message="Failed to fetch table definition. Please try again.",
                cause=e
            )
    
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
        successful = 0
        
        logger.info(f"Fetching {len(tables)} table definitions from API")
        
        for table in tables:
            definition = self.fetch_table_definition(connection, schema, table)
            if definition:
                definitions.append(definition)
                definitions.append("\n" + "=" * 80 + "\n")  # Separator
                successful += 1
        
        combined = "\n".join(definitions)
        
        logger.info(f"Successfully fetched {successful}/{len(tables)} table definitions")
        
        if successful == 0 and len(tables) > 0:
            logger.warning("No table definitions were fetched successfully")
        
        return combined
    
    def fetch_multiple_tables_batch(
        self,
        connection: str,
        schema: str,
        tables: List[str]
    ) -> str:
        """
        Fetch definitions for multiple tables using a batch API endpoint.
        
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
            logger.info("Mock mode: using individual table fetches")
            return self.fetch_multiple_tables(connection, schema, tables)
        
        batch_url = f"{self.base_url}/batch"
        
        try:
            return self._fetch_batch_with_retry(batch_url, connection, schema, tables)
        except Exception as e:
            logger.warning(f"Batch API not available or failed: {e}")
            logger.info("Falling back to individual API calls")
            return self.fetch_multiple_tables(connection, schema, tables)
    
    def _fetch_batch_with_retry(
        self,
        batch_url: str,
        connection: str,
        schema: str,
        tables: List[str]
    ) -> str:
        """Fetch batch table definitions with retry."""
        def do_batch_fetch():
            return self._do_batch_request(batch_url, connection, schema, tables)
        
        return retry_sync_operation(do_batch_fetch, config=TABLE_API_RETRY_CONFIG)
    
    def _do_batch_request(
        self,
        batch_url: str,
        connection: str,
        schema: str,
        tables: List[str]
    ) -> str:
        """Execute batch request."""
        logger.info(f"Attempting batch fetch for {len(tables)} tables")
        
        payload = {
            "connection": connection,
            "schema": schema,
            "tables": tables
        }
        
        response = requests.post(batch_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        
        definitions = []
        for item in data.get("definitions", []):
            definition = item.get("definition", "")
            if definition:
                definitions.append(definition)
                definitions.append("\n" + "=" * 80 + "\n")
        
        combined = "\n".join(definitions)
        
        logger.info(f"Batch fetch successful: {len(definitions) // 2} tables")
        return combined
    
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
        except Exception:
            return False


# Global instance (will be initialized with auth when needed)
table_api_client = TableAPIClient()


def get_table_api_client() -> TableAPIClient:
    """Get the global table API client instance."""
    return table_api_client


def set_table_api_auth(auth_headers: Dict[str, str]) -> None:
    """
    Set authentication headers for the global table API client.
    
    Args:
        auth_headers: Dictionary with Authorization and TokenKey headers
    """
    global table_api_client
    table_api_client.auth_headers = auth_headers
    logger.info("Updated table API client auth headers")


# Convenience functions
def fetch_table_definitions(
    connection: str,
    schema: str,
    tables: List[str],
    connection_id: str = None,
    use_batch: bool = False  # ICC API doesn't support batch yet
) -> str:
    """
    Fetch table definitions from ICC API.
    
    Args:
        connection: Connection name (for mock mode)
        schema: Schema name
        tables: List of table names
        connection_id: Connection ID for ICC API (required for real API)
        use_batch: Whether to use batch API if available (not implemented yet)
        
    Returns:
        Combined string with all table definitions
    """
    # For now, always use individual calls since ICC API doesn't have batch endpoint yet
    definitions = []
    successful = 0
    
    logger.info(f"Fetching {len(tables)} table definitions")
    
    for table in tables:
        definition = table_api_client.fetch_table_definition(
            connection_id=connection_id or connection,  # Use connection_id if available, else connection name for mock
            schema=schema,
            table=table,
            connection_name=connection
        )
        if definition:
            definitions.append(definition)
            definitions.append("\n" + "=" * 80 + "\n")  # Separator
            successful += 1
    
    combined = "\n".join(definitions)
    
    logger.info(f"Successfully fetched {successful}/{len(tables)} table definitions")
    
    if successful == 0 and len(tables) > 0:
        logger.warning("No table definitions were fetched successfully")
    
    return combined
