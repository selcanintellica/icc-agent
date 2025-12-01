"""
Connection and schema fetching utility.

Provides reusable methods for fetching connections and schemas following DRY principle.
"""

import logging
from typing import Dict, Any
from src.ai.router.stage_handlers.base_handler import StageHandlerResult
from src.ai.router.memory import Memory

logger = logging.getLogger(__name__)


class ConnectionFetcher:
    """
    Utility class for fetching connections and schemas from API.
    
    Following Single Responsibility Principle - only responsible for API communication.
    """
    
    @staticmethod
    async def fetch_connections(memory: Memory) -> Dict[str, Any]:
        """
        Fetch all available connections from API and store in memory.
        
        Args:
            memory: Conversation memory to store connections
            
        Returns:
            Dict with success status, message, and fetched connections
        """
        logger.info("📋 Fetching all available connections...")
        
        try:
            from src.utils.connection_api_client import ConnectionAPIClient
            from src.utils.auth import authenticate
            
            userpass, token = await authenticate()
            client = ConnectionAPIClient(userpass=userpass, token=token)
            connections_dict = await client.fetch_connections()
            
            memory.connections = connections_dict
            logger.info(f"✅ Fetched {len(connections_dict)} connections")
            
            return {
                "success": True,
                "message": f"Fetched {len(connections_dict)} connections",
                "connections": connections_dict
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching connections: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to fetch connections: {str(e)}",
                "connections": {}
            }
    
    @staticmethod
    async def fetch_schemas(connection_name: str, memory: Memory) -> Dict[str, Any]:
        """
        Fetch schemas for a specific connection and store in memory.
        
        Args:
            connection_name: Name of the connection
            memory: Conversation memory to store schemas
            
        Returns:
            Dict with success status, message, and fetched schemas
        """
        logger.info(f"📋 Fetching schemas for connection: {connection_name}")
        
        try:
            from src.utils.connection_api_client import fetch_schemas_for_connection
            from src.utils.auth import authenticate
            
            connection_id = memory.get_connection_id(connection_name)
            if not connection_id:
                return {
                    "success": False,
                    "message": f"Unknown connection: {connection_name}",
                    "schemas": []
                }
            
            userpass, token = await authenticate()
            auth_headers = {
                "Authorization": f"Basic {userpass}",
                "TokenKey": token
            }
            
            schemas = await fetch_schemas_for_connection(connection_id, auth_headers=auth_headers)
            memory.available_schemas = schemas
            logger.info(f"✅ Fetched {len(schemas)} schemas for {connection_name}")
            
            return {
                "success": True,
                "message": f"Fetched {len(schemas)} schemas",
                "schemas": schemas
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching schemas: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to fetch schemas: {str(e)}",
                "schemas": []
            }
    
    @staticmethod
    def create_connection_question(memory: Memory, purpose: str = "main") -> str:
        """
        Create a question asking user to select a connection.
        
        Args:
            memory: Conversation memory with connections
            purpose: Purpose of the connection ("main", "write_count", etc.)
            
        Returns:
            Formatted question string with connection list
        """
        connection_list = memory.get_connection_list_for_llm()
        
        if purpose == "write_count":
            base_question = "Which connection should I use for the row count?"
            default_hint = f"\n\n(Or press enter to use '{memory.connection}')"
        else:
            base_question = "Which connection should I use?"
            default_hint = ""
        
        if connection_list:
            return f"{base_question}\n\nAvailable connections:\n{connection_list}{default_hint}"
        else:
            return base_question + default_hint
    
    @staticmethod
    def create_schema_question(memory: Memory, purpose: str = "main") -> str:
        """
        Create a question asking user to select a schema.
        
        Args:
            memory: Conversation memory with schemas
            purpose: Purpose of the schema ("main", "write_count", "result")
            
        Returns:
            Formatted question string with schema list
        """
        schema_list = memory.get_schema_list_for_llm()
        
        if purpose == "write_count":
            base_question = "Which schema should I write the row count to?"
        elif purpose == "result":
            base_question = "Which schema should I write the results to?"
        elif purpose == "data":
            base_question = "Which schema should I write the data to?"
        else:
            base_question = "Which schema should I use?"
        
        if schema_list:
            return f"{base_question}\n\nAvailable schemas:\n{schema_list}"
        else:
            return base_question
