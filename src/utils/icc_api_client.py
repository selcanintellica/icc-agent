"""
ICC API Client - Unified interface for all ICC API interactions.

This module provides:
- Connection list fetching
- Schema list fetching for a specific connection
- Authentication handling
- Response mapping to internal formats
"""
from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from src.utils.auth import authenticate

logger = logging.getLogger(__name__)


class ICCAPIClient:
    """Client for ICC API operations with authentication."""
    
    def __init__(self, base_url: Optional[str] = None, auth_headers: Optional[Dict[str, str]] = None):
        """
        Initialize ICC API client.
        
        Args:
            base_url: Base URL for ICC API (e.g., https://172.16.22.13:8084)
            auth_headers: Optional authentication headers (Authorization and TokenKey)
        """
        self.base_url = base_url or os.getenv("ICC_API_BASE_URL", "https://172.16.22.13:8084")
        self.auth_headers = auth_headers or {}
        self.timeout = 30.0
    
    async def fetch_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all available connections from ICC API.
        
        Returns:
            Dictionary mapping connection names to their info:
            {
                "ORACLE_10": {
                    "id": "4976629955435844",
                    "db_type": "Oracle",
                    "url": "jdbc:oracle:thin:@...",
                    "user": "icc_test"
                },
                ...
            }
        """
        endpoint = f"{self.base_url}/connection/list"
        logger.info(f"🔌 Fetching connections from: {endpoint}")
        
        try:
            async with httpx.AsyncClient(headers=self.auth_headers, verify=False, timeout=self.timeout) as client:
                resp = await client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
                
                objects = data.get('object', [])
                logger.info(f"✅ Fetched {len(objects)} connections")
                
                return self._map_connections(objects)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching connections: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching connections: {e}")
            raise
    
    async def fetch_schemas(self, connection_id: str) -> List[str]:
        """
        Fetch available schemas for a specific connection.
        
        Args:
            connection_id: The connection ID (e.g., "4976629955435844")
            
        Returns:
            List of schema names:
            ["ANONYMOUS", "HR", "ICC_META", "SYSTEM", ...]
        """
        endpoint = f"{self.base_url}/utility/connection/{connection_id}"
        logger.info(f"📋 Fetching schemas from: {endpoint}")
        
        try:
            async with httpx.AsyncClient(headers=self.auth_headers, verify=False, timeout=self.timeout) as client:
                # POST request without body
                resp = await client.post(endpoint)
                resp.raise_for_status()
                schemas = resp.json()
                
                if not isinstance(schemas, list):
                    logger.warning(f"⚠️ Expected list of schemas, got {type(schemas)}")
                    return []
                
                logger.info(f"✅ Fetched {len(schemas)} schemas")
                return schemas
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching schemas: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching schemas: {e}")
            raise
    
    def _map_connections(self, objects: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Map raw connection objects to internal format.
        
        Args:
            objects: List of connection objects from API
            
        Returns:
            Dictionary mapping connection names to their info
        """
        result: Dict[str, Dict[str, Any]] = {}
        skipped = 0
        
        for obj in objects:
            mapped = self._map_connection_object(obj)
            if not mapped:
                skipped += 1
                continue
            name, payload = mapped
            result[name] = payload
        
        logger.info(f"✅ Mapped {len(result)} connections (skipped {skipped} invalid)")
        return result
    
    def _map_connection_object(self, obj: Dict[str, Any]) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Map a single connection object to internal format.
        
        Args:
            obj: Connection object from API
            
        Returns:
            Tuple of (name, connection_info) or None if invalid
        """
        conn_id = obj.get("id")
        props = obj.get("props") or {}
        name = props.get("name")
        
        if not name or not conn_id:
            logger.debug(f"Skipping connection with missing name or id")
            return None
        
        database_url = obj.get("databaseUrl") or ""
        database_user = obj.get("databaseUser") or ""
        connection_type = obj.get("connectionType") or ""
        endpoint = obj.get("endpoint") or ""
        storage_account_name = obj.get("storageAccountName") or ""
        
        # Choose URL
        if connection_type == "oauth2":
            url = endpoint or database_url or None
        else:
            url = database_url or endpoint or None
        
        # Choose user
        if database_user:
            user = database_user
        elif storage_account_name:
            user = storage_account_name
        else:
            user = None
        
        db_type = self._infer_db_type(name=name, database_url=url, connection_type=connection_type)
        
        return name, {
            "id": conn_id,
            "db_type": db_type,
            "url": url,
            "user": user,
        }
    
    def _infer_db_type(self, name: str, database_url: Optional[str], connection_type: str) -> str:
        """
        Infer database type from connection details.
        
        Args:
            name: Connection name
            database_url: JDBC URL or connection string
            connection_type: Connection type
            
        Returns:
            Database type string
        """
        url = (database_url or "").lower()
        name_lower = name.lower()
        ctype = (connection_type or "").lower()
        
        if "jdbc:postgresql" in url or "postgre" in name_lower:
            return "PostgreSQL"
        if "jdbc:oracle" in url or "oracle" in name_lower:
            return "Oracle"
        if "jdbc:sqlserver" in url or "mssql" in name_lower or "sql server" in name_lower:
            return "SQL Server"
        if "jdbc:hive2" in url or "hive" in name_lower:
            return "Hive"
        if "jdbc:sap" in url or "hana" in name_lower:
            return "SAP HANA"
        if url.startswith("mongodb") or "mongo" in name_lower:
            return "MongoDB"
        if url.startswith("jdbc:cassandra") or "cassandra" in name_lower:
            return "Cassandra"
        if "snowflakecomputing.com" in url or "snowflake" in name_lower:
            return "Snowflake"
        if ctype == "oauth2":
            return "Azure Data Lake"
        if url.startswith("ftp://") or "sftp" in name_lower:
            return "SFTP"
        
        return "Generic"


async def populate_memory_connections(memory, auth_headers: Optional[Dict[str, str]] = None) -> bool:
    """
    Fetch connections from ICC API and populate memory.
    
    Args:
        memory: Memory instance to populate
        auth_headers: Optional authentication headers
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = ICCAPIClient(auth_headers=auth_headers)
        connections = await client.fetch_connections()
        memory.connections = connections
        logger.info(f"✅ Populated memory with {len(connections)} connections")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to populate memory connections: {e}", exc_info=True)
        return False


