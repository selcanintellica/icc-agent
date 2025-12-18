"""
API models package.
"""

from backend.api.models.request import (
    ChatMessageRequest,
    CreateSessionRequest,
    GetSchemasRequest,
    GetTablesRequest,
    SubmitMappingRequest,
    ColumnMapping,
    KeyMapping
)

from backend.api.models.response import (
    ChatMessageResponse,
    SessionResponse,
    ConnectionInfo,
    SchemaInfo,
    ConnectionsResponse,
    SchemasResponse,
    TablesResponse,
    HealthResponse,
    ErrorDetail,
    ErrorCategory
)

__all__ = [
    # Request models
    "ChatMessageRequest",
    "CreateSessionRequest",
    "GetSchemasRequest",
    "GetTablesRequest",
    "SubmitMappingRequest",
    "ColumnMapping",
    "KeyMapping",
    # Response models
    "ChatMessageResponse",
    "SessionResponse",
    "ConnectionInfo",
    "SchemaInfo",
    "ConnectionsResponse",
    "SchemasResponse",
    "TablesResponse",
    "HealthResponse",
    "ErrorDetail",
    "ErrorCategory"
]
