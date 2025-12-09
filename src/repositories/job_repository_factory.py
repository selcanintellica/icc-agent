"""
Factory for creating JobRepository instances with proper dependency injection.

Follows SOLID principles:
- Single Responsibility: Only creates and configures JobRepository instances
- Open/Closed: Easy to extend with new configuration options
- Dependency Inversion: Abstracts repository creation logic
"""

import logging
from typing import Optional
from httpx import AsyncClient

from src.repositories.job_repository import JobRepository
from src.payload_builders.wire_builder import get_wire_builder, WireBuilder
from src.payload_builders.query_builder import get_query_builder, QueryBuilder
from src.repositories.services import ColumnFetchingService

logger = logging.getLogger(__name__)


class JobRepositoryFactory:
    """
    Factory for creating fully configured JobRepository instances.
    
    Reduces coupling by centralizing dependency creation and injection.
    Follows the Factory pattern to encapsulate complex object creation.
    """
    
    @staticmethod
    def create(
        client: AsyncClient,
        wire_builder: Optional[WireBuilder] = None,
        query_builder: Optional[QueryBuilder] = None,
        column_service: Optional[ColumnFetchingService] = None
    ) -> JobRepository:
        """
        Create a JobRepository with all dependencies injected.
        
        Args:
            client: HTTP client for API calls (required)
            wire_builder: Custom wire builder (optional, uses singleton if not provided)
            query_builder: Custom query builder (optional, uses singleton if not provided)
            column_service: Custom column service (optional, creates new if not provided)
            
        Returns:
            JobRepository: Fully configured repository instance
        """
        # Use provided dependencies or create defaults
        wire_builder = wire_builder or get_wire_builder()
        query_builder = query_builder or get_query_builder()
        column_service = column_service or ColumnFetchingService(client)
        
        logger.debug("Creating JobRepository with injected dependencies")
        
        return JobRepository(
            client=client,
            wire_builder=wire_builder,
            query_builder=query_builder,
            column_service=column_service
        )
    
    @staticmethod
    def create_with_defaults(client: AsyncClient) -> JobRepository:
        """
        Create a JobRepository with all default dependencies.
        
        This is the most common use case - just provide a client
        and let the factory handle all dependency creation.
        
        Args:
            client: HTTP client for API calls
            
        Returns:
            JobRepository: Repository with default dependencies
        """
        return JobRepositoryFactory.create(client)


# Convenience function for the most common use case
def create_job_repository(client: AsyncClient) -> JobRepository:
    """
    Convenience function to create a JobRepository with default dependencies.
    
    Args:
        client: HTTP client for API calls
        
    Returns:
        JobRepository: Configured repository instance
    """
    return JobRepositoryFactory.create_with_defaults(client)
