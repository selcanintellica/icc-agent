"""
Refactored Query Builder using Dependency Injection.

Builds query payloads with injected ConnectionResolver.
"""

import logging
from typing import Optional

from src.models.query import QueryPayload
from src.models.natural_language import SendEmailLLMRequest, ReadSqlLLMRequest
from .services.connection_resolver import ConnectionResolver

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Builder for query payloads.
    
    Follows DIP - depends on ConnectionResolver abstraction.
    Follows SRP - only handles query payload building.
    """
    
    def __init__(self, connection_resolver: Optional[ConnectionResolver] = None):
        """
        Initialize query builder.
        
        Args:
            connection_resolver: Connection resolver (creates new if not provided)
        """
        self._resolver = connection_resolver or ConnectionResolver()
    
    async def build_send_email_query_payload(
        self,
        data: SendEmailLLMRequest
    ) -> QueryPayload:
        """
        Build query payload for SendEmail request.
        
        Args:
            data: SendEmail request with connection and query
            
        Returns:
            QueryPayload: Built query payload
        """
        connection_name = data.variables[0].connection
        connection_id = self._resolver.resolve_connection_id(connection_name)
        
        logger.info(
            f"SendEmail query: connection '{connection_name}' -> '{connection_id}'"
        )
        
        sql = data.variables[0].query
        folder_id = ""
        
        return QueryPayload(
            connectionId=connection_id,
            sql=sql,
            folderId=folder_id
        )
    
    async def build_read_sql_query_payload(
        self,
        data: ReadSqlLLMRequest
    ) -> QueryPayload:
        """
        Build query payload for ReadSQL request.
        
        Args:
            data: ReadSQL request with connection and query
            
        Returns:
            QueryPayload: Built query payload
        """
        connection_name = data.variables[0].connection
        connection_id = self._resolver.resolve_connection_id(connection_name)
        
        logger.info(
            f"ReadSQL query: connection '{connection_name}' -> '{connection_id}'"
        )
        
        sql = data.variables[0].query
        folder_id = ""
        
        payload = QueryPayload(
            connectionId=connection_id,
            sql=sql,
            folderId=folder_id
        )
        
        logger.debug(
            f"Built QueryPayload: connectionId='{payload.connectionId}', "
            f"sql='{sql[:100]}...', folderId='{folder_id}'"
        )
        
        return payload


# Global builder instance (singleton pattern)
_builder: Optional[QueryBuilder] = None


def get_query_builder() -> QueryBuilder:
    """
    Get global query builder instance.
    
    Returns:
        QueryBuilder: Global builder instance
    """
    global _builder
    
    if _builder is None:
        _builder = QueryBuilder()
        logger.info("Created global QueryBuilder instance")
    
    return _builder
