"""Strategy for NEED_FIRST_USER_SQL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class NeedFirstUserSQLStrategy(StageStrategy):
    """Handle first user-provided SQL."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute NEED_FIRST_USER_SQL stage."""
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            return self._create_result(memory, "For the FIRST query, how would you like to proceed?\n- 'create' - I'll generate SQL\n- 'provide' - You provide the SQL", Stage.ASK_FIRST_SQL_METHOD)
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(memory, "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries", Stage.ASK_JOB_TYPE)
        
        sql = user_input.strip()
        
        if not sql:
            return self._create_result(
                memory,
                "Please provide your FIRST SQL query:"
            )
        
        memory.first_sql = sql
        return self._create_result(
            memory,
            f"You provided this FIRST SQL:\n```sql\n{memory.first_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_FIRST_USER_SQL
        )
