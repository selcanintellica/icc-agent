"""Strategy for NEED_USER_SQL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class NeedUserSqlStrategy(StageStrategy):
    """Handle user-provided SQL input."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process user's directly provided SQL query.
        
        Validates basic SQL syntax and stores the query.
        """
        logger.info("User provided SQL directly")
        
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            return self._create_result(
                memory,
                "How would you like to proceed?\n- 'create' - I'll generate SQL for you\n- 'provide' - You'll write the SQL",
                Stage.ASK_SQL_METHOD
            )
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(
                memory,
                "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        sql = user_input.strip()
        
        if not sql:
            return self._create_result(
                memory,
                "Please provide your SQL query:"
            )

        # Basic SQL validation
        sql_lower = sql.lower()
        valid_keywords = ["select", "insert", "update", "delete", "create", "drop", "alter", "with"]

        if not any(sql_lower.startswith(kw) or f" {kw} " in sql_lower for kw in valid_keywords):
            return self._create_result(
                memory,
                "That doesn't look like a valid SQL query. Please provide a SQL statement starting with SELECT, INSERT, UPDATE, DELETE, or other SQL keywords:"
            )
        
        memory.last_sql = sql
        
        warning = ""
        if "select" not in sql_lower:
            warning = "\n\nNote: This is a non-SELECT query which may modify data."

        response = f"You provided this SQL:\n```sql\n{memory.last_sql}\n```{warning}\n\nIs this correct? (yes/no)"
        logger.info(f"User SQL received: {memory.last_sql}")
        
        return self._create_result(memory, response, Stage.CONFIRM_USER_SQL)
