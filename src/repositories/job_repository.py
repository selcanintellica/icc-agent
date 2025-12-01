import logging
from typing import Optional
from src.models.wire import WirePayload
from src.models.query import QueryPayload
from src.models.save_job_response import APIResponse, JobResponse
from src.utils.config import API_CONFIG
from src.repositories.base_repository import BaseRepository

from src.payload_builders.wire_builder import get_wire_builder, WireBuilder
from src.payload_builders.query_builder import get_query_builder, QueryBuilder
from src.repositories.services import ColumnFetchingService, CompareSQLColumnGenerator

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Repository for handling job-related API operations with dependency injection."""
    
    def __init__(
        self,
        client,
        wire_builder: Optional[WireBuilder] = None,
        query_builder: Optional[QueryBuilder] = None,
        column_service: Optional[ColumnFetchingService] = None
    ):
        """Initialize with injected dependencies."""
        super().__init__(client)
        self.wire_builder = wire_builder or get_wire_builder()
        self.query_builder = query_builder or get_query_builder()
        self.column_service = column_service or ColumnFetchingService(client)

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
        Columns should already be populated from the router flow.
        Generates columns_output if not provided.
        """
        var = data.variables[0]
        conn_id = var.connection
        sql1 = var.first_sql_query
        sql2 = var.second_sql_query
        
        # Fetch columns only if not already provided
        if not var.first_table_columns:
            query_payload1 = QueryPayload(connectionId=conn_id, sql=sql1, folderId="")
            var.first_table_columns = await self.column_service.get_columns_as_comma_separated(query_payload1)
        
        if not var.second_table_columns:
            query_payload2 = QueryPayload(connectionId=conn_id, sql=sql2, folderId="")
            var.second_table_columns = await self.column_service.get_columns_as_comma_separated(query_payload2)
        
        # Dynamically generate columns_output based on keys
        if not var.columns_output:
            var.columns_output = CompareSQLColumnGenerator.generate_columns_output(
                first_table_keys=var.first_table_keys,
                second_table_keys=var.second_table_keys
            )

        wire = self.wire_builder.build_wire_payload(data)
        
        logger.info(f"Creating compare SQL job: {data.template}")
        logger.info(f"Keys mapping: {var.keys_mapping}")
        logger.info(f"Column mapping: {var.column_mapping}")
        endpoint = ""
        response = await self.post_request(endpoint, wire, JobResponse)
        return response
