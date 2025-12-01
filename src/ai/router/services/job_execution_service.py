"""
Job Execution Service Layer.

This module provides service classes for executing jobs following SOLID principles:
- Single Responsibility: Each service handles one job type
- Open/Closed: Easy to extend with new job types
- Dependency Inversion: Depends on abstractions
"""

import json
import logging
from typing import Dict, Any, Protocol
from abc import ABC, abstractmethod

from src.ai.toolkits.icc_toolkit import read_sql_job, write_data_job, send_email_job, compare_sql_job
from src.models.natural_language import (
    ReadSqlLLMRequest,
    ReadSqlVariables,
    WriteDataLLMRequest,
    WriteDataVariables,
    SendEmailLLMRequest,
    SendEmailVariables,
    CompareSqlLLMRequest,
    CompareSqlVariables,
    ColumnSchema
)

logger = logging.getLogger(__name__)


class JobExecutionResult:
    """
    Result from job execution.
    
    Encapsulates the response with success/failure state.
    """
    
    def __init__(self, success: bool, data: Dict[str, Any], error: str = None):
        self.success = success
        self.data = data
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "data": self.data
        }
        if self.error:
            result["error"] = self.error
        return result


class JobExecutionService(ABC):
    """
    Abstract base class for job execution services.
    
    Following SOLID principles - defines interface for all job services.
    """
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> JobExecutionResult:
        """
        Execute the job with given parameters.
        
        Args:
            params: Job parameters
            
        Returns:
            JobExecutionResult: Result of execution
        """
        pass


class ReadSQLService(JobExecutionService):
    """
    Service for executing ReadSQL jobs.
    
    Following Single Responsibility Principle - only handles ReadSQL execution.
    """
    
    async def execute(self, params: Dict[str, Any]) -> JobExecutionResult:
        """
        Execute a ReadSQL job.
        
        Args:
            params: Must include:
                - name: Job name
                - query: SQL query
                - connection_id: Connection ID
                - execute_query: Boolean
                - write_count: Boolean
                And conditionally: result_schema, table_name, drop_before_create,
                write_count_schema, write_count_table, write_count_connection
                
        Returns:
            JobExecutionResult: Execution result
        """
        logger.info("⚡ ReadSQLService: Executing read_sql job...")
        
        try:
            execute_query = params.get("execute_query", False)
            write_count = params.get("write_count", False)
            
            read_sql_vars = ReadSqlVariables(
                query=params["query"],
                connection=params["connection_id"],
                execute_query=execute_query,
                write_count=write_count
            )
            
            if execute_query:
                read_sql_vars.result_schema = params.get("result_schema")
                read_sql_vars.table_name = params.get("table_name")
                read_sql_vars.drop_before_create = params.get("drop_before_create", False)
                read_sql_vars.only_dataset_columns = params.get("only_dataset_columns", False)
            
            if write_count:
                read_sql_vars.write_count_connection = params["write_count_connection_id"]
                read_sql_vars.write_count_schema = params.get("write_count_schema")
                read_sql_vars.write_count_table = params.get("write_count_table")
            
            request = ReadSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": params.get("name", "ReadSQL_Job"),
                    "description": ""
                },
                variables=[read_sql_vars]
            )
            
            result = await read_sql_job(request)
            
            logger.info(f"📊 ReadSQL result: {json.dumps(result, indent=2)}")
            
            if result.get("message") == "Success":
                return JobExecutionResult(
                    success=True,
                    data={
                        "job_id": result.get("job_id"),
                        "columns": result.get("columns", []),
                        "connection": result.get("connection")
                    }
                )
            else:
                return JobExecutionResult(
                    success=False,
                    data={},
                    error=result.get("error", "Unknown error")
                )
        
        except Exception as e:
            logger.error(f"❌ ReadSQL error: {str(e)}", exc_info=True)
            return JobExecutionResult(
                success=False,
                data={},
                error=str(e)
            )


class WriteDataService(JobExecutionService):
    """
    Service for executing WriteData jobs.
    
    Following Single Responsibility Principle - only handles WriteData execution.
    """
    
    async def execute(self, params: Dict[str, Any]) -> JobExecutionResult:
        """
        Execute a WriteData job.
        
        Args:
            params: Must include:
                - name: Job name
                - data_set: Job ID from previous read
                - data_set_job_name: ReadSQL job name
                - data_set_folder: ReadSQL job folder
                - columns: List of column names
                - connection_id: Connection ID
                - schemas: Schema name
                - table: Table name
                - drop_or_truncate: DROP/TRUNCATE/INSERT
                - write_count: Boolean
                And conditionally: write_count_schemas, write_count_table, write_count_connection_id
                
        Returns:
            JobExecutionResult: Execution result
        """
        logger.info("⚡ WriteDataService: Executing write_data job...")
        
        try:
            columns = [ColumnSchema(columnName=col) for col in params.get("columns", [])]
            write_count = params.get("write_count", False)
            
            write_data_vars = WriteDataVariables(
                data_set=params["data_set"],
                data_set_job_name=params.get("data_set_job_name", ""),
                data_set_folder=params.get("data_set_folder", "3023602439587835"),
                columns=columns,
                add_columns=[],
                connection=params["connection_id"],
                schemas=params["schemas"],
                table=params["table"],
                drop_or_truncate=params.get("drop_or_truncate", "INSERT"),
                write_count=write_count
            )
            
            if write_count:
                write_data_vars.write_count_connection = params["write_count_connection_id"]
                write_data_vars.write_count_schemas = params.get("write_count_schemas")
                write_data_vars.write_count_table = params.get("write_count_table")
            
            request = WriteDataLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": params.get("name", "WriteData_Job"),
                    "description": ""
                },
                variables=[write_data_vars]
            )
            
            result = await write_data_job(request)
            
            logger.info(f"📊 WriteData result: {json.dumps(result, indent=2, default=str)}")
            
            if result.get("message") == "Success":
                return JobExecutionResult(
                    success=True,
                    data={
                        "table": params["table"],
                        "schemas": params["schemas"]
                    }
                )
            else:
                return JobExecutionResult(
                    success=False,
                    data={},
                    error=result.get("error", "Unknown error")
                )
        
        except Exception as e:
            logger.error(f"❌ WriteData error: {str(e)}", exc_info=True)
            return JobExecutionResult(
                success=False,
                data={},
                error=str(e)
            )


