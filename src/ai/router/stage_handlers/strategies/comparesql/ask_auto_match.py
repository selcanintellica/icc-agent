"""Strategy for ASK_AUTO_MATCH stage."""

import logging
import json
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskAutoMatchStrategy(StageStrategy):
    """Handle auto-match column question."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_AUTO_MATCH stage."""
        user_lower = user_input.lower()
        auto_match = any(word in user_lower for word in ["yes", "auto", "ok"])
        
        response_data = {
            "action": "show_map_table",
            "first_columns": memory.first_columns,
            "second_columns": memory.second_columns,
            "auto_matched": auto_match
        }
        
        if auto_match:
            auto_mappings = []
            for col in memory.first_columns:
                if col in memory.second_columns:
                    auto_mappings.append({"FirstMappedColumn": col, "SecondMappedColumn": col})
            response_data["pre_mappings"] = auto_mappings
        
        return self._create_result(
            memory,
            f"MAP_TABLE_POPUP:{json.dumps(response_data)}",
            Stage.WAITING_MAP_TABLE
        )
