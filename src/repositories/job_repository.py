from src.models.wire import WirePayload
from src.models.save_job_response import APIResponse, JobResponse
from src.utils.config import API_CONFIG
from src.repositories.base_repository import BaseRepository
from loguru import logger

from src.payload_builders.wire_builder import build_wire_payload
from src.payload_builders.query_builder import QueryBuilder
from src.repositories.query_repository import QueryRepository


class JobRepository(BaseRepository):
    """Repository for handling job-related API operations"""

    @staticmethod
    async def write_data_job(self, data) -> APIResponse[JobResponse]:
        wire = build_wire_payload(data)

        logger.info(f"Creating write data job: {data.template}")
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        return response

    @staticmethod
    async def read_sql_job(self, data) -> tuple[APIResponse[JobResponse], list[str]]:
        """
        Execute a read SQL job and return both the job response and column names.
        
        Returns:
            tuple: (APIResponse[JobResponse], list[str]) 
                   - API response with job_id
                   - List of column names from the query
        """
        query_payload = await QueryBuilder.build_read_sql_query_payload(data)
        column_response = await QueryRepository.get_column_names(self, query_payload)
        
        # Extract column names from the response
        column_names = column_response.data.object.columns if column_response.success else []

        wire = build_wire_payload(data, column_names=column_names)

        logger.info(f"Creating read SQL job: {data.template}")
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        
        logger.info(f"Read SQL job created. Job ID: {response.data.object_id if response.success else 'N/A'}, Columns: {column_names}")
        return response, column_names

    @staticmethod
    async def send_email_job(self, data) -> APIResponse[JobResponse]:
        wire = build_wire_payload(data)

        logger.info(f"Creating send email job: {data.template}")
        endpoint = ""  # Empty string since base_url already contains the full path
        response = await self.post_request(endpoint, wire, JobResponse)
        return response


