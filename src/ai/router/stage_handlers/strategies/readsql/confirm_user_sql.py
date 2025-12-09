"""Strategy for CONFIRM_USER_SQL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class ConfirmUserSqlStrategy(StageStrategy):
    """Handle confirmation of user-provided SQL."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process user's confirmation of their own SQL.
        
        User can:
        - Confirm and proceed to execution
        - Reject and provide corrected SQL
        - Navigate back/reset
        """
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            memory.last_sql = None
            return self._create_result(
                memory,
                "Please provide your SQL query:",
                Stage.NEED_USER_SQL
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
            logger.info("User confirmed their SQL")
            return self._create_result(
                memory,
                "Perfect! I'll set up and execute the job now. Ready to proceed? (Type 'yes' to continue)",
                Stage.EXECUTE_SQL
            )
        elif any(word in user_lower for word in ["no", "change", "modify", "different"]):
            logger.info("User wants to modify their SQL")
            return self._create_result(
                memory,
                "Please provide the corrected SQL query:",
                Stage.NEED_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to execute or 'no' to provide a different query."
            )
