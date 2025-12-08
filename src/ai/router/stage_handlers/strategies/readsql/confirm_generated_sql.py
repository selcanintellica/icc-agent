"""Strategy for CONFIRM_GENERATED_SQL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class ConfirmGeneratedSqlStrategy(StageStrategy):
    """Handle confirmation of agent-generated SQL."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process user's confirmation of generated SQL.
        
        User can:
        - Confirm and proceed to execution
        - Reject and provide new description
        - Navigate back/reset
        """
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            return self._create_result(
                memory,
                "Describe what data you want in natural language.",
                Stage.NEED_NATURAL_LANGUAGE
            )
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(
                memory,
                "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["yes", "ok", "correct", "execute", "run"]):
            logger.info("User confirmed generated SQL")
            return self._create_result(
                memory,
                "Perfect! I'll set up and execute the job now. Ready to proceed? (Type 'yes' to continue)",
                Stage.EXECUTE_SQL
            )
        elif any(word in user_lower for word in ["no", "change", "modify", "different"]):
            logger.info("User wants to modify - going back to natural language input")
            return self._create_result(
                memory,
                "No problem! Please describe what you want differently:",
                Stage.NEED_NATURAL_LANGUAGE
            )
        else:
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to execute or 'no' to modify the query."
            )
