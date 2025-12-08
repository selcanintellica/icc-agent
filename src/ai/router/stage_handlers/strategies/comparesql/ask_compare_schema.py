"""Strategy for ASK_COMPARE_SCHEMA stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskCompareSchemaStrategy(StageStrategy):
    """Handle comparison schema selection."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_COMPARE_SCHEMA stage."""
        # Check if this is a direct schema selection from dropdown (bypass LLM)
        if user_input.startswith("__SCHEMA_SELECTED__:"):
            schema_name = user_input.replace("__SCHEMA_SELECTED__:", "").strip()
            logger.info(f"✅ Schema directly selected via dropdown: {schema_name}")
        else:
            schema_name = user_input.strip()
        
        if not schema_name:
            return self._create_result(
                memory,
                "Please provide a schema name to save the results:"
            )
        
        memory.gathered_params["schemas"] = schema_name
        response = f"Schema set to '{schema_name}'.\n\nWhat table name do you want to use for the comparison results?"
        return self._create_result(memory, response, Stage.ASK_COMPARE_TABLE_NAME)
