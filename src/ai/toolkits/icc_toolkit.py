"""
ICC Toolkit - Refactored with SOLID principles and comprehensive error handling.

This module provides tools for ICC job operations following SOLID principles:
- Single Responsibility: Each function has one clear purpose
- Open/Closed: Easy to extend with new tools
- Dependency Inversion: Depends on service abstractions
"""

from typing import List, Optional
import uuid
import logging

from src.models.natural_language import (
    SendEmailLLMRequest,
    ReadSqlLLMRequest,
    WriteDataLLMRequest,
    CompareSqlLLMRequest,
)
from src.repositories.job_repository import JobRepository
from src.ai.toolkits.services import HTTPClientManager
from src.errors import (
    ICCBaseError,
    JobError,
    JobCreationFailedError,
    DuplicateJobNameError,
    NetworkTimeoutError,
    APIUnavailableError,
    AuthenticationError,
    ErrorHandler,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class JobToolExecutor:
    """
    Executes job tool operations using dependency injection.
    
    Following SOLID principles:
    - Single Responsibility: Only executes jobs
    - Dependency Inversion: Depends on HTTPClientManager abstraction
    """
    
    def __init__(self, client_manager: Optional[HTTPClientManager] = None):
        """
        Initialize job tool executor.
        
        Args:
            client_manager: HTTP client manager (creates default if None)
        """
        self.client_manager = client_manager or HTTPClientManager()
    
    async def execute_write_data_job(self, data: WriteDataLLMRequest) -> dict:
        """
        Execute a write data job with error handling.
        
        Args:
            data: Write data request payload
            
        Returns:
            dict: Job execution result
        """
        job_name = data.props.get("name", "WriteData_Job") if hasattr(data, "props") and data.props else "WriteData_Job"
        
        try:
            if not data.id:
                data.id = str(uuid.uuid4())
            
            async with self.client_manager.get_authenticated_client() as client:
                repo = JobRepository(client)
                await repo.write_data_job(data)
            
            logger.info(f"Write data job executed successfully: {data.id}")
            return {"message": "Success", "data": data.model_dump()}
        
        except DuplicateJobNameError:
            # Re-raise to let handler deal with it and enable retry with new name
            raise
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout for WriteData job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except APIUnavailableError as e:
            logger.error(f"API unavailable for WriteData job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except AuthenticationError as e:
            logger.error(f"Authentication error for WriteData job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except ICCBaseError as e:
            logger.error(f"ICC error in WriteData job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except Exception as e:
            logger.error(f"Unexpected error in WriteData job: {type(e).__name__}: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"job_type": "WriteData", "job_name": job_name})
            return {"message": "Error", "error": icc_error.user_message}
    
    async def execute_read_sql_job(self, data: ReadSqlLLMRequest) -> dict:
        """
        Execute a read SQL job with error handling.
        
        Args:
            data: Read SQL request payload
            
        Returns:
            dict: Job execution result with job_id and columns
        """
        job_name = data.props.get("name", "ReadSQL_Job") if hasattr(data, "props") and data.props else "ReadSQL_Job"
        
        try:
            if not data.id:
                data.id = str(uuid.uuid4())
            
            async with self.client_manager.get_authenticated_client() as client:
                repo = JobRepository(client)
                response, columns = await repo.read_sql_job(data)
            
            if response.success:
                logger.info(f"Read SQL job executed successfully: {response.data.object_id}")
                return {
                    "message": "Success",
                    "job_id": response.data.object_id,
                    "columns": columns,
                    "query": data.variables[0].query,
                    "connection": data.variables[0].connection
                }
            else:
                error_msg = response.error or "Unknown error"
                logger.error(f"Read SQL job failed: {error_msg}")
                
                # Check for duplicate name error (raise exception to let handler deal with it)
                error_lower = error_msg.lower()
                if "same name" in error_lower or "already exists" in error_lower:
                    raise DuplicateJobNameError(
                        job_name=job_name,
                        message=error_msg,
                        user_message=f"A job named '{job_name}' already exists. Please choose a different name."
                    )
                
                return {
                    "message": "Error",
                    "error": error_msg,
                    "columns": columns
                }
        
        except DuplicateJobNameError:
            # Re-raise to let handler deal with it and enable retry with new name
            raise
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout for ReadSQL job: {e}")
            return {"message": "Error", "error": e.user_message, "columns": []}
        
        except APIUnavailableError as e:
            logger.error(f"API unavailable for ReadSQL job: {e}")
            return {"message": "Error", "error": e.user_message, "columns": []}
        
        except AuthenticationError as e:
            logger.error(f"Authentication error for ReadSQL job: {e}")
            return {"message": "Error", "error": e.user_message, "columns": []}
        
        except ICCBaseError as e:
            logger.error(f"ICC error in ReadSQL job: {e}")
            return {"message": "Error", "error": e.user_message, "columns": []}
        
        except Exception as e:
            logger.error(f"Unexpected error in ReadSQL job: {type(e).__name__}: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"job_type": "ReadSQL", "job_name": job_name})
            return {"message": "Error", "error": icc_error.user_message, "columns": []}
    
    async def execute_send_email_job(self, data: SendEmailLLMRequest) -> dict:
        """
        Execute a send email job with error handling.
        
        Args:
            data: Send email request payload
            
        Returns:
            dict: Job execution result
        """
        job_name = data.props.get("name", "Email_Job") if hasattr(data, "props") and data.props else "Email_Job"
        
        try:
            if not data.id:
                data.id = str(uuid.uuid4())
            
            async with self.client_manager.get_authenticated_client() as client:
                repo = JobRepository(client)
                await repo.send_email_job(data)
            
            logger.info(f"Send email job executed successfully: {data.id}")
            return {"message": "Success", "data": data.model_dump()}
        
        except DuplicateJobNameError:
            # Re-raise to let handler deal with it and enable retry with new name
            raise
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout for SendEmail job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except APIUnavailableError as e:
            logger.error(f"API unavailable for SendEmail job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except AuthenticationError as e:
            logger.error(f"Authentication error for SendEmail job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except ICCBaseError as e:
            logger.error(f"ICC error in SendEmail job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except Exception as e:
            logger.error(f"Unexpected error in SendEmail job: {type(e).__name__}: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"job_type": "SendEmail", "job_name": job_name})
            return {"message": "Error", "error": icc_error.user_message}
    
    async def execute_compare_sql_job(self, data: CompareSqlLLMRequest) -> dict:
        """
        Execute a compare SQL job with error handling.
        
        Args:
            data: Compare SQL request payload
            
        Returns:
            dict: Job execution result
        """
        job_name = data.props.get("name", "CompareSQL_Job") if hasattr(data, "props") and data.props else "CompareSQL_Job"
        
        try:
            if not data.id:
                data.id = str(uuid.uuid4())
            
            async with self.client_manager.get_authenticated_client() as client:
                repo = JobRepository(client)
                response = await repo.compare_sql_job(data)
            
            if response.success:
                logger.info(f"Compare SQL job executed successfully: {response.data.object_id}")
                return {
                    "message": "Success",
                    "job_id": response.data.object_id,
                    "data": data.model_dump()
                }
            else:
                error_msg = response.error or "Unknown error"
                logger.error(f"Compare SQL job failed: {error_msg}")
                
                # Check for duplicate name error (raise exception to let handler deal with it)
                error_lower = error_msg.lower()
                if "same name" in error_lower or "already exists" in error_lower:
                    raise DuplicateJobNameError(
                        job_name=job_name,
                        message=error_msg,
                        user_message=f"A job named '{job_name}' already exists. Please choose a different name."
                    )
                
                return {
                    "message": "Error",
                    "error": error_msg
                }
        
        except DuplicateJobNameError:
            # Re-raise to let handler deal with it and enable retry with new name
            raise
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout for CompareSQL job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except APIUnavailableError as e:
            logger.error(f"API unavailable for CompareSQL job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except AuthenticationError as e:
            logger.error(f"Authentication error for CompareSQL job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except ICCBaseError as e:
            logger.error(f"ICC error in CompareSQL job: {e}")
            return {"message": "Error", "error": e.user_message}
        
        except Exception as e:
            logger.error(f"Unexpected error in CompareSQL job: {type(e).__name__}: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"job_type": "CompareSQL", "job_name": job_name})
            return {"message": "Error", "error": icc_error.user_message}


# Global executor instance
_executor: Optional[JobToolExecutor] = None


def get_executor() -> JobToolExecutor:
    """Get or create singleton executor."""
    global _executor
    if _executor is None:
        _executor = JobToolExecutor()
    return _executor


# Tool functions for backward compatibility
async def write_data_job(data: WriteDataLLMRequest) -> dict:
    """
    Create a job to write data using the JobRepository.
    Use this to initiate data writing tasks.
    
    IMPORTANT: This tool writes data from a previously executed read_sql_job.
    - data_set: Should be the job_id returned from read_sql_job
    - columns: Should match the columns from read_sql_job results
    
    Args:
        data: Payload containing data to be written.
    Returns:
        dict: Confirmation message and job details.
    """
    return await get_executor().execute_write_data_job(data)


async def read_sql_job(data: ReadSqlLLMRequest) -> dict:
    """
    Create a job to read SQL data using the JobRepository.
    Use this to initiate SQL data reading tasks.
    
    IMPORTANT: This tool returns both a job_id and column names.
    - job_id: Use this as the 'data_set' parameter when calling write_data_job
    - columns: Use these as the 'columns' parameter when calling write_data_job
    
    Args:
        data: Payload containing SQL read parameters.
    Returns:
        dict: Contains:
            - message: Success status
            - job_id: The created job ID (use as data_set in write_data_job)
            - columns: List of column names from the query (use in write_data_job)
            - query: The SQL query that was executed
    """
    return await get_executor().execute_read_sql_job(data)


async def send_email_job(data: SendEmailLLMRequest) -> dict:
    """
    Create a job to send an email using the JobRepository.
    Use this to initiate email sending tasks.
    Args:
        data: Payload containing email parameters.
    Returns:
        dict: Confirmation message and job details.
    """
    return await get_executor().execute_send_email_job(data)


async def compare_sql_job(data: CompareSqlLLMRequest) -> dict:
    """
    Create a job to compare two SQL queries using the JobRepository.
    
    Args:
        data: Payload containing compare SQL parameters.
    Returns:
        dict: Confirmation message and job details.
    """
    return await get_executor().execute_compare_sql_job(data)


class ICCToolkit:
    """
    ICC Toolkit provides tools for the ICC Agent.
    
    Following SOLID principles:
    - Single Responsibility: Only responsible for providing ICC-specific tools
    - Open/Closed: Easy to extend with new tools without modifying existing code
    - Dependency Inversion: Uses injected executor
    """
    
    def __init__(self, executor: Optional[JobToolExecutor] = None):
        """
        Initialize ICC Toolkit.
        
        Args:
            executor: Job tool executor (uses singleton if None)
        """
        self.executor = executor or get_executor()
        self._tools = [
            write_data_job,
            read_sql_job,
            send_email_job,
            compare_sql_job,
        ]
    
    def get_tools(self) -> List:
        """
        Get the list of tools provided by the ICC Toolkit.
        
        Returns:
            List: A list of tool functions available in the ICC Toolkit.
        """
        return self._tools
    
    def add_tool(self, tool) -> None:
        """
        Add a new tool to the toolkit.
        
        Args:
            tool: A callable tool function to add
        """
        if callable(tool):
            self._tools.append(tool)
            logger.info(f"Added tool: {tool.__name__}")
        else:
            raise ValueError("Tool must be callable")
    
    def remove_tool(self, tool) -> None:
        """
        Remove a tool from the toolkit.
        
        Args:
            tool: The tool function to remove
        """
        if tool in self._tools:
            self._tools.remove(tool)
            logger.info(f"Removed tool: {tool.__name__}")
