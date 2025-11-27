"""
Job execution service abstraction - handles job execution (read_sql, write_data, etc).
Implements Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class JobExecutionService(ABC):
    """Abstract interface for job execution."""
    
    @abstractmethod
    async def execute_read_sql(self, request: Any) -> Dict[str, Any]:
        """Execute read_sql job."""
        pass
    
    @abstractmethod
    async def execute_write_data(self, request: Any) -> Dict[str, Any]:
        """Execute write_data job."""
        pass
    
    @abstractmethod
    async def execute_send_email(self, request: Any) -> Dict[str, Any]:
        """Execute send_email job."""
        pass
    
    @abstractmethod
    async def execute_compare_sql(self, request: Any) -> Dict[str, Any]:
        """Execute compare_sql job."""
        pass


class ICCJobExecutionService(JobExecutionService):
    """ICC-specific implementation of job execution service."""
    
    async def execute_read_sql(self, request: Any) -> Dict[str, Any]:
        """Execute read_sql job via ICC toolkit."""
        from src.ai.toolkits.icc_toolkit import read_sql_job
        return await read_sql_job(request)
    
    async def execute_write_data(self, request: Any) -> Dict[str, Any]:
        """Execute write_data job via ICC toolkit."""
        from src.ai.toolkits.icc_toolkit import write_data_job
        return await write_data_job(request)
    
    async def execute_send_email(self, request: Any) -> Dict[str, Any]:
        """Execute send_email job via ICC toolkit."""
        from src.ai.toolkits.icc_toolkit import send_email_job
        return await send_email_job(request)
    
    async def execute_compare_sql(self, request: Any) -> Dict[str, Any]:
        """Execute compare_sql job via ICC toolkit."""
        from src.ai.toolkits.icc_toolkit import compare_sql_job
        return await compare_sql_job(request)


class MockJobExecutionService(JobExecutionService):
    """Mock job execution service for testing."""
    
    def __init__(self):
        self.executed_jobs = []
    
    async def execute_read_sql(self, request: Any) -> Dict[str, Any]:
        self.executed_jobs.append(("read_sql", request))
        return {"message": "Success", "job_id": "mock_job_123", "columns": ["col1", "col2"]}
    
    async def execute_write_data(self, request: Any) -> Dict[str, Any]:
        self.executed_jobs.append(("write_data", request))
        return {"message": "Success", "job_id": "mock_write_456"}
    
    async def execute_send_email(self, request: Any) -> Dict[str, Any]:
        self.executed_jobs.append(("send_email", request))
        return {"message": "Success", "job_id": "mock_email_789"}
    
    async def execute_compare_sql(self, request: Any) -> Dict[str, Any]:
        self.executed_jobs.append(("compare_sql", request))
        return {"message": "Success", "job_id": "mock_compare_101"}
