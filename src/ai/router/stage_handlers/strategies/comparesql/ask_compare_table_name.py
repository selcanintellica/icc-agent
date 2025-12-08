"""Strategy for ASK_COMPARE_TABLE_NAME stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskCompareTableNameStrategy(StageStrategy):
    """Handle comparison table name input."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_COMPARE_TABLE_NAME stage."""
        table_name = user_input.strip()
        
        if not table_name:
            return self._create_result(
                memory,
                "Please provide a table name to save the results:"
            )
        
        memory.gathered_params["table_name"] = table_name
        response = f"Table name set to '{table_name}'.\n\nFinally, what would you like to name this job? (This will help you find it easily in ICC)"
        return self._create_result(memory, response, Stage.ASK_COMPARE_JOB_NAME)
