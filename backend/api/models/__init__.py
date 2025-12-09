"""
API models package.
"""

from backend.api.models.request import (
    ChatMessageRequest,
    CreateSessionRequest,
    GetSchemasRequest,
    GetTablesRequest
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
