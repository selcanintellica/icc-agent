"""
Dropdown Handler Service.

Generic handler for dropdown selections in the UI (schema, connection, folder).
Eliminates code duplication between nearly identical dropdown callbacks.
"""

from typing import Dict, List, Optional, Any, Callable
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class DropdownHandler:
    """
    Generic dropdown selection handler.

    Handles dropdown selections by:
    1. Parsing triggered button to extract selected value
    2. Adding user message to chat
    3. Optionally updating memory state
    4. Invoking router with selection flag
    5. Formatting response for display
    """

    def __init__(self, session_manager, invoke_router_async):
        """
        Initialize dropdown handler.

        Args:
            session_manager: Session manager for memory access
            invoke_router_async: Async function to invoke router
        """
        self.session_manager = session_manager
        self.invoke_router_async = invoke_router_async

    def parse_selection(
        self,
        triggered_id: str,
        n_clicks: List[Optional[int]],
        selected_values: List[Optional[str]],
        button_ids: List[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Parse dropdown selection from Dash callback inputs.

        Args:
            triggered_id: ID of triggered button from callback_context
            n_clicks: List of n_clicks for all buttons
            selected_values: List of selected dropdown values
            button_ids: List of button ID dictionaries

        Returns:
            Dict with 'param_name' and 'selected_value', or None if parsing failed
        """
        try:
            # Parse button ID to get param_name
            button_id_dict = json.loads(triggered_id.split(".")[0])
            param_name = button_id_dict.get("param")

            # Find corresponding value by checking n_clicks
            triggered_idx = None
            for i, bid in enumerate(button_ids):
                if bid.get("param") == param_name and n_clicks[i] is not None:
                    triggered_idx = i
                    break

            if triggered_idx is None:
                logger.debug(f"No triggered button found for {param_name}")
                return None

            if not selected_values[triggered_idx]:
                logger.warning(f"No value selected for {param_name}")
                return None

            selected_value = selected_values[triggered_idx]

            return {
                "param_name": param_name,
                "selected_value": selected_value
            }

        except Exception as e:
            logger.error(f"Error parsing selection: {e}")
            return None

    def create_user_message(self, selected_value: str) -> Dict[str, str]:
        """
        Create user message dict for chat.

        Args:
            selected_value: The value user selected

        Returns:
            Message dict with role, content, timestamp
        """
        return {
            "role": "user",
            "content": selected_value,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    def create_error_message(self, error_text: str) -> Dict[str, str]:
        """
        Create error message dict for chat.

        Args:
            error_text: Error message text

        Returns:
            Message dict with role, content, timestamp
        """
        return {
            "role": "error",
            "content": error_text,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    async def process_selection(
        self,
        selection_type: str,
        selected_value: str,
        param_name: str,
        session_id: str,
        config: Dict[str, Any],
        memory_update_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process dropdown selection and invoke router.

        Args:
            selection_type: Type of selection (e.g., 'SCHEMA', 'CONNECTION', 'FOLDER')
            selected_value: The selected value
            param_name: Parameter name for memory assignment
            session_id: Session ID
            config: Configuration dict with connection, schema, tables
            memory_update_fn: Optional function to update memory state (receives memory object)

        Returns:
            Router response dict
        """
        # Get or create memory
        memory = self.session_manager.get_or_create_session(session_id)

        if not memory:
            logger.warning(f"Session '{session_id}' could not be created during {selection_type} selection")
            raise ValueError("Session not initialized")

        # Assign parameter in memory (bypass LLM)
        memory.gathered_params[param_name] = selected_value
        logger.info(f"Directly assigned {param_name}={selected_value} (bypassed LLM)")

        # Apply custom memory update if provided
        if memory_update_fn:
            memory_update_fn(memory)

        # Invoke router with selection flag
        selection_flag = f"__{selection_type}_SELECTED__:{selected_value}"
        response = await self.invoke_router_async(
            selection_flag,
            session_id=session_id,
            connection=config.get("connection"),
            schema=config.get("schema"),
            selected_tables=config.get("tables", []),
            folder_id=config.get("folder_id")
        )

        return response

    def format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format router response into appropriate message format.

        Handles special response formats (SCHEMA_DROPDOWN, CONNECTION_DROPDOWN, FOLDER_DROPDOWN).

        Args:
            response: Router response dict

        Returns:
            Message dict ready for chat display
        """
        response_text = response.get("response", "Selection successful!")

        # Check for SCHEMA_DROPDOWN
        if response_text.startswith("SCHEMA_DROPDOWN:"):
            schema_data = json.loads(response_text.replace("SCHEMA_DROPDOWN:", ""))
            return {
                "role": "schema_dropdown",
                "content": schema_data.get("question", "Which schema should I use?"),
                "schemas": schema_data.get("schemas", []),
                "param_name": schema_data.get("param_name", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # Check for CONNECTION_DROPDOWN
        elif response_text.startswith("CONNECTION_DROPDOWN:"):
            connection_data = json.loads(response_text.replace("CONNECTION_DROPDOWN:", ""))
            return {
                "role": "connection_dropdown",
                "content": connection_data.get("question", "Which connection should I use?"),
                "connections": connection_data.get("connections", []),
                "param_name": connection_data.get("param_name", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # Check for FOLDER_DROPDOWN
        elif response_text.startswith("FOLDER_DROPDOWN:"):
            folder_data = json.loads(response_text.replace("FOLDER_DROPDOWN:", ""))
            return {
                "role": "folder_dropdown",
                "content": folder_data.get("question", "Select a folder:"),
                "folders": folder_data.get("folders", []),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # Default agent message
        else:
            return {
                "role": "agent",
                "content": response_text,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }


# Singleton instance
_dropdown_handler_instance: Optional[DropdownHandler] = None


def get_dropdown_handler() -> DropdownHandler:
    """
    Get singleton instance of DropdownHandler.

    Note: This requires session_manager and invoke_router_async to be set after import.
    Use init_dropdown_handler() to initialize with dependencies.

    Returns:
        DropdownHandler: Singleton instance
    """
    global _dropdown_handler_instance
    if _dropdown_handler_instance is None:
        raise RuntimeError(
            "DropdownHandler not initialized. Call init_dropdown_handler() first."
        )
    return _dropdown_handler_instance


def init_dropdown_handler(session_manager, invoke_router_async) -> DropdownHandler:
    """
    Initialize singleton instance of DropdownHandler with dependencies.

    Args:
        session_manager: Session manager instance
        invoke_router_async: Async function to invoke router

    Returns:
        DropdownHandler: Singleton instance
    """
    global _dropdown_handler_instance
    if _dropdown_handler_instance is None:
        _dropdown_handler_instance = DropdownHandler(session_manager, invoke_router_async)
    return _dropdown_handler_instance
