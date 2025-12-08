"""Strategy for CONFIRM_SECOND_GENERATED_SQL and CONFIRM_SECOND_USER_SQL stages."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.models.query import QueryPayload
from src.repositories.query_repository import QueryRepository
from httpx import AsyncClient
from src.utils.auth import authenticate
from src.errors import NetworkTimeoutError

logger = logging.getLogger(__name__)


class ConfirmSecondSQLStrategy(StageStrategy):
    """Handle second SQL confirmation and column fetching."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute CONFIRM_SECOND_GENERATED_SQL / CONFIRM_SECOND_USER_SQL stage."""
        # Check for navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            next_stage = Stage.NEED_SECOND_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_SECOND_GENERATED_SQL else Stage.NEED_SECOND_USER_SQL
            prompt = "Describe what data you want for the SECOND query." if next_stage == Stage.NEED_SECOND_NATURAL_LANGUAGE else "Please provide your SECOND SQL query:"
            return self._create_result(memory, prompt, next_stage)
        elif nav_cmd == "reset":
            memory.current_tool = None
            return self._create_result(memory, "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries", Stage.ASK_JOB_TYPE)
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["yes", "ok", "correct"]):
            return await self._fetch_columns_for_both_queries(memory)
        elif any(word in user_lower for word in ["no", "change", "modify"]):
            next_stage = Stage.NEED_SECOND_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_SECOND_GENERATED_SQL else Stage.NEED_SECOND_USER_SQL
            return self._create_result(
                memory,
                "No problem! Please provide/describe the second query again:",
                next_stage
            )
        else:
            return self._create_result(
                memory,
                "Please say 'yes' to execute or 'no' to change the second query."
            )
    
    async def _fetch_columns_for_both_queries(self, memory: Memory) -> StageHandlerResult:
        """Fetch columns for both SQL queries."""
        logger.info("Fetching columns for both queries...")
        
        try:
            from src.utils.connections import get_connection_id
            from src.errors import ErrorCode
            
            connection_id = get_connection_id(memory.connection)
            
            if not connection_id:
                return self._create_result(
                    memory,
                    self._format_connection_error(memory.connection),
                    is_error=True,
                    error_code=ErrorCode.CONN_UNKNOWN_CONNECTION.code
                )
            
            auth_result = await authenticate()
            if auth_result:
                userpass, token = auth_result
                headers = {"Authorization": f"Basic {userpass}", "TokenKey": token}
            else:
                headers = {}
                logger.warning("No authentication available for column fetch")
            
            async with AsyncClient(headers=headers, verify=False, timeout=30.0) as client:
                repo = QueryRepository(client)
                
                query_payload1 = QueryPayload(connectionId=connection_id, sql=memory.first_sql, folderId="")
                col_resp1 = await QueryRepository.get_column_names(repo, query_payload1)
                memory.first_columns = col_resp1.data.object.columns if col_resp1.success else []
                
                if not col_resp1.success:
                    logger.warning(f"Failed to fetch columns for first query: {col_resp1.error}")
                
                query_payload2 = QueryPayload(connectionId=connection_id, sql=memory.second_sql, folderId="")
                col_resp2 = await QueryRepository.get_column_names(repo, query_payload2)
                memory.second_columns = col_resp2.data.object.columns if col_resp2.success else []
                
                if not col_resp2.success:
                    logger.warning(f"Failed to fetch columns for second query: {col_resp2.error}")
            
            logger.info(f"First columns: {memory.first_columns}")
            logger.info(f"Second columns: {memory.second_columns}")
            
            if not memory.first_columns and not memory.second_columns:
                return self._create_result(
                    memory,
                    "Unable to fetch columns from either query. Please check your SQL queries are valid.",
                    is_error=True
                )
            
            first_cols_str = ', '.join(memory.first_columns[:10])
            if len(memory.first_columns) > 10:
                first_cols_str += f"... ({len(memory.first_columns)} total)"
            
            second_cols_str = ', '.join(memory.second_columns[:10])
            if len(memory.second_columns) > 10:
                second_cols_str += f"... ({len(memory.second_columns)} total)"
            
            response = f"Both queries confirmed!\n\nFirst query columns: {first_cols_str}\nSecond query columns: {second_cols_str}\n\nWould you like to auto-match columns with the same name? (yes/no)"
            return self._create_result(memory, response, Stage.ASK_AUTO_MATCH)
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout fetching columns: {e}")
            return self._create_result(
                memory,
                e.user_message + "\n\nPlease try again.",
                is_error=True,
                error_code=e.code
            )
        except Exception as e:
            logger.error(f"Error fetching columns: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"Unable to fetch column information: {str(e)}\n\nPlease check your SQL queries and try again.",
                is_error=True
            )
