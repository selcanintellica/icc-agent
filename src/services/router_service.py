"""
Router service for handling agent interactions.

Extracts router invocation logic from app.py following SOLID principles:
- Single Responsibility: Only handles router operations
- Dependency Inversion: Depends on router abstraction
"""

import logging
from typing import Dict, Any, Optional, List
from src.ai.router import handle_turn, Memory

logger = logging.getLogger(__name__)


class RouterService:
    """
    Service for managing router interactions and memory population.
    
    Encapsulates the complexity of invoking the router with proper
    memory management and connection population.
    """
    
    @staticmethod
    async def invoke_router(
        user_input: str,
        memory: Memory,
        connection: Optional[str] = None,
        schema: Optional[str] = None,
        selected_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Invoke the router with user input and memory.
        
        Args:
            user_input: User's input message
            memory: Session memory
            connection: Database connection name
            schema: Database schema name
            selected_tables: List of selected table names
            
        Returns:
            Dict with response and optional error information
        """
        try:
            # Populate memory with connection info if provided
            if connection and schema and selected_tables:
                logger.debug(f"Populating memory: {connection}.{schema}, tables: {selected_tables}")
                # Set connection info directly on memory
                memory.connection_manager.default_connection = connection
                memory.connection_manager.default_schema = schema
                memory.connection_manager.selected_tables = selected_tables
            
            # Invoke router
            logger.info(f"Invoking router with input: {user_input[:50]}...")
            memory, response_text = await handle_turn(memory, user_input)
            
            return {
                "response": response_text,
                "memory": memory,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invoking router: {e}", exc_info=True)
            
            # Format error response
            from src.services.ui_formatter import UIFormatter
            error_info = UIFormatter.format_error_for_ui(e)
            
            return {
                "error": str(e),
                "error_info": error_info,
                "memory": memory,
                "success": False
            }
    
    @staticmethod
    def validate_configuration(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate database configuration.
        
        Args:
            config: Configuration dict with connection, schema, tables
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        connection = config.get("connection")
        schema = config.get("schema")
        tables = config.get("tables", [])
        
        if not connection:
            return False, "Please select a database connection"
        
        if not schema:
            return False, "Please select a schema"
        
        if not tables:
            return False, "Please select at least one table"
        
        return True, None


# Global router service instance (singleton pattern)
_router_service: Optional[RouterService] = None


def get_router_service() -> RouterService:
    """
    Get or create the global router service instance.
    
    Returns:
        RouterService: Global router service instance
    """
    global _router_service
    if _router_service is None:
        _router_service = RouterService()
        logger.info("Created global RouterService instance")
    return _router_service
