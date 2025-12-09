"""Strategy for ASK_SECOND_SQL_METHOD stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskSecondSQLMethodStrategy(StageStrategy):
    """Handle second SQL method selection."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_SECOND_SQL_METHOD stage."""
        user_lower = user_input.lower().strip()
        
        # Handle back/reset commands - go back to first SQL method
        if user_lower in ["back", "go back"]:
            logger.info("User requested 'back' - going back to first SQL method selection")
            # Clear second query data
            memory.second_sql = None
            return self._create_result(
                memory,
                "Okay, let's go back to the first query.\n\nFor the FIRST query, how would you like to proceed?\n- 'create' - I'll generate SQL from your description\n- 'provide' - You provide the SQL query directly",
                Stage.ASK_FIRST_SQL_METHOD
            )
        
        if user_lower in ["reset", "start over", "cancel"]:
            logger.info(f"User requested '{user_lower}' - going back to job type selection")
            memory.current_tool = None
            memory.job_type = None
            memory.first_sql = None
            memory.second_sql = None
            return self._create_result(
                memory,
                "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        if any(word in user_lower for word in ["create", "generate"]):
            return self._create_result(
                memory,
                "Describe what data you want for the SECOND query in natural language.",
                Stage.NEED_SECOND_NATURAL_LANGUAGE
            )
        elif any(word in user_lower for word in ["provide", "write", "own"]):
            return self._create_result(
                memory,
                "Please provide your SECOND SQL query:",
                Stage.NEED_SECOND_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose 'create' or 'provide' for the second query."
            )
