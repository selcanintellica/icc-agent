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
    schema_name: Optional[str] = Field(
        None,
        description="Database schema name (optional)",
        alias="schema"  # Accept 'schema' in JSON but use 'schema_name' internally
    )
    tables: Optional[List[str]] = Field(
        None,
        description="List of selected table names (optional)"
    )
    
    class Config:
        populate_by_name = True  # Allow using both 'schema' and 'schema_name'
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


class ColumnMapping(BaseModel):
    """
    Single column mapping between two queries.
    """
    first_column: str = Field(
        ...,
        description="Column name from first query",
        min_length=1,
        alias="FirstMappedColumn"
    )
    second_column: str = Field(
        ...,
        description="Column name from second query",
        min_length=1,
        alias="SecondMappedColumn"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "FirstMappedColumn": "customer_id",
                "SecondMappedColumn": "cust_id"
            }
        }


class KeyMapping(BaseModel):
    """
    Key mapping for joining two queries.
    """
    first_key: str = Field(
        ...,
        description="Key column from first query",
        min_length=1,
        alias="FirstKey"
    )
    second_key: str = Field(
        ...,
        description="Key column from second query",
        min_length=1,
        alias="SecondKey"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "FirstKey": "customer_id",
                "SecondKey": "cust_id"
            }
        }


class SubmitMappingRequest(BaseModel):
    """
    Request model for submitting column mappings.
    """
    session_id: str = Field(
        ...,
        description="Session ID for maintaining conversation context",
        min_length=1
    )
    column_mappings: List[ColumnMapping] = Field(
        ...,
        description="List of column mappings between the two queries",
        min_items=1
    )
    key_mappings: List[KeyMapping] = Field(
        default_factory=list,
        description="List of key mappings for joining the two queries"
    )
    connection: Optional[str] = Field(
        None,
        description="Database connection ID (optional)"
    )
    schema_name: Optional[str] = Field(
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
                "column_mappings": [
                    {"FirstMappedColumn": "customer_id", "SecondMappedColumn": "cust_id"},
                    {"FirstMappedColumn": "name", "SecondMappedColumn": "customer_name"}
                ],
                "key_mappings": [
                    {"FirstKey": "customer_id", "SecondKey": "cust_id"}
                ],
                "connection": "ORACLE_10",
                "schema_name": "SALES",
                "tables": ["customers", "orders"]
            }
        }