async def fetch_schemas_for_connection(connection_id: str, auth_headers: Optional[Dict[str, str]] = None) -> List[str]:
    """
    Fetch available schemas for a specific connection.
    
    Args:
        connection_id: The connection ID
        auth_headers: Optional authentication headers
        
    Returns:
        List of schema names
    """
    try:
        client = ICCAPIClient(auth_headers=auth_headers)
        schemas = await client.fetch_schemas(connection_id)
        return schemas
    except Exception as e:
        logger.error(f"❌ Failed to fetch schemas: {e}", exc_info=True)
        return []


if __name__ == "__main__":
    """
    Test script for ICC API client.
    
    Usage:
        python src/utils/icc_api_client.py
    """
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_api():
        # Get authentication
        try:
            userpass, token = authenticate()
            auth_headers = {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return
        
        client = ICCAPIClient(auth_headers=auth_headers)
        
        # Test 1: Fetch connections
        print("\n🔌 Testing connection fetch...")
        try:
            connections = await client.fetch_connections()
            print(f"✅ Fetched {len(connections)} connections")
            
            # Show first few
            for i, (name, info) in enumerate(list(connections.items())[:5]):
                print(f"  • {name} ({info['db_type']}) - ID: {info['id']}")
            
            # Test 2: Fetch schemas for first connection
            if connections:
                first_name = list(connections.keys())[0]
                first_id = connections[first_name]["id"]
                
                print(f"\n📋 Testing schema fetch for {first_name} (ID: {first_id})...")
                schemas = await client.fetch_schemas(first_id)
                print(f"✅ Fetched {len(schemas)} schemas")
                print(f"  First 10: {schemas[:10]}")
        
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    asyncio.run(test_api())
