import logging
from typing import Optional
from src.models import WirePayload
from src.models import QueryPayload
from src.models import APIResponse, JobResponse
from src.utils.config import API_CONFIG
from src.repositories.base_repository import BaseRepository

from src.payload_builders.wire_builder import WireBuilder
from src.payload_builders.query_builder import QueryBuilder
from src.repositories.services import ColumnFetchingService, CompareSQLColumnGenerator

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """
    Repository for handling job-related API operations.
    
    NOTE: Use JobRepositoryFactory.create() or create_job_repository() 
    to instantiate this class with proper dependency injection.
    
    Following SOLID principles:
    - Single Responsibility: Only handles job API operations
    - Dependency Inversion: All dependencies injected via constructor
    """
    
    def __init__(
        self,
        client,
        wire_builder: WireBuilder,
        query_builder: QueryBuilder,
        column_service: ColumnFetchingService
    ):
        """
        Initialize with required injected dependencies.
        
        Args:
            client: HTTP client for API calls
            wire_builder: Builder for wire payloads
            query_builder: Builder for query payloads
            column_service: Service for fetching column information
        """
        super().__init__(client)
        self.wire_builder = wire_builder
        self.query_builder = query_builder
        self.column_service = column_service

    async def write_data_job(self, data) -> APIResponse[JobResponse]:
        wire = self.wire_builder.build_wire_payload(data)

        logger.info(f"Creating write data job: {data.template}")
        logger.info(f"📦 Wire payload being sent to API:")
        logger.info(f"{wire.model_dump(exclude_none=True, by_alias=True)}")
        
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        return response

    async def read_sql_job(self, data) -> tuple[APIResponse[JobResponse], list[str]]:
        """
        Execute a read SQL job and return both the job response and column names.
        
        Returns:
            tuple: (APIResponse[JobResponse], list[str]) 
                   - API response with job_id
                   - List of column names from the query
        """
        query_payload = await self.query_builder.build_read_sql_query_payload(data)
        
        # Use column service to fetch columns
        column_names = await self.column_service.get_columns_as_list(query_payload)

        wire = self.wire_builder.build_wire_payload(data, column_names=column_names)

        logger.info(f"Creating read SQL job: {data.template}")
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        
        logger.info(f"Read SQL job created. Job ID: {response.data.object_id if response.success else 'N/A'}, Columns: {column_names}")
        return response, column_names

    async def send_email_job(self, data) -> APIResponse[JobResponse]:
        wire = self.wire_builder.build_wire_payload(data)

        logger.info(f"Creating send email job: {data.template}")
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        return response

    async def compare_sql_job(self, data) -> APIResponse[JobResponse]:
        """
        Execute a compare SQL job.
        
        API structure uses COMMA-SEPARATED STRINGS:
        - first_table_keys: comma-separated key column names (e.g., "EMPLOYEE_ID")
        - second_table_keys: comma-separated key column names (e.g., "EMPLOYEE_ID")
        - first_table_columns: comma-separated ALL column names (e.g., "ID,NAME,EMAIL")
        - second_table_columns: comma-separated ALL column names (e.g., "ID,NAME,EMAIL")
        - columns_output: fixed structure with 3 key columns each
        """
        var = data.variables[0]
        
        # Generate columns_output with fixed structure (always 3 key columns each)
        if not var.columns_output:
            var.columns_output = CompareSQLColumnGenerator.generate_columns_output()

        wire = self.wire_builder.build_wire_payload(data)
        
        logger.info(f"Creating compare SQL job: {data.template}")
        logger.info(f"First table keys: {var.first_table_keys}")
        logger.info(f"Second table keys: {var.second_table_keys}")
        logger.info(f"First table columns: {var.first_table_columns}")
        logger.info(f"Second table columns: {var.second_table_columns}")
        endpoint = ""
        response = await self.post_request(endpoint, wire, JobResponse)
        return response
