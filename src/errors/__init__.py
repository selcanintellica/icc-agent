"""
ICC Error Handling Module.

Provides a comprehensive error handling system with:
- Custom exception hierarchy
- Error codes and categories
- User-friendly error messages
- Global error handler

Usage:
    from src.errors import (
        # Exceptions
        ICCBaseError,
        AuthenticationError,
        ValidationError,
        JobError,
        
        # Error codes
        ErrorCode,
        ErrorCategory,
        
        # Handler
        ErrorHandler,
        handle_errors,
        
        # Messages
        ErrorMessages,
    )
"""

# Error codes
from .error_codes import (
    ErrorCode,
    ErrorCategory,
    ErrorCodeInfo,
    get_error_code_by_string,
)

# Exceptions
from .exceptions import (
    # Base
    ICCBaseError,
    
    # Authentication
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError,
    NoCredentialsError,
    
    # Connection
    ICCConnectionError,
    NetworkTimeoutError,
    APIUnavailableError,
    DatabaseConnectionError,
    UnknownConnectionError,
    HTTPError,
    
    # Validation
    ValidationError,
    InvalidParameterError,
    MissingParameterError,
    InvalidSQLError,
    InvalidEmailError,
    InvalidJSONError,
    
    # Job
    JobError,
    DuplicateJobNameError,
    JobCreationFailedError,
    JobExecutionFailedError,
    MissingDatasetError,
    
    # LLM
    LLMError,
    LLMTimeoutError,
    LLMParsingError,
    LLMUnavailableError,
    
    # Configuration
    ConfigurationError,
    MissingConfigError,
    MissingEnvVarError,
    
    # SQL
    SQLError,
    SQLSyntaxError,
    SQLExecutionError,
    TableNotFoundError,
)

# Error messages
from .error_messages import (
    ErrorMessages,
    ErrorMessageBuilder,
)

# Error handler
from .error_handler import (
    ErrorHandler,
    handle_errors,
)

__all__ = [
    # Error codes
    "ErrorCode",
    "ErrorCategory",
    "ErrorCodeInfo",
    "get_error_code_by_string",
    
    # Base exception
    "ICCBaseError",
    
    # Authentication exceptions
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "NoCredentialsError",
    
    # Connection exceptions
    "ICCConnectionError",
    "NetworkTimeoutError",
    "APIUnavailableError",
    "DatabaseConnectionError",
    "UnknownConnectionError",
    "HTTPError",
    
    # Validation exceptions
    "ValidationError",
    "InvalidParameterError",
    "MissingParameterError",
    "InvalidSQLError",
    "InvalidEmailError",
    "InvalidJSONError",
    
    # Job exceptions
    "JobError",
    "DuplicateJobNameError",
    "JobCreationFailedError",
    "JobExecutionFailedError",
    "MissingDatasetError",
    
    # LLM exceptions
    "LLMError",
    "LLMTimeoutError",
    "LLMParsingError",
    "LLMUnavailableError",
    
    # Configuration exceptions
    "ConfigurationError",
    "MissingConfigError",
    "MissingEnvVarError",
    
    # SQL exceptions
    "SQLError",
    "SQLSyntaxError",
    "SQLExecutionError",
    "TableNotFoundError",
    
    # Error messages
    "ErrorMessages",
    "ErrorMessageBuilder",
    
    # Error handler
    "ErrorHandler",
    "handle_errors",
]

