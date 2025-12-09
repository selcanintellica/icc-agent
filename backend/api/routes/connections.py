"""
Connection endpoints for ICC Agent API.

Handles database connection, schema, and table metadata operations.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from backend.api.models import (
    ConnectionsResponse,
    SchemasResponse,
    TablesResponse,
    ConnectionInfo,
    SchemaInfo
)

from src.services import get_connection_service
from src.errors import ICCBaseError, ErrorHandler

logger = logging.getLogger(__name__)

router = APIRouter()


def get_connection_service_dependency():
    """Dependency for connection service"""
    return get_connection_service()


@router.get("", response_model=ConnectionsResponse)
async def list_connections(
    connection_service = Depends(get_connection_service_dependency)
) -> ConnectionsResponse:
    """
    Get list of all available database connections.
    
    **Returns:**
    - List of connections with ID, name, and type
    """
    try:
        logger.info("Fetching available connections")
        
        # Get connections from service
        config = connection_service.get_initial_config()
        connections = config.get("connections", [])
        
        # Format response
        connection_list = [
            ConnectionInfo(
                id=str(conn.get("id", "")),
                name=conn.get("name", ""),
                type=conn.get("type", "unknown")
            )
            for conn in connections
        ]
        
        return ConnectionsResponse(
            connections=connection_list,
            count=len(connection_list)
        )
    
    except ICCBaseError as e:
        logger.error(f"ICC error listing connections: {e}", exc_info=True)
        error_info = ErrorHandler.handle_error(e)
        raise HTTPException(status_code=500, detail=error_info.message)
    
    except Exception as e:
        logger.error(f"Error listing connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connection_id}/schemas", response_model=SchemasResponse)
async def list_schemas(
    connection_id: str,
    connection_service = Depends(get_connection_service_dependency)
) -> SchemasResponse:
    """
    Get list of schemas for a specific connection.
    
    **Parameters:**
    - **connection_id**: Database connection ID
    
    **Returns:**
    - List of schemas with their tables
    """
    try:
        logger.info(f"Fetching schemas for connection: {connection_id}")
        
        # Get initial config
        config = connection_service.get_initial_config()
        connections = config.get("connections", [])
        
        # Find the connection
        connection = next(
            (c for c in connections if str(c.get("id")) == connection_id),
            None
        )
        
        if not connection:
            raise HTTPException(
                status_code=404,
                detail=f"Connection not found: {connection_id}"
            )
        
        # Get schemas
        schemas = connection.get("schemas", [])
        
        # Format response
        schema_list = [
            SchemaInfo(
                name=schema.get("name", ""),
                tables=schema.get("tables", [])
            )
            for schema in schemas
        ]
        
        return SchemasResponse(
            connection_id=connection_id,
            schemas=schema_list,
            count=len(schema_list)
        )
    
    except HTTPException:
        raise
    
    except ICCBaseError as e:
        logger.error(f"ICC error listing schemas: {e}", exc_info=True)
        error_info = ErrorHandler.handle_error(e)
        raise HTTPException(status_code=500, detail=error_info.message)
    
    except Exception as e:
        logger.error(f"Error listing schemas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connection_id}/schemas/{schema_name}/tables", response_model=TablesResponse)
async def list_tables(
    connection_id: str,
    schema_name: str,
    connection_service = Depends(get_connection_service_dependency)
) -> TablesResponse:
    """
    Get list of tables in a specific schema.
    
    **Parameters:**
    - **connection_id**: Database connection ID
    - **schema_name**: Schema name
    
    **Returns:**
    - List of table names
    """
    try:
        logger.info(f"Fetching tables for {connection_id}.{schema_name}")
        
        # Get initial config
        config = connection_service.get_initial_config()
        connections = config.get("connections", [])
        
        # Find the connection
        connection = next(
            (c for c in connections if str(c.get("id")) == connection_id),
            None
        )
        
        if not connection:
            raise HTTPException(
                status_code=404,
                detail=f"Connection not found: {connection_id}"
            )
        
        # Find the schema
        schemas = connection.get("schemas", [])
        schema = next(
            (s for s in schemas if s.get("name") == schema_name),
            None
        )
        
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"Schema not found: {schema_name}"
            )
        
        # Get tables
        tables = schema.get("tables", [])
        
        return TablesResponse(
            connection_id=connection_id,
            schema_name=schema_name,
            tables=tables,
            count=len(tables)
        )
    
    except HTTPException:
        raise
    
    except ICCBaseError as e:
        logger.error(f"ICC error listing tables: {e}", exc_info=True)
        error_info = ErrorHandler.handle_error(e)
        raise HTTPException(status_code=500, detail=error_info.message)
    
    except Exception as e:
        logger.error(f"Error listing tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
