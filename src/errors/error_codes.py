"""
Error codes and categories for ICC application.

Provides structured error codes for consistent error tracking and reporting.
Each error category has a numeric range:
- AUTH: 001-099 (Authentication/Authorization)
- CONN: 100-199 (Connection/Network)
- VAL: 200-299 (Validation)
- JOB: 300-399 (Job Operations)
- LLM: 400-499 (LLM/AI Operations)
- CFG: 500-599 (Configuration)
- SQL: 600-699 (SQL Operations)
"""

from enum import Enum
from typing import NamedTuple


class ErrorCategory(Enum):
    """Categories for grouping related errors."""
    AUTHENTICATION = "AUTH"
    CONNECTION = "CONN"
    VALIDATION = "VAL"
    JOB = "JOB"
    LLM = "LLM"
    CONFIGURATION = "CFG"
    SQL = "SQL"


class ErrorCodeInfo(NamedTuple):
    """Information about an error code."""
    code: str
    category: ErrorCategory
    description: str
    is_retryable: bool = False


class ErrorCode(Enum):
    """
    Enumeration of all error codes in the system.
    
    Format: CATEGORY_NUMBER (e.g., AUTH_001, CONN_101)
    """
    
    # Authentication Errors (AUTH_001 - AUTH_099)
    AUTH_FAILED = ErrorCodeInfo("AUTH_001", ErrorCategory.AUTHENTICATION, "Authentication failed")
    AUTH_TOKEN_EXPIRED = ErrorCodeInfo("AUTH_002", ErrorCategory.AUTHENTICATION, "Authentication token expired", is_retryable=True)
    AUTH_INVALID_CREDENTIALS = ErrorCodeInfo("AUTH_003", ErrorCategory.AUTHENTICATION, "Invalid credentials provided")
    AUTH_NO_CREDENTIALS = ErrorCodeInfo("AUTH_004", ErrorCategory.AUTHENTICATION, "No credentials configured")
    AUTH_TOKEN_FETCH_FAILED = ErrorCodeInfo("AUTH_005", ErrorCategory.AUTHENTICATION, "Failed to fetch authentication token", is_retryable=True)
    
    # Connection Errors (CONN_100 - CONN_199)
    CONN_NETWORK_TIMEOUT = ErrorCodeInfo("CONN_101", ErrorCategory.CONNECTION, "Network connection timed out", is_retryable=True)
    CONN_API_UNAVAILABLE = ErrorCodeInfo("CONN_102", ErrorCategory.CONNECTION, "API service unavailable", is_retryable=True)
    CONN_DATABASE_ERROR = ErrorCodeInfo("CONN_103", ErrorCategory.CONNECTION, "Database connection error")
    CONN_UNKNOWN_CONNECTION = ErrorCodeInfo("CONN_104", ErrorCategory.CONNECTION, "Unknown connection name")
    CONN_HTTP_ERROR = ErrorCodeInfo("CONN_105", ErrorCategory.CONNECTION, "HTTP request failed", is_retryable=True)
    CONN_SSL_ERROR = ErrorCodeInfo("CONN_106", ErrorCategory.CONNECTION, "SSL/TLS connection error")
    CONN_DNS_ERROR = ErrorCodeInfo("CONN_107", ErrorCategory.CONNECTION, "DNS resolution failed", is_retryable=True)
    
    # Validation Errors (VAL_200 - VAL_299)
    VAL_INVALID_PARAMETER = ErrorCodeInfo("VAL_201", ErrorCategory.VALIDATION, "Invalid parameter value")
    VAL_MISSING_PARAMETER = ErrorCodeInfo("VAL_202", ErrorCategory.VALIDATION, "Required parameter missing")
    VAL_INVALID_SQL = ErrorCodeInfo("VAL_203", ErrorCategory.VALIDATION, "Invalid SQL syntax")
    VAL_INVALID_EMAIL = ErrorCodeInfo("VAL_204", ErrorCategory.VALIDATION, "Invalid email address format")
    VAL_INVALID_CONNECTION = ErrorCodeInfo("VAL_205", ErrorCategory.VALIDATION, "Invalid connection configuration")
    VAL_INVALID_SCHEMA = ErrorCodeInfo("VAL_206", ErrorCategory.VALIDATION, "Invalid schema name")
    VAL_INVALID_TABLE = ErrorCodeInfo("VAL_207", ErrorCategory.VALIDATION, "Invalid table name")
    VAL_EMPTY_INPUT = ErrorCodeInfo("VAL_208", ErrorCategory.VALIDATION, "Empty input provided")
    VAL_INVALID_JSON = ErrorCodeInfo("VAL_209", ErrorCategory.VALIDATION, "Invalid JSON format")
    
    # Job Errors (JOB_300 - JOB_399)
    JOB_CREATION_FAILED = ErrorCodeInfo("JOB_301", ErrorCategory.JOB, "Job creation failed")
    JOB_DUPLICATE_NAME = ErrorCodeInfo("JOB_302", ErrorCategory.JOB, "Job with this name already exists")
    JOB_EXECUTION_FAILED = ErrorCodeInfo("JOB_303", ErrorCategory.JOB, "Job execution failed")
    JOB_NOT_FOUND = ErrorCodeInfo("JOB_304", ErrorCategory.JOB, "Job not found")
    JOB_INVALID_STATE = ErrorCodeInfo("JOB_305", ErrorCategory.JOB, "Job is in invalid state")
    JOB_MISSING_DATASET = ErrorCodeInfo("JOB_306", ErrorCategory.JOB, "Required dataset not found")
    JOB_COLUMN_MISMATCH = ErrorCodeInfo("JOB_307", ErrorCategory.JOB, "Column mismatch between datasets")
    
    # LLM Errors (LLM_400 - LLM_499)
    LLM_TIMEOUT = ErrorCodeInfo("LLM_401", ErrorCategory.LLM, "LLM request timed out", is_retryable=True)
    LLM_PARSING_ERROR = ErrorCodeInfo("LLM_402", ErrorCategory.LLM, "Failed to parse LLM response")
    LLM_UNAVAILABLE = ErrorCodeInfo("LLM_403", ErrorCategory.LLM, "LLM service unavailable", is_retryable=True)
    LLM_INVALID_RESPONSE = ErrorCodeInfo("LLM_404", ErrorCategory.LLM, "Invalid response from LLM")
    LLM_CONTEXT_TOO_LONG = ErrorCodeInfo("LLM_405", ErrorCategory.LLM, "Context exceeds LLM limit")
    LLM_RATE_LIMITED = ErrorCodeInfo("LLM_406", ErrorCategory.LLM, "LLM rate limit exceeded", is_retryable=True)
    
    # Configuration Errors (CFG_500 - CFG_599)
    CFG_MISSING_CONFIG = ErrorCodeInfo("CFG_501", ErrorCategory.CONFIGURATION, "Required configuration missing")
    CFG_INVALID_CONFIG = ErrorCodeInfo("CFG_502", ErrorCategory.CONFIGURATION, "Invalid configuration value")
    CFG_ENV_VAR_MISSING = ErrorCodeInfo("CFG_503", ErrorCategory.CONFIGURATION, "Required environment variable not set")
    CFG_FILE_NOT_FOUND = ErrorCodeInfo("CFG_504", ErrorCategory.CONFIGURATION, "Configuration file not found")
    
    # SQL Errors (SQL_600 - SQL_699)
    SQL_SYNTAX_ERROR = ErrorCodeInfo("SQL_601", ErrorCategory.SQL, "SQL syntax error")
    SQL_EXECUTION_ERROR = ErrorCodeInfo("SQL_602", ErrorCategory.SQL, "SQL execution error")
    SQL_NO_RESULTS = ErrorCodeInfo("SQL_603", ErrorCategory.SQL, "Query returned no results")
    SQL_COLUMN_NOT_FOUND = ErrorCodeInfo("SQL_604", ErrorCategory.SQL, "Column not found in query result")
    SQL_TABLE_NOT_FOUND = ErrorCodeInfo("SQL_605", ErrorCategory.SQL, "Table not found")
    SQL_PERMISSION_DENIED = ErrorCodeInfo("SQL_606", ErrorCategory.SQL, "Permission denied for SQL operation")
    
    @property
    def code(self) -> str:
        """Get the error code string."""
        return self.value.code
    
    @property
    def category(self) -> ErrorCategory:
        """Get the error category."""
        return self.value.category
    
    @property
    def description(self) -> str:
        """Get the error description."""
        return self.value.description
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error type is retryable."""
        return self.value.is_retryable


def get_error_code_by_string(code_str: str) -> ErrorCode:
    """
    Get ErrorCode enum by code string.
    
    Args:
        code_str: Error code string (e.g., "AUTH_001")
        
    Returns:
        ErrorCode enum value
        
    Raises:
        ValueError: If code string not found
    """
    for error_code in ErrorCode:
        if error_code.code == code_str:
            return error_code
    raise ValueError(f"Unknown error code: {code_str}")

