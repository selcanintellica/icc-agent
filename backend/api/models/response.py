"""
Response models for ICC Agent API.

Pydantic models for structuring API responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ErrorCategory(str, Enum):
    """Error categories"""
    AUTHENTICATION = "authentication"
    CONNECTION = "connection"
    VALIDATION = "validation"
    JOB = "job"
    LLM = "llm"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class ErrorDetail(BaseModel):
    """
    Error detail structure.
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    category: ErrorCategory = Field(..., description="Error category")


class ChatMessageResponse(BaseModel):
    """
    Response model for chat message.
    """
    session_id: str = Field(..., description="Session ID")
    response: str = Field(..., description="Agent's response message")
    stage: Optional[str] = Field(None, description="Current conversation stage")
    gathered_params: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters gathered so far"
    )
    job_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Job-specific context (SQL, results, etc.)"
    )
    requires_dropdown: Optional[bool] = Field(
        False,
        description="Whether response requires dropdown selection"
    )
    dropdown_type: Optional[str] = Field(
        None,
        description="Type of dropdown (connection, schema, table)"
    )
    dropdown_options: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Dropdown options if requires_dropdown is True"
    )
    requires_mapping: Optional[bool] = Field(
        False,
        description="Whether response requires column mapping (for compare SQL)"
    )
    mapping_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Column mapping data (first_columns, second_columns, auto_matched, pre_mappings)"
    )
    error: Optional[ErrorDetail] = Field(
        None,
        description="Error details if request failed"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "Here's the SQL query:\nSELECT * FROM customers WHERE country = 'USA'\n\nLooks good?",
                "stage": "confirm_generated_sql",
                "gathered_params": {},
                "job_context": {
                    "sql_query": "SELECT * FROM customers WHERE country = 'USA'"
                },
                "requires_dropdown": False,
                "error": None
            }
        }


class SessionResponse(BaseModel):
    """
    Response model for session operations.
    """
    session_id: str = Field(..., description="Session ID")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    stage: Optional[str] = Field(None, description="Current stage")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-12-09T10:30:00Z",
                "stage": "router",
                "message": "Session created successfully"
            }
        }


class ConnectionInfo(BaseModel):
    """
    Database connection information.
    """
    id: str = Field(..., description="Connection ID")
    name: str = Field(..., description="Connection name")
    type: str = Field(..., description="Database type (oracle, postgres, etc.)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "4976629955435844",
                "name": "ORACLE_10",
                "type": "oracle"
            }
        }


class SchemaInfo(BaseModel):
    """
    Database schema information.
    """
    name: str = Field(..., description="Schema name")
    tables: Optional[List[str]] = Field(None, description="List of tables in schema")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "SALES",
                "tables": ["customers", "orders", "products"]
            }
        }


class ConnectionsResponse(BaseModel):
    """
    Response model for listing connections.
    """
    connections: List[ConnectionInfo] = Field(..., description="List of available connections")
    count: int = Field(..., description="Number of connections")
    
    class Config:
        json_schema_extra = {
            "example": {
                "connections": [
                    {"id": "4976629955435844", "name": "ORACLE_10", "type": "oracle"},
                    {"id": "4976629955435845", "name": "POSTGRES_01", "type": "postgres"}
                ],
                "count": 2
            }
        }


class SchemasResponse(BaseModel):
    """
    Response model for listing schemas.
    """
    connection_id: str = Field(..., description="Connection ID")
    schemas: List[SchemaInfo] = Field(..., description="List of schemas")
    count: int = Field(..., description="Number of schemas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "ORACLE_10",
                "schemas": [
                    {"name": "SALES", "tables": ["customers", "orders"]},
                    {"name": "HR", "tables": ["employees", "departments"]}
                ],
                "count": 2
            }
        }


class TablesResponse(BaseModel):
    """
    Response model for listing tables.
    """
    connection_id: str = Field(..., description="Connection ID")
    schema_name: str = Field(..., description="Schema name")
    tables: List[str] = Field(..., description="List of table names")
    count: int = Field(..., description="Number of tables")
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "ORACLE_10",
                "schema_name": "SALES",
                "tables": ["customers", "orders", "products", "order_items"],
                "count": 4
            }
        }


class HealthResponse(BaseModel):
    """
    Response model for health check.
    """
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    services: Dict[str, str] = Field(..., description="Status of dependent services")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-12-09T10:30:00Z",
                "services": {
                    "router": "ok",
                    "session_manager": "ok",
                    "connection_service": "ok"
                }
            }
        }
