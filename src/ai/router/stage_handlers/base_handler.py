"""
Base handler for stage processing with error handling.

Defines the interface and common functionality for all stage handlers
following SOLID principles with structured error handling.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any, Dict

from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.errors import (
    ICCBaseError,
    ErrorHandler,
    ErrorMessages,
    JobError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class StageHandlerResult:
    """
    Result from a stage handler.
    
    Following the Single Responsibility Principle, this class only
    represents the outcome of stage processing.
    """
    memory: Memory
    response: str
    next_stage: Optional[Stage] = None
    error_code: Optional[str] = None  # For tracking error types
    is_error: bool = False  # Indicates if response is an error message
    
    def __post_init__(self):
        """Update memory stage if next_stage is provided."""
        if self.next_stage is not None:
            self.memory.stage = self.next_stage


class BaseStageHandler(ABC):
    """
    Abstract base class for stage handlers with error handling.
    
    Following SOLID principles:
    - Single Responsibility: Each handler manages one stage type
    - Open/Closed: Easy to extend with new handlers
    - Liskov Substitution: All handlers can be used interchangeably
    - Interface Segregation: Clear, focused interface
    - Dependency Inversion: Depends on abstractions
    """
    
    @abstractmethod
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Args:
            stage: The stage to check
            
        Returns:
            bool: True if this handler can process the stage
        """
        pass
    
    @abstractmethod
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process the stage and return the result.
        
        Args:
            memory: Current conversation memory
            user_input: User's input message
            
        Returns:
            StageHandlerResult: Result with updated memory and response
        """
        pass
    
    def _create_result(
        self, 
        memory: Memory, 
        response: str, 
        next_stage: Optional[Stage] = None,
        is_error: bool = False,
        error_code: Optional[str] = None
    ) -> StageHandlerResult:
        """
        Helper to create a stage handler result.
        
        Args:
            memory: Updated memory
            response: Response message
            next_stage: Optional next stage to transition to
            is_error: Whether this is an error response
            error_code: Error code if applicable
            
        Returns:
            StageHandlerResult: The result object
        """
        return StageHandlerResult(
            memory=memory,
            response=response,
            next_stage=next_stage,
            is_error=is_error,
            error_code=error_code
        )
    
    def _create_error_result(
        self,
        memory: Memory,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        fallback_message: Optional[str] = None
    ) -> StageHandlerResult:
        """
        Create a result from an exception with user-friendly message.
        
        Args:
            memory: Current memory
            error: The exception that occurred
            context: Additional context for error handling
            fallback_message: Message to use if error handling fails
            
        Returns:
            StageHandlerResult with error information
        """
        try:
            if isinstance(error, ICCBaseError):
                icc_error = error
            else:
                icc_error = ErrorHandler.handle(error, context or {})
            
            return StageHandlerResult(
                memory=memory,
                response=f"Error: {icc_error.user_message}",
                is_error=True,
                error_code=icc_error.code
            )
        except Exception as e:
            logger.error(f"Error creating error result: {e}")
            return StageHandlerResult(
                memory=memory,
                response=fallback_message or "An unexpected error occurred. Please try again.",
                is_error=True
            )
    
    def _format_connection_error(
        self,
        connection_name: str,
        original_error: Optional[Exception] = None
    ) -> str:
        """Format user-friendly message for connection errors."""
        base_msg = f"Unable to use connection '{connection_name}'."
        
        if original_error:
            error_str = str(original_error).lower()
            if "not found" in error_str or "unknown" in error_str:
                return f"{base_msg} This connection was not found. Please select a valid connection from the list."
            elif "timeout" in error_str:
                return f"{base_msg} The connection timed out. Please try again."
            elif "auth" in error_str or "permission" in error_str:
                return f"{base_msg} Authentication failed. Please check your credentials."
        
        return f"{base_msg} Please try again or select a different connection."
    
    def _format_job_error(
        self,
        job_type: str,
        error: Exception,
        job_name: Optional[str] = None
    ) -> str:
        """Format user-friendly message for job errors."""
        error_str = str(error).lower()
        
        if "same name" in error_str or "already exists" in error_str or "duplicate" in error_str:
            name_part = f"'{job_name}'" if job_name else "with this name"
            return f"A {job_type} job {name_part} already exists. Please choose a different name."
        
        if "timeout" in error_str:
            return f"The {job_type} job creation timed out. Please try again."
        
        if "auth" in error_str or "unauthorized" in error_str:
            return f"Unable to create {job_type} job due to authentication issues. Please refresh and try again."
        
        if "validation" in error_str or "invalid" in error_str:
            return f"The {job_type} job parameters are invalid. Please check your inputs and try again."
        
        return f"Unable to create {job_type} job. Please check your inputs and try again."
    
    def _format_sql_error(self, sql: Optional[str], error: Exception) -> str:
        """Format user-friendly message for SQL errors."""
        error_str = str(error).lower()
        
        if "syntax" in error_str:
            return "The SQL query has a syntax error. Please check and correct the query."
        
        if "column" in error_str and "not found" in error_str:
            return "One or more columns in the query were not found. Please verify column names."
        
        if "table" in error_str and "not found" in error_str:
            return "One or more tables in the query were not found. Please verify table names."
        
        if "permission" in error_str or "denied" in error_str:
            return "You don't have permission to execute this query. Please check your access rights."
        
        if "timeout" in error_str:
            return "The query took too long to execute. Please try a simpler query."
        
        return "There was an error executing the SQL query. Please check the query and try again."
    
    def _format_validation_error(self, parameter: str, value: Any = None) -> str:
        """Format user-friendly message for validation errors."""
        if value is not None:
            return f"The value '{value}' is not valid for '{parameter}'. Please provide a correct value."
        return f"Please provide a valid value for '{parameter}'."
