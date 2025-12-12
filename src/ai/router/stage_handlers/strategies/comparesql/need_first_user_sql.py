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
