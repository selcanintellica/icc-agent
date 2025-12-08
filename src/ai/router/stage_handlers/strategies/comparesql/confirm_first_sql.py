"""Strategy for CONFIRM_FIRST_GENERATED_SQL and CONFIRM_FIRST_USER_SQL stages."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class ConfirmFirstSQLStrategy(StageStrategy):
    """Handle first SQL confirmation."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute CONFIRM_FIRST_GENERATED_SQL / CONFIRM_FIRST_USER_SQL stage."""
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            next_stage = Stage.NEED_FIRST_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_FIRST_GENERATED_SQL else Stage.NEED_FIRST_USER_SQL
            prompt = "Describe what data you want for the FIRST query." if next_stage == Stage.NEED_FIRST_NATURAL_LANGUAGE else "Please provide your FIRST SQL query:"
            return self._create_result(memory, prompt, next_stage)
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(memory, "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries", Stage.ASK_JOB_TYPE)
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["yes", "ok", "correct"]):
            return self._create_result(
                memory,
                "Great! Now for the SECOND query, how would you like to proceed?\n- 'create' - I'll generate SQL\n- 'provide' - You'll write the SQL",
                Stage.ASK_SECOND_SQL_METHOD
            )
        elif any(word in user_lower for word in ["no", "change", "modify"]):
            next_stage = Stage.NEED_FIRST_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_FIRST_GENERATED_SQL else Stage.NEED_FIRST_USER_SQL
            return self._create_result(
                memory,
                "No problem! Please provide/describe the first query again:",
                next_stage
            )
        else:
            return self._create_result(
                memory,
                "Please say 'yes' to proceed or 'no' to change the first query."
            )
