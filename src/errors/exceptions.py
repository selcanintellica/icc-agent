"""
Custom exception hierarchy for ICC application.

Provides structured exceptions with error codes, user-friendly messages,
and additional context for debugging and user communication.
"""

from typing import Optional, Dict, Any
from .error_codes import ErrorCode, ErrorCategory


class ICCBaseError(Exception):
    """
    Base exception class for all ICC application errors.
    
    Provides:
    - Error code for tracking
    - User-friendly message
    - Technical details for logging
    - Additional context
    """
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize ICC error.
        
        Args:
            error_code: Structured error code
            message: Technical error message (for logging)
            user_message: User-friendly message (for UI display)
            details: Additional context information
            cause: Original exception that caused this error
        """
        self.error_code = error_code
        self.technical_message = message or error_code.description
        self.user_message = user_message or self._default_user_message()
        self.details = details or {}
        self.cause = cause
        
        super().__init__(self.technical_message)
    
    def _default_user_message(self) -> str:
        """Get default user message based on error category."""
        category_messages = {
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please try logging in again.",
            ErrorCategory.CONNECTION: "Unable to connect to the server. Please try again.",
            ErrorCategory.VALIDATION: "The provided information is invalid. Please check and try again.",
            ErrorCategory.JOB: "Unable to complete the job operation. Please try again.",
            ErrorCategory.LLM: "The AI assistant encountered an issue. Please try rephrasing your request.",
            ErrorCategory.CONFIGURATION: "There's a configuration issue. Please contact support.",
            ErrorCategory.SQL: "There was an issue with the SQL query. Please check the syntax.",
        }
        return category_messages.get(
            self.error_code.category,
            "An unexpected error occurred. Please try again."
        )
    
    @property
    def code(self) -> str:
        """Get the error code string."""
        return self.error_code.code
    
    @property
    def category(self) -> ErrorCategory:
        """Get the error category."""
        return self.error_code.category
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error is retryable."""
        return self.error_code.is_retryable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        result = {
            "error_code": self.code,
            "category": self.category.value,
            "message": self.technical_message,
            "user_message": self.user_message,
            "is_retryable": self.is_retryable,
        }
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"[{self.code}] {self.technical_message}"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"message={self.technical_message!r}, "
            f"details={self.details!r})"
        )


# Authentication Errors

class AuthenticationError(ICCBaseError):
    """Base class for authentication-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.AUTH_FAILED,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    
    def __init__(
        self,
        message: str = "Authentication token has expired",
        user_message: str = "Your session has expired. Please refresh and try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            ErrorCode.AUTH_TOKEN_EXPIRED,
            message,
            user_message,
            details,
            cause
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""
    
    def __init__(
        self,
        message: str = "Invalid credentials provided",
        user_message: str = "Unable to authenticate. Please check your credentials and try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            message,
            user_message,
            details,
            cause
        )


class NoCredentialsError(AuthenticationError):
    """Raised when no credentials are configured."""
    
    def __init__(
        self,
        message: str = "No authentication credentials configured",
        user_message: str = "Authentication is not configured. Please contact your administrator.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            ErrorCode.AUTH_NO_CREDENTIALS,
            message,
            user_message,
            details,
            cause
        )


# Connection Errors

class ICCConnectionError(ICCBaseError):
    """Base class for connection-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.CONN_HTTP_ERROR,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class NetworkTimeoutError(ICCConnectionError):
    """Raised when a network request times out."""
    
    def __init__(
        self,
        message: str = "Network request timed out",
        user_message: str = "The connection timed out. Please try again in a moment.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        timeout_seconds: Optional[float] = None
    ):
        if timeout_seconds:
            details = details or {}
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            ErrorCode.CONN_NETWORK_TIMEOUT,
            message,
            user_message,
            details,
            cause
        )


class APIUnavailableError(ICCConnectionError):
    """Raised when an API service is unavailable."""
    
    def __init__(
        self,
        message: str = "API service is unavailable",
        user_message: str = "The service is temporarily unavailable. Please try again later.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        service_name: Optional[str] = None
    ):
        if service_name:
            details = details or {}
            details["service_name"] = service_name
        super().__init__(
            ErrorCode.CONN_API_UNAVAILABLE,
            message,
            user_message,
            details,
            cause
        )


class DatabaseConnectionError(ICCConnectionError):
    """Raised when database connection fails."""
    
    def __init__(
        self,
        message: str = "Database connection failed",
        user_message: str = "Unable to connect to the database. Please try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        connection_name: Optional[str] = None
    ):
        if connection_name:
            details = details or {}
            details["connection_name"] = connection_name
            user_message = f"Unable to connect to '{connection_name}'. Please check the connection and try again."
        super().__init__(
            ErrorCode.CONN_DATABASE_ERROR,
            message,
            user_message,
            details,
            cause
        )


