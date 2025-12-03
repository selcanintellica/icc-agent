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
        
        New API structure:
        - map_table: JSON array of column mappings [{"FirstMappedColumn": "...", "SecondMappedColumn": "..."}]
        - keys: JSON array of key pairs [{"FirstKey": "...", "SecondKey": "..."}]
        - columns_output: generated based on keys structure
        """
        import json
        
        var = data.variables[0]
        
        # Dynamically generate columns_output based on keys
        if not var.columns_output:
            # Parse keys JSON to extract first/second table keys for columns_output generation
            first_keys = ""
            second_keys = ""
            if var.keys:
                try:
                    keys_list = json.loads(var.keys) if isinstance(var.keys, str) else var.keys
                    first_keys = ",".join([k.get("FirstKey", "") for k in keys_list if k.get("FirstKey")])
                    second_keys = ",".join([k.get("SecondKey", "") for k in keys_list if k.get("SecondKey")])
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Could not parse keys JSON, using empty keys for columns_output")
            
            var.columns_output = CompareSQLColumnGenerator.generate_columns_output(
                first_table_keys=first_keys,
                second_table_keys=second_keys
            )

        wire = self.wire_builder.build_wire_payload(data)
        
        logger.info(f"Creating compare SQL job: {data.template}")
        logger.info(f"Keys: {var.keys}")
        logger.info(f"Map table: {var.map_table}")
        endpoint = ""
        response = await self.post_request(endpoint, wire, JobResponse)
        return response
