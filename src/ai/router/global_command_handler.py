"""
Global Command Handler for cross-stage navigation and editing.

This module provides centralized handling of global commands (back, reset, edit, review)
that work across all stages and job types.
"""

import logging
from typing import Optional, Dict, Any
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class GlobalCommandHandler:
    """
    Handles global navigation commands across all stages.

    Supports:
    - back: Go to previous stage
    - reset: Clear all and start over
    - edit <param>: Edit any stored parameter
    - review/summary: Show all current parameters
    """

    @staticmethod
    def check_global_command(memory: Memory, user_input: str) -> Optional[str]:
        """
        Check if user input is a global command.

        Args:
            memory: Conversation memory
            user_input: User's input

        Returns:
            Command type if detected: 'back', 'reset', 'edit', 'review', or None
        """
        user_lower = user_input.lower().strip()

        # Reset commands
        if user_lower in ["reset", "start over", "cancel", "restart", "clear all"]:
            return "reset"

        # Back commands
        if user_lower in ["back", "go back", "previous", "undo"]:
            return "back"

        # Review commands
        if user_lower in ["review", "summary", "show params", "what do we have", "current state"]:
            return "review"

        # Edit commands
        if any(user_lower.startswith(prefix) for prefix in ["edit ", "change ", "correct ", "fix ", "update "]):
            return "edit"

        return None

    @staticmethod
    def handle_reset(memory: Memory) -> Dict[str, Any]:
        """
        Handle reset command - clear all data and start over.

        Args:
            memory: Conversation memory

        Returns:
            Dict with action and message
        """
        logger.info("User requested reset - clearing all data")

        # Collect what we're clearing for user feedback
        cleared_items = []

        if memory.connection:
            cleared_items.append(f"connection: {memory.connection}")
            memory.connection = None

        if memory.schema:
            cleared_items.append(f"schema: {memory.schema}")
            memory.schema = None

        if hasattr(memory, 'last_sql') and memory.last_sql:
            cleared_items.append("SQL query")
            memory.last_sql = None

        if hasattr(memory, 'first_sql') and memory.first_sql:
            cleared_items.append("first SQL query")
            memory.first_sql = None

        if hasattr(memory, 'second_sql') and memory.second_sql:
            cleared_items.append("second SQL query")
            memory.second_sql = None

        if memory.gathered_params:
            cleared_items.append(f"{len(memory.gathered_params)} parameters")
            memory.gathered_params.clear()

        # Clear stage history
        if hasattr(memory.stage_context, 'reset_history'):
            memory.stage_context.reset_history()

        message = "🔄 Reset complete. Starting fresh!\n\n"
        if cleared_items:
            message += f"Cleared: {', '.join(cleared_items)}\n\n"
        message += "What type of job would you like to create? (ReadSQL, WriteData, SendEmail, CompareSQL)"

        return {
            "action": "RESET",
            "message": message,
            "transition_to": Stage.START
        }

    @staticmethod
    def handle_back(memory: Memory) -> Dict[str, Any]:
        """
        Handle back command - go to previous stage.

        Args:
            memory: Conversation memory

        Returns:
            Dict with action and message
        """
        logger.info(f"User requested back from stage: {memory.stage.value}")

        # If we're in parameter gathering mode (current_tool is set), handle specially
        if memory.current_tool and memory.gathered_params:
            # Remove last gathered parameter and re-trigger parameter gathering
            last_param = list(memory.gathered_params.keys())[-1]
            old_value = memory.gathered_params.pop(last_param)
            logger.info(f"Removed last parameter during {memory.current_tool} gathering: {last_param}={old_value}")

            # Clear last_question to trigger fresh parameter gathering
            memory.last_question = None

            return {
                "action": "BACK_PARAM",
                "message": f"⬅️ Removed: {last_param} = '{old_value}'",
                "transition_to": None,  # Stay in current stage
                "re_gather": True  # Signal to re-run parameter gathering
            }

        # Use stage history if available
        if hasattr(memory.stage_context, 'go_back'):
            previous_stage = memory.stage_context.go_back()
            logger.info(f"Going back to stage: {previous_stage.value}")

            return {
                "action": "BACK",
                "message": f"⬅️ Going back to previous step...",
                "transition_to": previous_stage
            }
        else:
            # Fallback: remove last parameter if in parameter gathering
            if memory.gathered_params:
                last_param = list(memory.gathered_params.keys())[-1]
                old_value = memory.gathered_params.pop(last_param)
                logger.info(f"Removed last parameter: {last_param}={old_value}")

                return {
                    "action": "BACK",
                    "message": f"⬅️ Removed: {last_param} = '{old_value}'\n\nLet's continue from here.",
                    "transition_to": None  # Stay in current stage
                }
            else:
                return {
                    "action": "BACK",
                    "message": "No previous steps to go back to. Let's continue from here.",
                    "transition_to": None
                }

    @staticmethod
    def handle_review(memory: Memory) -> Dict[str, Any]:
        """
        Handle review command - show current state.

        Args:
            memory: Conversation memory

        Returns:
            Dict with action and message
        """
        logger.info("User requested review of current state")

        summary = "📋 **Current State Summary**\n\n"

        # Connection info
        if memory.connection:
            summary += f"**Connection:** {memory.connection}\n"
        if memory.schema:
            summary += f"**Schema:** {memory.schema}\n"

        # SQL queries
        if hasattr(memory, 'last_sql') and memory.last_sql:
            summary += f"\n**SQL Query:**\n```sql\n{memory.last_sql[:200]}{'...' if len(memory.last_sql) > 200 else ''}\n```\n"

        if hasattr(memory, 'first_sql') and memory.first_sql:
            summary += f"\n**First SQL:**\n```sql\n{memory.first_sql[:200]}{'...' if len(memory.first_sql) > 200 else ''}\n```\n"

        if hasattr(memory, 'second_sql') and memory.second_sql:
            summary += f"\n**Second SQL:**\n```sql\n{memory.second_sql[:200]}{'...' if len(memory.second_sql) > 200 else ''}\n```\n"

        # Gathered parameters
        if memory.gathered_params:
            summary += "\n**Parameters:**\n"
            for key, value in memory.gathered_params.items():
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                summary += f"- {key}: {value}\n"

        # Current stage
        summary += f"\n**Current Stage:** {memory.stage.value}\n"

        if not memory.connection and not memory.gathered_params and not hasattr(memory, 'last_sql'):
            summary = "📋 **Current State Summary**\n\nNo data gathered yet. We're at the beginning of the conversation."

        summary += "\n💡 You can type 'edit <parameter>' to modify something, or 'reset' to start over."

        return {
            "action": "REVIEW",
            "message": summary,
            "transition_to": None  # Stay in current stage
        }

    @staticmethod
    def handle_edit(memory: Memory, user_input: str, edit_resolver) -> Dict[str, Any]:
        """
        Handle edit command - edit a specific parameter.

        Args:
            memory: Conversation memory
            user_input: Full user input (e.g., "edit sql")
            edit_resolver: EditTargetResolver instance

        Returns:
            Dict with action, message, and transition info
        """
        logger.info(f"User requested edit: {user_input}")

        # Extract edit target
        edit_target = user_input.lower().strip()
        for prefix in ["edit ", "change ", "correct ", "fix ", "update "]:
            if edit_target.startswith(prefix):
                edit_target = edit_target[len(prefix):].strip()
                break

        # Use resolver to determine what to edit
        resolution = edit_resolver.resolve(edit_target, memory)

        if resolution:
            logger.info(f"Resolved edit target '{edit_target}' to: {resolution}")
            return {
                "action": "EDIT",
                "message": resolution.get("message"),
                "transition_to": resolution.get("transition_to"),
                "clear_params": resolution.get("clear_params", [])
            }
        else:
            # Couldn't resolve - ask user to clarify
            available = []
            if memory.connection:
                available.append("connection")
            if hasattr(memory, 'last_sql') and memory.last_sql:
                available.append("sql")
            if hasattr(memory, 'first_sql') and memory.first_sql:
                available.append("first sql")
            if hasattr(memory, 'second_sql') and memory.second_sql:
                available.append("second sql")
            if memory.gathered_params:
                available.extend(memory.gathered_params.keys())

            message = f"I couldn't identify what you want to edit from '{user_input}'.\n\n"
            if available:
                message += f"Available items to edit:\n"
                for item in available[:10]:  # Show first 10
                    message += f"- {item}\n"
                message += "\nPlease be more specific, like:\n"
                message += f"- edit {available[0]}\n"
                if len(available) > 1:
                    message += f"- change {available[1]}\n"
            else:
                message += "No parameters have been set yet."

            return {
                "action": "EDIT_CLARIFY",
                "message": message,
                "transition_to": None
            }
