"""Strategy for SHOW_RESULTS stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class ShowResultsStrategy(StageStrategy):
    """Handle showing results after SQL execution."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Show results and prompt for next action.
        
        User can choose to:
        - Write results to a table
        - Email results
        - Finish the workflow
        """
        memory.current_tool = None
        
        if memory.execute_query_enabled:
            response = "Data has been written to the table automatically!\n\nWhat would you like to do next?\n- 'email' - Send results via email\n- 'done' - Finish"
        else:
            response = "What would you like to do next?\n- 'write' - Save results to a table\n- 'done' - Finish"
        
        return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
