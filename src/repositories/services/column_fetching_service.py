"""
Column Fetching Service.

Separates column name retrieval concern from job repositories.
Follows Single Responsibility Principle.
"""

import logging
from typing import List, Optional
from httpx import AsyncClient

from src.models.query import QueryPayload, QueryResponse
from src.models.save_job_response import APIResponse
from src.utils.config import API_CONFIG
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ColumnFetchingService(BaseRepository):
    """
    Service for fetching column names from SQL queries.
    
    Following SOLID principles:
    - Single Responsibility: Only handles column name fetching
    - Dependency Inversion: Depends on BaseRepository abstraction
    """
    
    def __init__(self, client: AsyncClient):
        """Initialize with HTTP client."""
        super().__init__(client)
    
    async def get_column_names(self, query_payload: QueryPayload) -> APIResponse[QueryResponse]:
        """
        Get column names by analyzing a SQL query.
        
        Args:
            query_payload: QueryPayload with connection and SQL query
            
        Returns:
            APIResponse[QueryResponse]: Response containing column names
        """
        endpoint = API_CONFIG['query_api_base_url']
        logger.debug(f"Fetching columns for query: {query_payload.sql[:100]}...")
        
        response = await self.post_request(endpoint, query_payload, QueryResponse)
        
        if response.success:
            columns = response.data.object.columns
            logger.info(f"✅ Fetched {len(columns)} columns")
        else:
            logger.error(f"❌ Failed to fetch columns: {response.error}")
        
        return response
    
    async def get_columns_as_list(self, query_payload: QueryPayload) -> List[str]:
        """
        Get column names as a simple list.
        
        Args:
            query_payload: QueryPayload with connection and SQL query
            
        Returns:
            List[str]: List of column names (empty if error)
        """
        response = await self.get_column_names(query_payload)
        return response.data.object.columns if response.success else []
    
    async def get_columns_as_comma_separated(self, query_payload: QueryPayload) -> str:
        """
        Get column names as comma-separated string.
        
        Args:
            query_payload: QueryPayload with connection and SQL query
            
        Returns:
            str: Comma-separated column names (empty if error)
        """
        columns = await self.get_columns_as_list(query_payload)
        return ",".join(columns)
