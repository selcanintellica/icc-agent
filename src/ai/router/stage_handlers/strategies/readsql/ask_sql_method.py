"""Strategy for ASK_SQL_METHOD stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskSqlMethodStrategy(StageStrategy):
    """Handle the ASK_SQL_METHOD stage where user chooses SQL input method."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process user's choice of SQL input method.
        
        User can choose to:
        - Generate SQL from natural language
        - Provide SQL query directly
        - Navigate back/reset
        """
        user_lower = user_input.lower().strip()
        
        # Handle back/reset commands - go back to job type selection
        if user_lower in ["back", "go back", "reset", "start over", "cancel"]:
            logger.info(f"User requested '{user_lower}' - going back to job type selection")
            memory.current_tool = None
            return self._create_result(
                memory,
                "Okay! Let's start over.\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        if "create" in user_lower or "generate" in user_lower:
            logger.info("User chose: Agent will generate SQL")
            return self._create_result(
                memory,
                "Great! Describe what data you want in natural language. (e.g., 'get all customers from USA')",
                Stage.NEED_NATURAL_LANGUAGE
            )
        elif "provide" in user_lower or "write" in user_lower or "my own" in user_lower:
            logger.info("User chose: Provide SQL directly")
            return self._create_result(
                memory,
                "Please provide your SQL query:",
                Stage.NEED_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose:\n- 'create' - I'll generate SQL for you\n- 'provide' - You'll write the SQL"
            )
