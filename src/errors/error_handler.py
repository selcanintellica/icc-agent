"""
Global error handler for ICC application.

Provides centralized error handling, logging, and user message formatting.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Tuple, Type
from functools import wraps

from .exceptions import (
    ICCBaseError,
    AuthenticationError,
    ICCConnectionError,
    ValidationError,
    JobError,
    LLMError,
    ConfigurationError,
    SQLError,
    NetworkTimeoutError,
    APIUnavailableError,
    HTTPError,
    LLMTimeoutError,
    LLMParsingError,
    InvalidJSONError,
    DuplicateJobNameError,
    JobCreationFailedError,
)
from .error_codes import ErrorCode, ErrorCategory
from .error_messages import ErrorMessages

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handler for the ICC application.
    
    Provides:
    - Error classification and mapping
    - User-friendly message generation
    - Structured logging
    - Error response formatting
    """
    
    # Map common exception types to ICC exceptions
    EXCEPTION_MAP: Dict[Type[Exception], Tuple[Type[ICCBaseError], ErrorCode]] = {
        TimeoutError: (NetworkTimeoutError, ErrorCode.CONN_NETWORK_TIMEOUT),
        ConnectionError: (ICCConnectionError, ErrorCode.CONN_HTTP_ERROR),
        json.JSONDecodeError if 'json' in dir() else ValueError: (InvalidJSONError, ErrorCode.VAL_INVALID_JSON),
    }
    
    @classmethod
    def handle(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        log_error: bool = True
    ) -> ICCBaseError:
        """
        Handle an exception and convert it to an ICCBaseError.
        
        Args:
            error: The exception to handle
            context: Additional context information
            log_error: Whether to log the error
            
        Returns:
            ICCBaseError with user-friendly message
        """
        context = context or {}
        
        # If already an ICC error, enhance and return
        if isinstance(error, ICCBaseError):
            if context:
                error.details.update(context)
            if log_error:
                cls._log_error(error)
            return error
        
        # Convert standard exceptions to ICC errors
        icc_error = cls._convert_exception(error, context)
        
        if log_error:
            cls._log_error(icc_error)
        
        return icc_error
    
    @classmethod
    def _convert_exception(
        cls,
        error: Exception,
        context: Dict[str, Any]
    ) -> ICCBaseError:
        """Convert a standard exception to an ICC error."""
        error_str = str(error).lower()
        
        # Check for specific error patterns
        if cls._is_timeout_error(error, error_str):
            return NetworkTimeoutError(
                message=str(error),
                details=context,
                cause=error
            )
        
        if cls._is_connection_error(error, error_str):
            return APIUnavailableError(
                message=str(error),
                details=context,
                cause=error
            )
        
        if cls._is_auth_error(error, error_str):
            return AuthenticationError(
                message=str(error),
                details=context,
                cause=error
            )
        
        if cls._is_duplicate_job_error(error_str):
            job_name = context.get("job_name", "unknown")
            return DuplicateJobNameError(
                job_name=job_name,
                cause=error
            )
        
        if cls._is_json_error(error):
            return InvalidJSONError(
                message=str(error),
                details=context,
                cause=error
            )
        
        if cls._is_http_error(error, error_str):
            status_code = cls._extract_status_code(error)
            return HTTPError(
                message=str(error),
                details=context,
                cause=error,
                status_code=status_code
            )
        
        # Default: wrap in generic ICC error
        return ICCBaseError(
            error_code=ErrorCode.JOB_CREATION_FAILED,
            message=str(error),
            details=context,
            cause=error
        )
    
    @classmethod
    def _is_timeout_error(cls, error: Exception, error_str: str) -> bool:
        """Check if error is a timeout error."""
        timeout_indicators = ["timeout", "timed out", "deadline exceeded"]
        return (
            isinstance(error, TimeoutError) or
            any(ind in error_str for ind in timeout_indicators)
        )
    
    @classmethod
    def _is_connection_error(cls, error: Exception, error_str: str) -> bool:
        """Check if error is a connection error."""
        conn_indicators = [
            "connection refused", "connection reset", "connection error",
            "network unreachable", "no route to host", "connection aborted"
        ]
        return (
            isinstance(error, (ConnectionError, OSError)) or
            any(ind in error_str for ind in conn_indicators)
        )
    
    @classmethod
    def _is_auth_error(cls, error: Exception, error_str: str) -> bool:
        """Check if error is an authentication error."""
        auth_indicators = [
            "unauthorized", "authentication", "403", "401",
            "forbidden", "invalid token", "token expired"
        ]
        return any(ind in error_str for ind in auth_indicators)
    
    @classmethod
    def _is_duplicate_job_error(cls, error_str: str) -> bool:
        """Check if error is a duplicate job name error."""
        duplicate_indicators = [
            "same name", "already exists", "duplicate", "name conflict"
        ]
        return any(ind in error_str for ind in duplicate_indicators)
    
    @classmethod
    def _is_json_error(cls, error: Exception) -> bool:
        """Check if error is a JSON parsing error."""
        import json
        return isinstance(error, (json.JSONDecodeError, ValueError)) and "json" in str(type(error)).lower()
    
    @classmethod
    def _is_http_error(cls, error: Exception, error_str: str) -> bool:
        """Check if error is an HTTP error."""
        http_indicators = ["http", "status code", "response"]
        return any(ind in error_str for ind in http_indicators)
    
    @classmethod
    def _extract_status_code(cls, error: Exception) -> Optional[int]:
        """Extract HTTP status code from error if available."""
        if hasattr(error, "status_code"):
            return error.status_code
        if hasattr(error, "response") and hasattr(error.response, "status_code"):
            return error.response.status_code
        return None
    
    @classmethod
    def _log_error(cls, error: ICCBaseError) -> None:
        """Log an ICC error with appropriate level."""
        log_msg = (
            f"[{error.code}] {error.technical_message} | "
            f"Category: {error.category.value} | "
            f"Retryable: {error.is_retryable}"
        )
        
        if error.details:
            log_msg += f" | Details: {error.details}"
        
        if error.cause:
            log_msg += f" | Cause: {type(error.cause).__name__}: {str(error.cause)}"
        
        # Log at appropriate level based on error type
        if error.is_retryable:
            logger.warning(log_msg)
        else:
            logger.error(log_msg)
        
        # Log full traceback for debugging
        if error.cause:
            logger.debug(f"Original traceback:\n{traceback.format_exception(type(error.cause), error.cause, error.cause.__traceback__)}")
    
    @classmethod
    def get_user_message(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get user-friendly message for any exception.
        
        Args:
            error: The exception
            context: Additional context
            
        Returns:
            User-friendly error message
        """
        if isinstance(error, ICCBaseError):
            return error.user_message
        
        # Convert and get message
        icc_error = cls._convert_exception(error, context or {})
        return icc_error.user_message
    
    @classmethod
    def format_for_ui(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        Format error for UI display.
        
        Args:
            error: The exception
            context: Additional context
            include_suggestions: Whether to include recovery suggestions
            
        Returns:
            Dictionary with formatted error information
        """
        if not isinstance(error, ICCBaseError):
            error = cls._convert_exception(error, context or {})
        
        result = {
            "message": error.user_message,
            "code": error.code,
            "category": error.category.value,
            "is_retryable": error.is_retryable,
        }
        
        if include_suggestions:
            suggestions = cls._get_suggestions(error)
            if suggestions:
                result["suggestions"] = suggestions
        
        return result
    
    @classmethod
    def _get_suggestions(cls, error: ICCBaseError) -> list:
        """Get recovery suggestions based on error type."""
        suggestions = []
        
        if error.is_retryable:
            suggestions.append("Try the operation again in a few moments.")
        
        category_suggestions = {
            ErrorCategory.AUTHENTICATION: [
                "Refresh the page to start a new session.",
                "Check that your credentials are correct."
            ],
            ErrorCategory.CONNECTION: [
                "Check your internet connection.",
                "Verify the server is accessible."
            ],
            ErrorCategory.VALIDATION: [
                "Review the input values for errors.",
                "Ensure all required fields are filled."
            ],
            ErrorCategory.JOB: [
                "Check job parameters and try again.",
                "Verify you have permission for this operation."
            ],
            ErrorCategory.LLM: [
                "Try rephrasing your request.",
                "Break complex requests into smaller steps."
            ],
            ErrorCategory.SQL: [
                "Review the SQL syntax for errors.",
                "Verify table and column names are correct."
            ],
        }
        
        suggestions.extend(category_suggestions.get(error.category, []))
        
        return suggestions[:3]  # Limit to 3 suggestions


def handle_errors(
    default_message: str = "An error occurred. Please try again.",
    log_errors: bool = True,
    reraise: bool = False
):
    """
    Decorator for handling errors in functions.
    
    Args:
        default_message: Default user message if error handling fails
        log_errors: Whether to log errors
        reraise: Whether to reraise the error after handling
    
    Usage:
        @handle_errors("Failed to process request")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                icc_error = ErrorHandler.handle(e, log_error=log_errors)
                if reraise:
                    raise icc_error from e
                return {"error": icc_error.user_message, "error_code": icc_error.code}
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                icc_error = ErrorHandler.handle(e, log_error=log_errors)
                if reraise:
                    raise icc_error from e
                return {"error": icc_error.user_message, "error_code": icc_error.code}
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Import json for error checking
import json

