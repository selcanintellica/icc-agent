"""Strategy for NEED_NATURAL_LANGUAGE stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.sql_agent import call_sql_agent

logger = logging.getLogger(__name__)


class NeedNaturalLanguageStrategy(StageStrategy):
    """Handle natural language to SQL generation."""
    
    def __init__(self, sql_agent=None):
        """
        Initialize strategy with optional SQL agent.
        
        Args:
            sql_agent: SQL agent for query generation (optional, uses default if None)
        """
        self.sql_agent = sql_agent
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Generate SQL from natural language description.
        
        Uses SQL agent to convert user's natural language description
        into a SQL query.
        """
        logger.info("Generating SQL from natural language...")
        
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            return self._create_result(
                memory,
                "How would you like to proceed?\n- 'create' - I'll generate SQL for you\n- 'provide' - You'll write the SQL",
                Stage.ASK_SQL_METHOD
            )
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(
                memory,
                "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries",
                Stage.ASK_JOB_TYPE
            )
        
        if not user_input or not user_input.strip():
            return self._create_result(
                memory,
                "Please describe what data you want to query. For example: 'get all customers from USA'"
            )

        try:
            # Get connection_id from memory for ICC API
            connection_id = memory.get_connection_id(memory.connection)
            
            spec = call_sql_agent(
                user_input,
                connection=memory.connection,
                schema=memory.schema,
                selected_tables=memory.selected_tables,
                connection_id=connection_id
            )

            # Check if SQL agent returned an error
            if spec.error:
                logger.warning(f"SQL generation had issues: {spec.error}")

            if not spec.sql:
                return self._create_result(
                    memory,
                    "I couldn't generate a SQL query from that description. Please try rephrasing it more specifically."
                )

            memory.last_sql = spec.sql

            warning = ""
            if "select" not in spec.sql.lower():
                warning = "\n\nNote: This is a non-SELECT query which may modify data."

            if spec.error:
                warning += f"\n\nNote: {spec.error}"

            response = f"I prepared this SQL:\n```sql\n{spec.sql}\n```{warning}\n\nIs this okay? (yes/no)\nSay 'no' to modify, or 'yes' to execute."
            logger.info(f"SQL generated: {spec.sql}")

            return self._create_result(memory, response, Stage.CONFIRM_GENERATED_SQL)

        except Exception as e:
            logger.error(f"Error generating SQL: {e}", exc_info=True)
            return self._create_result(
                memory,
                "I had trouble generating SQL from your description. Please try rephrasing it or provide the SQL directly.",
                is_error=True
            )
