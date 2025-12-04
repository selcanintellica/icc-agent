"""
User-friendly error message templates for ICC application.

Provides contextual, helpful error messages for different scenarios.
Messages are designed to be:
- Clear and understandable
- Actionable (tell user what to do)
- Non-technical
"""

from typing import Dict, Any, Optional
from .error_codes import ErrorCode, ErrorCategory


class ErrorMessages:
    """
    User-friendly error message templates.
    
    Messages are organized by error code and can include dynamic values.
    """
    
    # Default messages by category
    CATEGORY_DEFAULTS: Dict[ErrorCategory, str] = {
        ErrorCategory.AUTHENTICATION: (
            "There was an authentication issue. Please refresh the page and try again. "
            "If the problem persists, contact your administrator."
        ),
        ErrorCategory.CONNECTION: (
            "Unable to connect to the server. Please check your internet connection "
            "and try again in a moment."
        ),
        ErrorCategory.VALIDATION: (
            "The provided information is not valid. Please check your inputs and try again."
        ),
        ErrorCategory.JOB: (
            "There was an issue with the job operation. Please review your settings and try again."
        ),
        ErrorCategory.LLM: (
            "The AI assistant encountered an issue. Please try rephrasing your request "
            "or simplifying your query."
        ),
        ErrorCategory.CONFIGURATION: (
            "There's a system configuration issue. Please contact your administrator for assistance."
        ),
        ErrorCategory.SQL: (
            "There was an issue with the SQL query. Please check the syntax and try again."
        ),
    }
    
    # Specific messages by error code
    CODE_MESSAGES: Dict[ErrorCode, str] = {
        # Authentication
        ErrorCode.AUTH_FAILED: (
            "Authentication failed. Please try logging in again."
        ),
        ErrorCode.AUTH_TOKEN_EXPIRED: (
            "Your session has expired. Please refresh the page to continue."
        ),
        ErrorCode.AUTH_INVALID_CREDENTIALS: (
            "The provided credentials are invalid. Please check and try again."
        ),
        ErrorCode.AUTH_NO_CREDENTIALS: (
            "Authentication is not configured. Please contact your administrator."
        ),
        ErrorCode.AUTH_TOKEN_FETCH_FAILED: (
            "Unable to authenticate at this time. Please try again in a moment."
        ),
        
        # Connection
        ErrorCode.CONN_NETWORK_TIMEOUT: (
            "The connection timed out. Please check your network and try again."
        ),
        ErrorCode.CONN_API_UNAVAILABLE: (
            "The service is temporarily unavailable. Please try again in a few moments."
        ),
        ErrorCode.CONN_DATABASE_ERROR: (
            "Unable to connect to the database. Please verify the connection settings."
        ),
        ErrorCode.CONN_UNKNOWN_CONNECTION: (
            "The specified connection was not found. Please select a valid connection from the list."
        ),
        ErrorCode.CONN_HTTP_ERROR: (
            "A network error occurred while communicating with the server. Please try again."
        ),
        ErrorCode.CONN_SSL_ERROR: (
            "A secure connection could not be established. Please contact your administrator."
        ),
        ErrorCode.CONN_DNS_ERROR: (
            "Unable to resolve the server address. Please check your network connection."
        ),
        
        # Validation
        ErrorCode.VAL_INVALID_PARAMETER: (
            "One of the provided values is invalid. Please check your inputs."
        ),
        ErrorCode.VAL_MISSING_PARAMETER: (
            "A required value is missing. Please provide all required information."
        ),
        ErrorCode.VAL_INVALID_SQL: (
            "The SQL query is not valid. Please check the syntax and try again."
        ),
        ErrorCode.VAL_INVALID_EMAIL: (
            "The email address format is invalid. Please provide a valid email (e.g., user@example.com)."
        ),
        ErrorCode.VAL_INVALID_CONNECTION: (
            "The connection configuration is invalid. Please check and try again."
        ),
        ErrorCode.VAL_INVALID_SCHEMA: (
            "The schema name is invalid. Please select a valid schema from the list."
        ),
        ErrorCode.VAL_INVALID_TABLE: (
            "The table name is invalid. Please check the table name and try again."
        ),
        ErrorCode.VAL_EMPTY_INPUT: (
            "No input was provided. Please enter a value and try again."
        ),
        ErrorCode.VAL_INVALID_JSON: (
            "The data format is invalid. Please try again."
        ),
        
        # Job
        ErrorCode.JOB_CREATION_FAILED: (
            "Unable to create the job. Please check your settings and try again."
        ),
        ErrorCode.JOB_DUPLICATE_NAME: (
            "A job with this name already exists. Please choose a different name."
        ),
        ErrorCode.JOB_EXECUTION_FAILED: (
            "The job could not be executed. Please check the job configuration and try again."
        ),
        ErrorCode.JOB_NOT_FOUND: (
            "The specified job was not found. It may have been deleted or moved."
        ),
        ErrorCode.JOB_INVALID_STATE: (
            "The job is in an invalid state for this operation. Please try again."
        ),
        ErrorCode.JOB_MISSING_DATASET: (
            "The required data is not available. Please run the previous step first."
        ),
        ErrorCode.JOB_COLUMN_MISMATCH: (
            "The columns don't match between the datasets. Please check the column mappings."
        ),
        
        # LLM
        ErrorCode.LLM_TIMEOUT: (
            "The AI is taking longer than expected. Please try a simpler request or try again later."
        ),
        ErrorCode.LLM_PARSING_ERROR: (
            "The AI response couldn't be understood. Please rephrase your request."
        ),
        ErrorCode.LLM_UNAVAILABLE: (
            "The AI assistant is temporarily unavailable. Please try again in a moment."
        ),
        ErrorCode.LLM_INVALID_RESPONSE: (
            "The AI provided an unexpected response. Please try rephrasing your request."
        ),
        ErrorCode.LLM_CONTEXT_TOO_LONG: (
            "Your request is too complex. Please try breaking it into smaller parts."
        ),
        ErrorCode.LLM_RATE_LIMITED: (
            "Too many requests. Please wait a moment before trying again."
        ),
        
        # Configuration
        ErrorCode.CFG_MISSING_CONFIG: (
            "A required configuration is missing. Please contact your administrator."
        ),
        ErrorCode.CFG_INVALID_CONFIG: (
            "There's a configuration error. Please contact your administrator."
        ),
        ErrorCode.CFG_ENV_VAR_MISSING: (
            "A required system setting is missing. Please contact your administrator."
        ),
        ErrorCode.CFG_FILE_NOT_FOUND: (
            "A configuration file is missing. Please contact your administrator."
        ),
        
        # SQL
        ErrorCode.SQL_SYNTAX_ERROR: (
            "The SQL query has a syntax error. Please review and correct the query."
        ),
        ErrorCode.SQL_EXECUTION_ERROR: (
            "The SQL query could not be executed. Please check the query and try again."
        ),
        ErrorCode.SQL_NO_RESULTS: (
            "The query returned no results. Try adjusting your search criteria."
        ),
        ErrorCode.SQL_COLUMN_NOT_FOUND: (
            "The specified column was not found. Please check the column name."
        ),
        ErrorCode.SQL_TABLE_NOT_FOUND: (
            "The specified table was not found. Please verify the table name and schema."
        ),
        ErrorCode.SQL_PERMISSION_DENIED: (
            "You don't have permission to perform this SQL operation."
        ),
    }
    
    @classmethod
    def get_message(
        cls,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get user-friendly message for an error code.
        
        Args:
            error_code: The error code
            context: Optional context for message customization
            
        Returns:
            User-friendly error message
        """
        # Try specific message first
        message = cls.CODE_MESSAGES.get(error_code)
        
        # Fall back to category default
        if not message:
            message = cls.CATEGORY_DEFAULTS.get(
                error_code.category,
                "An unexpected error occurred. Please try again."
            )
        
        # Apply context substitutions if provided
        if context:
            message = cls._apply_context(message, context)
        
        return message
    
    @classmethod
    def _apply_context(cls, message: str, context: Dict[str, Any]) -> str:
        """Apply context values to message template."""
        try:
            # Simple placeholder replacement for common fields
            if "{job_name}" in message and "job_name" in context:
                message = message.replace("{job_name}", str(context["job_name"]))
            if "{connection_name}" in message and "connection_name" in context:
                message = message.replace("{connection_name}", str(context["connection_name"]))
            if "{table_name}" in message and "table_name" in context:
                message = message.replace("{table_name}", str(context["table_name"]))
            if "{schema_name}" in message and "schema_name" in context:
                message = message.replace("{schema_name}", str(context["schema_name"]))
            if "{email}" in message and "email" in context:
                message = message.replace("{email}", str(context["email"]))
        except Exception:
            # If formatting fails, return original message
            pass
        return message
    
    @classmethod
    def format_with_details(
        cls,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format error message with additional helpful details.
        
        Args:
            error_code: The error code
            details: Additional details to include
            
        Returns:
            Formatted error message with details
        """
        base_message = cls.get_message(error_code, details)
        
        if not details:
            return base_message
        
        # Add specific details for certain error types
        extra_info = []
        
        if "job_name" in details:
            if error_code == ErrorCode.JOB_DUPLICATE_NAME:
                # Already in message, skip
                pass
        
        if "connection_name" in details:
            if error_code == ErrorCode.CONN_UNKNOWN_CONNECTION:
                extra_info.append(f"Connection: {details['connection_name']}")
        
        if "parameter_name" in details:
            extra_info.append(f"Field: {details['parameter_name']}")
        
        if extra_info:
            return f"{base_message}\n\nDetails: {', '.join(extra_info)}"
        
        return base_message


class ErrorMessageBuilder:
    """Builder for constructing contextual error messages."""
    
    def __init__(self, error_code: ErrorCode):
        """Initialize builder with error code."""
        self.error_code = error_code
        self.context: Dict[str, Any] = {}
        self.suggestions: list = []
    
    def with_job_name(self, job_name: str) -> "ErrorMessageBuilder":
        """Add job name to context."""
        self.context["job_name"] = job_name
        return self
    
    def with_connection(self, connection_name: str) -> "ErrorMessageBuilder":
        """Add connection name to context."""
        self.context["connection_name"] = connection_name
        return self
    
    def with_table(self, table_name: str, schema_name: Optional[str] = None) -> "ErrorMessageBuilder":
        """Add table info to context."""
        self.context["table_name"] = table_name
        if schema_name:
            self.context["schema_name"] = schema_name
        return self
    
    def with_suggestion(self, suggestion: str) -> "ErrorMessageBuilder":
        """Add a suggestion for the user."""
        self.suggestions.append(suggestion)
        return self
    
    def build(self) -> str:
        """Build the final error message."""
        message = ErrorMessages.get_message(self.error_code, self.context)
        
        if self.suggestions:
            suggestions_text = "\n".join(f"- {s}" for s in self.suggestions)
            message = f"{message}\n\nSuggestions:\n{suggestions_text}"
        
        return message

