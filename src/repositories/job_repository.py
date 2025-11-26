import json
import logging
from src.models.wire import WirePayload
from src.models.query import QueryPayload
from src.models.save_job_response import APIResponse, JobResponse
from src.utils.config import API_CONFIG
from src.repositories.base_repository import BaseRepository

from src.payload_builders.wire_builder import build_wire_payload
from src.payload_builders.query_builder import QueryBuilder
from src.repositories.query_repository import QueryRepository

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Repository for handling job-related API operations"""

    @staticmethod
    async def write_data_job(self, data) -> APIResponse[JobResponse]:
        wire = build_wire_payload(data)

        logger.info(f"Creating write data job: {data.template}")
        logger.info(f"📦 Wire payload being sent to API:")
        logger.info(f"{wire.model_dump(exclude_none=True, by_alias=True)}")
        
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

    @staticmethod
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
            col_resp1 = await QueryRepository.get_column_names(self, query_payload1)
            cols1 = col_resp1.data.object.columns if col_resp1.success else []
            var.first_table_columns = ",".join(cols1)
        
        if not var.second_table_columns:
            query_payload2 = QueryPayload(connectionId=conn_id, sql=sql2, folderId="")
            col_resp2 = await QueryRepository.get_column_names(self, query_payload2)
            cols2 = col_resp2.data.object.columns if col_resp2.success else []
            var.second_table_columns = ",".join(cols2)
        
        # Dynamically generate columns_output based on keys
        if not var.columns_output:
            output_cols = [
                {"columnName": "FIRST_SQL_QUERY"},
                {"columnName": "FIRST_TABLE_KEYS"}
            ]
            
            # Add columns for first table keys
            first_keys_list = [k.strip() for k in var.first_table_keys.split(",") if k.strip()]
            for i, _ in enumerate(first_keys_list, 1):
                output_cols.append({"columnName": f"FIRST_KEY_{i}"})
                
            output_cols.extend([
                {"columnName": "FIRST_COLUMN"},
                {"columnName": "FIRST_VALUE"},
                {"columnName": "FIRST_TABLE_COUNT"},
                {"columnName": "SECOND_SQL_QUERY"},
                {"columnName": "SECOND_TABLE_KEYS"}
            ])
            
            # Add columns for second table keys
            second_keys_list = [k.strip() for k in var.second_table_keys.split(",") if k.strip()]
            for i, _ in enumerate(second_keys_list, 1):
                output_cols.append({"columnName": f"SECOND_KEY_{i}"})
                
            output_cols.extend([
                {"columnName": "SECOND_COLUMN"},
                {"columnName": "SECOND_VALUE"},
                {"columnName": "SECOND_TABLE_COUNT"}
            ])
            
            var.columns_output = json.dumps(output_cols)

        wire = build_wire_payload(data)
        
        logger.info(f"Creating compare SQL job: {data.template}")
        logger.info(f"Keys mapping: {var.keys_mapping}")
        logger.info(f"Column mapping: {var.column_mapping}")
        endpoint = ""
        response = await self.post_request(endpoint, wire, JobResponse)
        return response
