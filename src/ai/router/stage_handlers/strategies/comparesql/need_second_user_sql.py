"""Strategy for NEED_SECOND_USER_SQL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class NeedSecondUserSQLStrategy(StageStrategy):
    """Handle second user-provided SQL."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute NEED_SECOND_USER_SQL stage."""
        sql = user_input.strip()
        
        if not sql:
            return self._create_result(
                memory,
                "Please provide your SECOND SQL query:"
            )
        
        memory.second_sql = sql
        return self._create_result(
            memory,
            f"You provided this SECOND SQL:\n```sql\n{memory.second_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_SECOND_USER_SQL
        )
