"""
Models package - organized by domain.

This package contains Pydantic models organized into subdirectories:
- jobs/: Job payload models (WirePayload, QueryPayload, RulePayload, etc.)
- api/: API response models (APIResponse, JobResponse)
- validation/: Validation and parameter models (NaturalLanguageModel, etc.)
"""

# Re-export from subdirectories for backward compatibility
from src.models.jobs import (
    WirePayload, WireVariable, WireProps,
    QueryPayload, QueryResponse,
    RulePayload, RuleBuilder
)
from src.models.api import APIResponse, JobResponse
from src.models.validation import (

    ReadSqlLLMRequest,
    ReadSqlVariables,
    WriteDataLLMRequest,
    WriteDataVariables,
    SendEmailLLMRequest,
    SendEmailVariables,
    CompareSqlLLMRequest,
    CompareSqlVariables,
    ColumnSchema,

)

__all__ = [
    # Job models
    "WirePayload", "WireVariable", "WireProps",
    "QueryPayload", "QueryResponse",
    "RulePayload", "RuleBuilder",
    # API models
    "APIResponse", "JobResponse",
    # Validation models
    "NaturalLanguageModel",
    "ReadSqlLLMRequest",
    "ReadSqlVariables",
    "WriteDataLLMRequest",
    "WriteDataVariables",
    "SendEmailLLMRequest",
    "SendEmailVariables",
    "CompareSqlLLMRequest",
    "CompareSqlVariables",
    "ColumnSchema",
    "DefinitionMap",
]
