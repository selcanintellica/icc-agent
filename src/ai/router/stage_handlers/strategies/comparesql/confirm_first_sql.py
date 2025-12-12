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
        user_lower = user_input.lower().strip()

        # If empty input (from "back" command), show the full confirmation
        if not user_lower:
            if memory.first_sql:
                return self._create_result(
                    memory,
                    f"You provided this FIRST SQL:\n```sql\n{memory.first_sql}\n```\nIs this correct? (yes/no)"
                )
            else:
                return self._create_result(
                    memory,
                    "Please say 'yes' to proceed or 'no' to change the first query."
                )

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