class SendEmailService(JobExecutionService):
    """
    Service for executing SendEmail jobs.
    
    Following Single Responsibility Principle - only handles SendEmail execution.
    """
    
    async def execute(self, params: Dict[str, Any]) -> JobExecutionResult:
        """
        Execute a SendEmail job.
        
        Args:
            params: Must include:
                - name: Job name
                - query: SQL query
                - connection_id: Connection ID
                - to: Recipient email
                - subject: Email subject
                - text: Email body
                - cc: CC addresses (optional)
                
        Returns:
            JobExecutionResult: Execution result
        """
        logger.info("⚡ SendEmailService: Executing send_email job...")
        
        try:
            request = SendEmailLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": params.get("name", "Email_Results"),
                    "description": ""
                },
                variables=[SendEmailVariables(
                    query=params["query"],
                    connection=params["connection_id"],
                    to=params["to"],
                    subject=params.get("subject", "Query Results"),
                    text=params.get("text", "Please find the query results attached."),
                    attachment=True,
                    cc=params.get("cc", "")
                )]
            )
            
            result = await send_email_job(request)
            
            logger.info(f"📊 SendEmail result: {json.dumps(result, indent=2, default=str)}")
            
            if result.get("message") == "Success":
                return JobExecutionResult(
                    success=True,
                    data={"to": params["to"]}
                )
            else:
                return JobExecutionResult(
                    success=False,
                    data={},
                    error=result.get("error", "Unknown error")
                )
        
        except Exception as e:
            logger.error(f"❌ SendEmail error: {str(e)}", exc_info=True)
            return JobExecutionResult(
                success=False,
                data={},
                error=str(e)
            )


class CompareSQLService(JobExecutionService):
    """
    Service for executing CompareSQL jobs.
    
    Following Single Responsibility Principle - only handles CompareSQL execution.
    """
    
    async def execute(self, params: Dict[str, Any]) -> JobExecutionResult:
        """
        Execute a CompareSQL job.
        
        Args:
            params: Must include:
                - name: Job name
                - connection_id: Connection ID
                - first_sql_query: First SQL query
                - second_sql_query: Second SQL query
                - first_table_keys: Keys for first table
                - second_table_keys: Keys for second table
                - first_table_columns: Columns for first table
                - second_table_columns: Columns for second table
                - reporting: Reporting type
                - schemas: Schema name
                - table_name: Table name
                And optionally: case_sensitive, drop_before_create, calculate_difference
                
        Returns:
            JobExecutionResult: Execution result
        """
        logger.info("⚡ CompareSQLService: Executing compare_sql job...")
        
        try:
            request = CompareSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": params.get("name", "CompareSQL_Job"),
                    "description": ""
                },
                variables=[CompareSqlVariables(
                    connection=params["connection_id"],
                    first_sql_query=params["first_sql_query"],
                    second_sql_query=params["second_sql_query"],
                    first_table_keys=params["first_table_keys"],
                    second_table_keys=params["second_table_keys"],
                    first_table_columns=params.get("first_table_columns", ""),
                    second_table_columns=params.get("second_table_columns", ""),
                    case_sensitive=params.get("case_sensitive", False),
                    reporting=params.get("reporting", "identical"),
                    schemas=params.get("schemas", "cache"),
                    table_name=params.get("table_name", "cache"),
                    drop_before_create=params.get("drop_before_create", True),
                    calculate_difference=params.get("calculate_difference", False)
                )]
            )
            
            result = await compare_sql_job(request)
            
            logger.info(f"📊 CompareSQL result: {json.dumps(result, indent=2, default=str)}")
            
            if result.get("message") == "Success":
                return JobExecutionResult(
                    success=True,
                    data={"job_id": result.get("job_id")}
                )
            else:
                return JobExecutionResult(
                    success=False,
                    data={},
                    error=result.get("error", "Unknown error")
                )
        
        except Exception as e:
            logger.error(f"❌ CompareSQL error: {str(e)}", exc_info=True)
            return JobExecutionResult(
                success=False,
                data={},
                error=str(e)
            )


class JobServiceFactory:
    """
    Factory for creating job execution services.
    
    Following Open/Closed Principle - easy to add new services.
    """
    
    _services: Dict[str, type] = {
        "read_sql": ReadSQLService,
        "write_data": WriteDataService,
        "send_email": SendEmailService,
        "compare_sql": CompareSQLService,
    }
    
    @classmethod
    def create(cls, job_type: str) -> JobExecutionService:
        """
        Create a job execution service for the given type.
        
        Args:
            job_type: Type of job (read_sql, write_data, send_email, compare_sql)
            
        Returns:
            JobExecutionService: Service instance
            
        Raises:
            ValueError: If job_type is not supported
        """
        service_class = cls._services.get(job_type)
        if not service_class:
            raise ValueError(f"Unsupported job type: {job_type}")
        return service_class()
    
    @classmethod
    def register_service(cls, job_type: str, service_class: type) -> None:
        """
        Register a new job service type.
        
        Args:
            job_type: Type identifier
            service_class: Service class
        """
        cls._services[job_type] = service_class