class UnknownConnectionError(ICCConnectionError):
    """Raised when a connection name is not found."""
    
    def __init__(
        self,
        connection_name: str,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["connection_name"] = connection_name
        super().__init__(
            ErrorCode.CONN_UNKNOWN_CONNECTION,
            message or f"Unknown connection: {connection_name}",
            user_message or f"The connection '{connection_name}' was not found. Please select a valid connection.",
            details,
            cause
        )


class HTTPError(ICCConnectionError):
    """Raised for HTTP-related errors."""
    
    def __init__(
        self,
        message: str = "HTTP request failed",
        user_message: str = "A network error occurred. Please try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body[:500]  # Truncate long responses
        super().__init__(
            ErrorCode.CONN_HTTP_ERROR,
            message,
            user_message,
            details,
            cause
        )


# Validation Errors

class ValidationError(ICCBaseError):
    """Base class for validation-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.VAL_INVALID_PARAMETER,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class InvalidParameterError(ValidationError):
    """Raised when a parameter value is invalid."""
    
    def __init__(
        self,
        parameter_name: str,
        value: Any = None,
        expected: Optional[str] = None,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["parameter_name"] = parameter_name
        if value is not None:
            details["provided_value"] = str(value)[:100]
        if expected:
            details["expected"] = expected
        
        default_user_msg = f"Invalid value for '{parameter_name}'."
        if expected:
            default_user_msg += f" Expected: {expected}"
        
        super().__init__(
            ErrorCode.VAL_INVALID_PARAMETER,
            message or f"Invalid parameter: {parameter_name}",
            user_message or default_user_msg,
            details,
            cause
        )


class MissingParameterError(ValidationError):
    """Raised when a required parameter is missing."""
    
    def __init__(
        self,
        parameter_name: str,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["parameter_name"] = parameter_name
        
        super().__init__(
            ErrorCode.VAL_MISSING_PARAMETER,
            message or f"Missing required parameter: {parameter_name}",
            user_message or f"Please provide the '{parameter_name}' value.",
            details,
            cause
        )


class InvalidSQLError(ValidationError):
    """Raised when SQL syntax is invalid."""
    
    def __init__(
        self,
        sql: Optional[str] = None,
        message: str = "Invalid SQL syntax",
        user_message: str = "The SQL query appears to be invalid. Please check the syntax and try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if sql:
            details["sql"] = sql[:200]  # Truncate long SQL
        super().__init__(
            ErrorCode.VAL_INVALID_SQL,
            message,
            user_message,
            details,
            cause
        )


class InvalidEmailError(ValidationError):
    """Raised when email address format is invalid."""
    
    def __init__(
        self,
        email: str,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["email"] = email
        
        super().__init__(
            ErrorCode.VAL_INVALID_EMAIL,
            message or f"Invalid email address: {email}",
            user_message or f"The email address '{email}' is not valid. Please provide a valid email.",
            details,
            cause
        )


class InvalidJSONError(ValidationError):
    """Raised when JSON parsing fails."""
    
    def __init__(
        self,
        message: str = "Invalid JSON format",
        user_message: str = "The data format is invalid. Please try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        raw_content: Optional[str] = None
    ):
        details = details or {}
        if raw_content:
            details["raw_content"] = raw_content[:200]
        super().__init__(
            ErrorCode.VAL_INVALID_JSON,
            message,
            user_message,
            details,
            cause
        )


# Job Errors

class JobError(ICCBaseError):
    """Base class for job-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.JOB_CREATION_FAILED,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class DuplicateJobNameError(JobError):
    """Raised when a job with the same name already exists."""
    
    def __init__(
        self,
        job_name: str,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["job_name"] = job_name
        
        super().__init__(
            ErrorCode.JOB_DUPLICATE_NAME,
            message or f"Job with name '{job_name}' already exists",
            user_message or f"A job named '{job_name}' already exists. Please choose a different name.",
            details,
            cause
        )


class JobCreationFailedError(JobError):
    """Raised when job creation fails."""
    
    def __init__(
        self,
        job_type: Optional[str] = None,
        message: str = "Job creation failed",
        user_message: str = "Unable to create the job. Please check your inputs and try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if job_type:
            details["job_type"] = job_type
        super().__init__(
            ErrorCode.JOB_CREATION_FAILED,
            message,
            user_message,
            details,
            cause
        )


class JobExecutionFailedError(JobError):
    """Raised when job execution fails."""
    
    def __init__(
        self,
        job_id: Optional[str] = None,
        message: str = "Job execution failed",
        user_message: str = "The job could not be executed. Please try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if job_id:
            details["job_id"] = job_id
        super().__init__(
            ErrorCode.JOB_EXECUTION_FAILED,
            message,
            user_message,
            details,
            cause
        )


class MissingDatasetError(JobError):
    """Raised when a required dataset is not found."""
    
    def __init__(
        self,
        dataset_id: Optional[str] = None,
        message: str = "Required dataset not found",
        user_message: str = "The required data is not available. Please run the previous step first.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if dataset_id:
            details["dataset_id"] = dataset_id
        super().__init__(
            ErrorCode.JOB_MISSING_DATASET,
            message,
            user_message,
            details,
            cause
        )


# LLM Errors

class LLMError(ICCBaseError):
    """Base class for LLM-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.LLM_UNAVAILABLE,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    
    def __init__(
        self,
        message: str = "LLM request timed out",
        user_message: str = "The AI is taking longer than expected. Please try again or rephrase your request.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        timeout_seconds: Optional[float] = None
    ):
        details = details or {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            ErrorCode.LLM_TIMEOUT,
            message,
            user_message,
            details,
            cause
        )


class LLMParsingError(LLMError):
    """Raised when LLM response cannot be parsed."""
    
    def __init__(
        self,
        message: str = "Failed to parse LLM response",
        user_message: str = "The AI response was unclear. Please try rephrasing your request.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        raw_response: Optional[str] = None
    ):
        details = details or {}
        if raw_response:
            details["raw_response"] = raw_response[:300]
        super().__init__(
            ErrorCode.LLM_PARSING_ERROR,
            message,
            user_message,
            details,
            cause
        )


class LLMUnavailableError(LLMError):
    """Raised when LLM service is unavailable."""
    
    def __init__(
        self,
        message: str = "LLM service unavailable",
        user_message: str = "The AI assistant is temporarily unavailable. Please try again in a moment.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        model_name: Optional[str] = None
    ):
        details = details or {}
        if model_name:
            details["model_name"] = model_name
        super().__init__(
            ErrorCode.LLM_UNAVAILABLE,
            message,
            user_message,
            details,
            cause
        )


# Configuration Errors

class ConfigurationError(ICCBaseError):
    """Base class for configuration-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.CFG_INVALID_CONFIG,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(
        self,
        config_key: str,
        message: Optional[str] = None,
        user_message: str = "A required configuration is missing. Please contact your administrator.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["config_key"] = config_key
        
        super().__init__(
            ErrorCode.CFG_MISSING_CONFIG,
            message or f"Missing required configuration: {config_key}",
            user_message,
            details,
            cause
        )


class MissingEnvVarError(ConfigurationError):
    """Raised when a required environment variable is not set."""
    
    def __init__(
        self,
        env_var: str,
        message: Optional[str] = None,
        user_message: str = "A required configuration is missing. Please contact your administrator.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["env_var"] = env_var
        
        super().__init__(
            ErrorCode.CFG_ENV_VAR_MISSING,
            message or f"Required environment variable not set: {env_var}",
            user_message,
            details,
            cause
        )


# SQL Errors

class SQLError(ICCBaseError):
    """Base class for SQL-related errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.SQL_EXECUTION_ERROR,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(error_code, message, user_message, details, cause)


class SQLSyntaxError(SQLError):
    """Raised for SQL syntax errors."""
    
    def __init__(
        self,
        sql: Optional[str] = None,
        message: str = "SQL syntax error",
        user_message: str = "The SQL query has a syntax error. Please check and correct it.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if sql:
            details["sql"] = sql[:200]
        super().__init__(
            ErrorCode.SQL_SYNTAX_ERROR,
            message,
            user_message,
            details,
            cause
        )


class SQLExecutionError(SQLError):
    """Raised when SQL execution fails."""
    
    def __init__(
        self,
        sql: Optional[str] = None,
        message: str = "SQL execution failed",
        user_message: str = "Unable to execute the query. Please check the SQL and try again.",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if sql:
            details["sql"] = sql[:200]
        super().__init__(
            ErrorCode.SQL_EXECUTION_ERROR,
            message,
            user_message,
            details,
            cause
        )


class TableNotFoundError(SQLError):
    """Raised when a table is not found."""
    
    def __init__(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        message: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details["table_name"] = table_name
        if schema_name:
            details["schema_name"] = schema_name
            full_name = f"{schema_name}.{table_name}"
        else:
            full_name = table_name
        
        super().__init__(
            ErrorCode.SQL_TABLE_NOT_FOUND,
            message or f"Table not found: {full_name}",
            user_message or f"The table '{full_name}' was not found. Please check the table name.",
            details,
            cause
        )

