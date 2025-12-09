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
        
        # Get connection names from config
        connection_names = connection_service._config_loader.get_available_connections()
        
        # Format response - use connection name as ID since we don't have actual IDs in config
        connection_list = [
            ConnectionInfo(
                id=name,  # Use name as ID for config-based connections
                name=name,
                type="database"  # Generic type since config doesn't specify
            )
            for name in connection_names
        ]
        
        return ConnectionsResponse(
            connections=connection_list,
            count=len(connection_list)
        )
    
    except ICCBaseError as e:
        logger.error(f"ICC error listing connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
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
        
        # Get schemas for this connection (connection_id is the connection name)
        schema_names = connection_service._config_loader.get_schemas_for_connection(connection_id)
        
        if not schema_names:
            raise HTTPException(
                status_code=404,
                detail=f"Connection not found or has no schemas: {connection_id}"
            )
        
        # Format response with tables for each schema
        schema_list = []
        for schema_name in schema_names:
            tables = connection_service._config_loader.get_tables_for_schema(connection_id, schema_name)
            # Handle both dict format (with columns) and list format
            if isinstance(tables, dict):
                table_names = list(tables.keys())
            else:
                table_names = tables
            
            schema_list.append(
                SchemaInfo(
                    name=schema_name,
                    tables=table_names
                )
            )
        
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
    - **connection_id**: Database connection ID (connection name)
    - **schema_name**: Schema name
    
    **Returns:**
    - List of table names
    """
    try:
        logger.info(f"Fetching tables for {connection_id}.{schema_name}")
        
        # Get tables for this schema
        tables = connection_service._config_loader.get_tables_for_schema(connection_id, schema_name)
        
        # Handle both dict format (with columns) and list format
        if isinstance(tables, dict):
            table_names = list(tables.keys())
        else:
            table_names = tables
        
        if not table_names:
            raise HTTPException(
                status_code=404,
                detail=f"Schema not found or has no tables: {connection_id}.{schema_name}"
            )
        
        return TablesResponse(
            connection_id=connection_id,
            schema_name=schema_name,
            tables=table_names,
            count=len(table_names)
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
