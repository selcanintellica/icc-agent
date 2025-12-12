"""Strategy for NEED_FIRST_NATURAL_LANGUAGE stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.sql_agent import call_sql_agent
from src.errors import ErrorHandler

logger = logging.getLogger(__name__)


class NeedFirstNaturalLanguageStrategy(StageStrategy):
    """Handle first natural language to SQL generation."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute NEED_FIRST_NATURAL_LANGUAGE stage."""
        if not user_input or not user_input.strip():
            return self._create_result(
                memory,
                "Please describe what data you want for the first query."
            )
        
        try:
            spec = call_sql_agent(
                user_input,
                connection=memory.connection,
                schema=memory.schema,
                selected_tables=memory.selected_tables
            )
            
            if not spec.sql:
                return self._create_result(
                    memory,
                    "I couldn't generate SQL from that description. Please try rephrasing it."
                )
            
            memory.first_sql = spec.sql
            
            warning = ""
            if spec.error:
                warning = f"\n\nNote: {spec.error}"
            
            return self._create_result(
                memory,
                f"I prepared this FIRST SQL:\n```sql\n{spec.sql}\n```{warning}\nIs this okay? (yes/no)",
                Stage.CONFIRM_FIRST_GENERATED_SQL
            )
        except Exception as e:
            logger.error(f"Error generating first SQL: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "generate_first_sql", "user_input": user_input[:100]})
            return self._create_result(
                memory,
                f"Error generating SQL: {icc_error.user_message}. Please try rephrasing or provide the SQL directly.",
                is_error=True
            )
