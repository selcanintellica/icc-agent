"""Strategy for ASK_COMPARE_JOB_NAME and EXECUTE_COMPARE_SQL stages."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.models.natural_language import CompareSqlLLMRequest, CompareSqlVariables
from src.ai.toolkits.icc_toolkit import compare_sql_job
from src.errors import (
    ICCBaseError,
    DuplicateJobNameError,
    NetworkTimeoutError,
    ErrorCode
)

logger = logging.getLogger(__name__)


class AskCompareJobNameStrategy(StageStrategy):
    """Handle job name input and execution."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_COMPARE_JOB_NAME stage."""
        job_name = user_input.strip()
        
        if not job_name:
            return self._create_result(
                memory,
                "Please provide a name for this job:"
            )
        
        memory.gathered_params["job_name"] = job_name
        return await self._execute_compare_job(memory, job_name)
    
    async def _execute_compare_job(self, memory: Memory, job_name: str) -> StageHandlerResult:
        """Execute the compare_sql job with error handling.
        
        Uses the new API field structure:
        - map_table: JSON array of column mappings
        - keys: JSON array of key pairs
        - first_table_keys/second_table_keys: usually empty (keys in 'keys' field)
        - save_result_in_cache: new boolean field (default False)
        """
        logger.info(f"Executing compare_sql_job with name '{job_name}'...")
        
        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            
            if not connection_id:
                return self._create_result(
                    memory,
                    self._format_connection_error(memory.connection),
                    is_error=True,
                    error_code=ErrorCode.CONN_UNKNOWN_CONNECTION.code
                )
            
            params = memory.gathered_params
            
            request = CompareSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": job_name, "description": ""},
                variables=[CompareSqlVariables(
                    connection=connection_id,
                    first_sql_query=memory.first_sql,
                    second_sql_query=memory.second_sql,
                    first_table_keys=params.get("first_table_keys", ""),
                    second_table_keys=params.get("second_table_keys", ""),
                    first_table_columns=params.get("first_table_columns", ""),
                    second_table_columns=params.get("second_table_columns", ""),
                    case_sensitive=params.get("case_sensitive", False),
                    calculate_difference=params.get("calculate_difference", False),
                    reporting=params.get("reporting", "identical"),
                    schemas=params.get("schemas", "cache"),
                    table_name=params.get("table_name", "cache"),
                    drop_before_create=params.get("drop_before_create", True),
                )]
            )
            
            result = await compare_sql_job(request)
            
            if result.get("message") == "Success":
                memory.last_job_id = result.get("job_id")
                
                memory.output_table_info = {
                    "schema": params.get("schemas", "cache"),
                    "table": params.get("table_name", "cache")
                }
                logger.info(f"Set output_table_info: {memory.output_table_info}")
                
                memory.gathered_params = {}
                
                response = (
                    f"Compare Job '{job_name}' created successfully!\n"
                    f"Job ID: {memory.last_job_id}\n\n"
                    f"What would you like to do next?\n- 'email' - Send results via email\n- 'done' - Finish"
                )
                return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
            else:
                error = result.get('error', 'Unknown error')
                return self._create_result(
                    memory,
                    self._format_job_error("CompareSQL", Exception(error), job_name),
                    is_error=True
                )
        
        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name '{job_name}': {e}")
            # Clear only the name - keep all other params for retry
            memory.gathered_params["job_name"] = ""
            memory.last_question = None  # Trigger fresh prompt for name
            return self._create_result(
                memory,
                f"A job named '{job_name}' already exists. Please provide a different name:",
                is_error=True,
                error_code=e.code
            )
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout: {e}")
            return self._create_result(
                memory,
                e.user_message + "\n\nPlease try again.",
                is_error=True,
                error_code=e.code
            )
        
        except ICCBaseError as e:
            logger.error(f"ICC error in compare_sql: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )
        
        except Exception as e:
            logger.error(f"Error in compare_sql: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                self._format_job_error("CompareSQL", e, job_name),
                is_error=True
            )


class ExecuteCompareSQLStrategy(AskCompareJobNameStrategy):
    """Handle EXECUTE_COMPARE_SQL stage (backward compatibility).
    
    This stage exists for backward compatibility but now redirects to ASK_COMPARE_JOB_NAME.
    """
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute EXECUTE_COMPARE_SQL stage."""
        return self._create_result(
            memory,
            "What would you like to name this job?",
            Stage.ASK_COMPARE_JOB_NAME
        )
