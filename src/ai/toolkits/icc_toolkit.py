from typing import List
import uuid
from httpx import AsyncClient
from src.models.natural_language import (
    SendEmailLLMRequest,
    ReadSqlLLMRequest,
    WriteDataLLMRequest,
)
from src.payload_builders.wire_builder import build_wire_payload
from src.repositories.job_repository import JobRepository
from src.utils.auth import authenticate



async def write_data_job(data: WriteDataLLMRequest) -> dict:
    """
    Create a job to write data using the JobRepository.
    Use this to initiate data writing tasks.
    
    IMPORTANT: This tool writes data from a previously executed read_sql_job.
    - data_set: Should be the job_id returned from read_sql_job
    - columns: Should match the columns from read_sql_job results
    
    Args:
        data (WriteDataPayload): Payload containing data to be written.
    Returns:
        dict: Confirmation message and job details.

    """
    if not data.id:
        data.id = str(uuid.uuid4())

    # Authenticate and create HTTP client with both Basic Auth and TokenKey headers
    auth_result = await authenticate()
    if auth_result:
        userpass, token = auth_result
        headers = {
            "Authorization": f"Basic {userpass}",
            "TokenKey": token
        }
    else:
        headers = {}
    
    async with AsyncClient(headers=headers, verify=False) as client:
        repo = JobRepository(client)
        await JobRepository.write_data_job(repo, data)
    return {"message": "Success", "data": data.model_dump()}


async def read_sql_job(data: ReadSqlLLMRequest) -> dict:
    """
    Create a job to read SQL data using the JobRepository.
    Use this to initiate SQL data reading tasks.
    
    IMPORTANT: This tool returns both a job_id and column names.
    - job_id: Use this as the 'data_set' parameter when calling write_data_job
    - columns: Use these as the 'columns' parameter when calling write_data_job
    
    Args:
        data (ReadSqlPayload): Payload containing SQL read parameters.
    Returns:
        dict: Contains:
            - message: Success status
            - job_id: The created job ID (use as data_set in write_data_job)
            - columns: List of column names from the query (use in write_data_job)
            - query: The SQL query that was executed

    """
    if not data.id:
        data.id = str(uuid.uuid4())
    
    # Authenticate and create HTTP client with both Basic Auth and TokenKey headers
    auth_result = await authenticate()
    if auth_result:
        userpass, token = auth_result
        headers = {
            "Authorization": f"Basic {userpass}",
            "TokenKey": token
        }
    else:
        headers = {}
    
    async with AsyncClient(headers=headers, verify=False) as client:
        repo = JobRepository(client)
        response, columns = await JobRepository.read_sql_job(repo, data)
    
    if response.success:
        return {
            "message": "Success",
            "job_id": response.data.object_id,
            "columns": columns,
            "query": data.variables[0].query,
            "connection": data.variables[0].connection
        }
    else:
        return {
            "message": "Error",
            "error": response.error,
            "columns": columns
        }


async def send_email_job(data: SendEmailLLMRequest) -> dict:
    """
    Create a job to send an email using the JobRepository.
    Use this to initiate email sending tasks.
    Args:
        data (SendEmailPayload): Payload containing email parameters.
    Returns:
        dict: Confirmation message and job details.
    """
    if not data.id:
        data.id = str(uuid.uuid4())

    # Authenticate and create HTTP client with both Basic Auth and TokenKey headers
    auth_result = await authenticate()
    if auth_result:
        userpass, token = auth_result
        headers = {
            "Authorization": f"Basic {userpass}",
            "TokenKey": token
        }
    else:
        headers = {}
    
    async with AsyncClient(headers=headers, verify=False) as client:
        repo = JobRepository(client)
        await JobRepository.send_email_job(repo, data)
    return {"message": "Success", "data": data.model_dump()}


class ICCToolkit:
    @staticmethod
    def get_tools() -> List:
        """
        Get the list of tools provided by the ICC Toolkit.
        Returns:
            List: A list of tool functions available in the ICC Toolkit.

        """
        return [
            write_data_job,
            read_sql_job,
            send_email_job,
        ]
