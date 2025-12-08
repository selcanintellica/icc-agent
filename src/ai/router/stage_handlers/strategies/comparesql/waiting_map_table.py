"""Strategy for WAITING_MAP_TABLE stage."""

import logging
import json
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.errors import ErrorCode

logger = logging.getLogger(__name__)


class WaitingMapTableStrategy(StageStrategy):
    """Handle map table column mapping.
    
    UI sends:
    - key_mappings: [{"FirstKey": "COL1", "SecondKey": "COL2"}] - pairs where key checkboxes are checked
    - column_mappings: [{"FirstMappedColumn": "COL1", "SecondMappedColumn": "COL2"}] - all column pairs
    
    Maps to API fields (COMMA-SEPARATED STRINGS):
    - first_table_keys: comma-separated key column names from first table
    - second_table_keys: comma-separated key column names from second table
    - first_table_columns: comma-separated ALL column names from first table
    - second_table_columns: comma-separated ALL column names from second table
    """
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute WAITING_MAP_TABLE stage."""
        try:
            mapping_data = json.loads(user_input)
            
            memory.key_mappings = mapping_data.get("key_mappings", [])
            memory.column_mappings = mapping_data.get("column_mappings", [])
            
            # Extract key columns as comma-separated strings
            first_keys = [km.get("FirstKey", "") for km in memory.key_mappings if km.get("FirstKey")]
            second_keys = [km.get("SecondKey", "") for km in memory.key_mappings if km.get("SecondKey")]
            
            # Extract ALL mapped columns as comma-separated strings
            first_columns = [cm.get("FirstMappedColumn", "") for cm in memory.column_mappings if cm.get("FirstMappedColumn")]
            second_columns = [cm.get("SecondMappedColumn", "") for cm in memory.column_mappings if cm.get("SecondMappedColumn")]
            
            # Store as comma-separated strings for API payload
            memory.gathered_params["first_table_keys"] = ",".join(first_keys)
            memory.gathered_params["second_table_keys"] = ",".join(second_keys)
            memory.gathered_params["first_table_columns"] = ",".join(first_columns)
            memory.gathered_params["second_table_columns"] = ",".join(second_columns)
            
            logger.info(f"Key mappings: {memory.key_mappings}")
            logger.info(f"Column mappings: {memory.column_mappings}")
            logger.info(f"first_table_keys: {memory.gathered_params['first_table_keys']}")
            logger.info(f"second_table_keys: {memory.gathered_params['second_table_keys']}")
            logger.info(f"first_table_columns: {memory.gathered_params['first_table_columns']}")
            logger.info(f"second_table_columns: {memory.gathered_params['second_table_columns']}")
            
            key_display = []
            for km in memory.key_mappings:
                key_display.append(f"{km.get('FirstKey', '?')} -> {km.get('SecondKey', '?')}")
            
            # Warn if no key mappings are provided
            key_warning = ""
            if not memory.key_mappings:
                key_warning = "\n\nNote: No key columns selected. Key columns are required for matching rows between tables."
            
            response = (
                f"Mappings received!\n\n"
                f"Keys: {', '.join(key_display) if key_display else '(none)'}\n"
                f"Mapped columns: {len(memory.column_mappings)} pairs{key_warning}\n\n"
                f"What type of reporting do you want?\n"
                f"- 'identical' - Show only identical records\n"
                f"- 'onlyDifference' - Show only different values\n"
                f"- 'onlyInTheFirstDataset' - Show records only in first dataset\n"
                f"- 'onlyInTheSecondDataset' - Show records only in second dataset\n"
                f"- 'allDifference' - Show all differences"
            )
            return self._create_result(memory, response, Stage.ASK_REPORTING_TYPE)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mapping data: {e}")
            return self._create_result(
                memory,
                "Invalid mapping data received. Please use the Map Table popup to configure mappings.",
                is_error=True,
                error_code=ErrorCode.VAL_INVALID_JSON.code
            )
