"""Strategy for ASK_REPORTING_TYPE stage."""

import logging
import json
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskReportingTypeStrategy(StageStrategy):
    """Handle reporting type selection."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_REPORTING_TYPE stage."""
        user_lower = user_input.lower().replace(" ", "")
        
        reporting_map = {
            "identical": "identical",
            "onlydifference": "onlyDifference",
            "onlyinthefirstdataset": "onlyInTheFirstDataset",
            "firstdataset": "onlyInTheFirstDataset",
            "onlyintheseconddataset": "onlyInTheSecondDataset",
            "seconddataset": "onlyInTheSecondDataset",
            "alldifference": "allDifference",
            "all": "allDifference",
        }
        
        for key, value in reporting_map.items():
            if key in user_lower:
                memory.gathered_params["reporting"] = value
                
                # Fetch schemas from current connection for dropdown
                try:
                    from src.ai.router.utils.connection_fetcher import ConnectionFetcher
                    result = await ConnectionFetcher.fetch_schemas(memory.connection, memory)
                    
                    if result["success"] and memory.available_schemas:
                        question_text = f"Reporting type set to '{value}'.\n\nWhich schema do you want to save the comparison results to?"
                        response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': 'schemas', 'question': question_text})}"
                        memory.last_question = question_text
                        return self._create_result(memory, response, Stage.GATHER_COMPARE_PARAMS)
                except Exception as e:
                    logger.warning(f"Could not fetch schemas for dropdown: {e}")
                
                # Fallback: ask without dropdown
                response = f"Reporting type set to '{value}'.\n\nWhich schema do you want to save the comparison results to?"
                return self._create_result(memory, response, Stage.GATHER_COMPARE_PARAMS)
        
        return self._create_result(
            memory,
            "Please choose a valid reporting type:\n- identical\n- onlyDifference\n- onlyInTheFirstDataset\n- onlyInTheSecondDataset\n- allDifference"
        )
