"""
Request models for ICC Agent API.

Pydantic models for validating incoming API requests.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ChatMessageRequest(BaseModel):
    """
    Request model for sending a chat message to the agent.
    """
    session_id: str = Field(
        ...,
        description="Session ID for maintaining conversation context",
        min_length=1
    )
    message: str = Field(
        ...,
        description="User's message/query",
        min_length=1
    )
    connection: Optional[str] = Field(
        None,
        description="Database connection ID (optional)"
    )
    schema: Optional[str] = Field(
        None,
        description="Database schema name (optional)"
    )
    tables: Optional[List[str]] = Field(
        None,
        description="List of selected table names (optional)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "get all customers from USA",
                "connection": "ORACLE_10",
                "schema": "SALES",
                "tables": ["customers", "orders"]
            }
        }


class CreateSessionRequest(BaseModel):
    """
    Request model for creating a new session.
    """
    session_id: Optional[str] = Field(
        None,
        description="Custom session ID (optional, will be generated if not provided)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "my-custom-session-123"
            }
        }


class GetSchemasRequest(BaseModel):
    """
    Request model for fetching schemas for a connection.
    """
    connection_id: str = Field(
        ...,
        description="Database connection ID",
        min_length=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "ORACLE_10"
            }
        }


class GetTablesRequest(BaseModel):
    """
    Request model for fetching tables in a schema.
    """
    connection_id: str = Field(
        ...,
        description="Database connection ID",
        min_length=1
    )
    schema_name: str = Field(
        ...,
        description="Schema name",
        min_length=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "ORACLE_10",
                "schema_name": "SALES"
            }
        }
