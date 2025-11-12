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
        endpoint = f"{API_CONFIG['api_base_url']}"
        response = await self.post_request(endpoint, wire, JobResponse)
        return response

    @staticmethod
    async def read_sql_job(self, data) -> APIResponse[JobResponse]:

        query_payload = QueryBuilder.build_send_email_query_payload(data)
        column_names = QueryRepository.get_column_names(query_payload)

        wire = build_wire_payload(data, column_names=column_names)

        logger.info(f"Creating read SQL job: {data.template}")
        endpoint = f"{API_CONFIG['api_base_url']}"
        response = await self.post_request(endpoint, wire, JobResponse)
        return response

    @staticmethod
    async def send_email_job(self, data) -> APIResponse[JobResponse]:
        wire = build_wire_payload(data)

        logger.info(f"Creating send email job: {data.template}")
        endpoint = f"{API_CONFIG['api_base_url']}"
        response = await self.post_request(endpoint, wire, JobResponse)
        return response


