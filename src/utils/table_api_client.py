"""
API client for fetching table definitions from external API.

This module provides table definition fetching with:
- Retry logic for transient failures
- Mock mode support for testing
- Structured error handling
"""

import os
import logging
from typing import List, Optional

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
    Client for fetching table definitions from API with retry support.
    
    Supports mock mode via TABLE_API_MOCK environment variable for testing.
    """
    
    def __init__(self, base_url: Optional[str] = None, use_mock: Optional[bool] = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the table definitions API.
                     If None, reads from TABLE_API_BASE_URL environment variable.
            use_mock: Whether to use mock data instead of API calls.
                     If None, reads from TABLE_API_MOCK environment variable.
        """
        self.base_url = base_url or os.getenv(
            "TABLE_API_BASE_URL",
            "http://localhost:8000/api/tables"
        )
        self.timeout = int(os.getenv("TABLE_API_TIMEOUT", "10"))
        
        # Check if mock mode is enabled
        if use_mock is None:
            mock_env = os.getenv("TABLE_API_MOCK", "false").lower()
            self.use_mock = mock_env in ("true", "1", "yes")
        else:
            self.use_mock = use_mock
        
        if self.use_mock:
            logger.info("TableAPIClient initialized in MOCK mode")
        else:
            logger.info(f"TableAPIClient initialized with base URL: {self.base_url}")
    
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
            logger.info(f"Using mock data for: {connection}.{schema}.{table}")
            definition = get_mock_table_definition(connection, schema, table)
            
            if definition:
                logger.info(f"Mock data found for {table} ({len(definition)} chars)")
            else:
                logger.warning(f"No mock data found for {connection}.{schema}.{table}")
            
            return definition
        
        # Real API call with retry
        url = f"{self.base_url}/{connection}/{schema}/{table}"
        
        try:
            return self._fetch_with_retry(url, connection, schema, table)
        except Exception as e:
            # Log but don't raise - return None to allow graceful degradation
            logger.error(f"Failed to fetch table definition for {connection}.{schema}.{table}: {e}")
            return None
    
    def _fetch_with_retry(
        self,
        url: str,
        connection: str,
        schema: str,
        table: str
    ) -> Optional[str]:
        """Fetch table definition with retry logic."""
        def do_fetch():
            return self._do_fetch_request(url, connection, schema, table)
        
        try:
            return retry_sync_operation(do_fetch, config=TABLE_API_RETRY_CONFIG)
        except Exception as e:
            # Handle retry exhaustion gracefully
            logger.warning(f"Table definition fetch failed after retries: {e}")
            return None
    
    def _do_fetch_request(
        self,
        url: str,
        connection: str,
        schema: str,
        table: str
    ) -> Optional[str]:
        """Execute the actual HTTP request."""
        logger.info(f"Fetching table definition from API: {connection}.{schema}.{table}")
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.warning(f"Table not found: {connection}.{schema}.{table}")
                return None
            
            if response.status_code >= 500:
                # Server error - will be retried
                raise APIUnavailableError(
                    message=f"Server error {response.status_code} from table API",
                    user_message="Table definition service is temporarily unavailable."
                )
            
            response.raise_for_status()
            data = response.json()
            
            definition = data.get("definition", "")
            
            if definition:
                logger.info(f"Successfully fetched definition for {table} ({len(definition)} chars)")
                return definition
            else:
                logger.warning(f"Empty definition returned for {connection}.{schema}.{table}")
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
