"""Strategy for ASK_FIRST_SQL_METHOD stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskFirstSQLMethodStrategy(StageStrategy):
    """Handle first SQL method selection."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_FIRST_SQL_METHOD stage."""
        user_lower = user_input.lower().strip()
        
        # Handle back/reset commands - go back to job type selection
        if user_lower in ["back", "go back", "reset", "start over", "cancel"]:
            logger.info(f"User requested '{user_lower}' - going back to job type selection")
            memory.current_tool = None
            memory.job_type = None
            return self._create_result(
                memory,
                "Okay! Let's start over.\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        if any(word in user_lower for word in ["create", "generate"]):
            return self._create_result(
                memory,
                "Describe what data you want for the FIRST query in natural language.",
                Stage.NEED_FIRST_NATURAL_LANGUAGE
            )
        elif any(word in user_lower for word in ["provide", "write", "own"]):
            return self._create_result(
                memory,
                "Please provide your FIRST SQL query:",
                Stage.NEED_FIRST_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose:\n- 'create' - I'll generate SQL for you\n- 'provide' - You'll write the SQL"
            )
