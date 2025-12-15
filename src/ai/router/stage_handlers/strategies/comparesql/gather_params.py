"""Strategy for GATHER_COMPARE_PARAMS stage - consolidates parameter gathering."""

import logging
import json
from typing import Dict, Any
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.router.utils.connection_fetcher import ConnectionFetcher
from src.models.natural_language import CompareSqlLLMRequest, CompareSqlVariables
from src.ai.toolkits.icc_toolkit import compare_sql_job
from src.errors import (
    ICCBaseError,
    DuplicateJobNameError,
    NetworkTimeoutError,
    ErrorCode,
    ErrorHandler
)

logger = logging.getLogger(__name__)


class GatherCompareParamsStrategy(StageStrategy):
    """
    Gather parameters for CompareSQL job using job agent.

    Consolidates the old ASK_COMPARE_SCHEMA, ASK_COMPARE_TABLE_NAME,
    and ASK_COMPARE_JOB_NAME stages into one intelligent stage.
    """

    def __init__(self, job_agent=None):
        """
        Initialize strategy with optional job agent.

        Args:
            job_agent: Job agent for parameter gathering (optional)
        """
        super().__init__()
        self.job_agent = job_agent

    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Gather parameters and execute the CompareSQL job.

        Uses job agent to collect all required parameters (schemas, table_name, job_name),
        then creates and executes the CompareSQL job.
        """
        logger.info("Gathering parameters for compare_sql...")

        try:
            # Handle schema dropdown selection
            if user_input.startswith("__SCHEMA_SELECTED__:"):
                schema_name = user_input.replace("__SCHEMA_SELECTED__:", "").strip()
                memory.gathered_params["schemas"] = schema_name
                user_input = schema_name
                logger.info(f"Schema selected from dropdown: {schema_name}")

            # If no parameters gathered yet and user just confirmed, ignore and start fresh
            if not memory.gathered_params and user_input.lower().strip() in ["yes", "ok", "okay", "sure", "correct"]:
                logger.debug(f"Ignoring confirmation message '{user_input}' - starting fresh parameter gathering")
                user_input = ""

            action = call_job_agent(memory, user_input, tool_name="compare_sql")

            if action.get("action") == "ASK":
                memory.last_question = action["question"]
                return self._create_result(memory, action["question"])

            if action.get("action") == "FETCH_SCHEMAS":
                return await self._fetch_schemas(memory, action.get("connection"))

            if action.get("action") == "TOOL" and action.get("tool_name") == "compare_sql":
                # NEW: Go to confirmation instead of executing directly
                return await self._show_confirmation(memory, action.get("params", {}))

            return self._create_result(
                memory,
                "To execute the comparison, I need the schema name. What schema should I use?"
            )
        except Exception as e:
            logger.error(f"Error in gather_compare_params stage: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "gather_compare_params_stage", "stage": memory.stage.value})
            return self._create_result(
                memory,
                f"Error: {icc_error.user_message}",
                is_error=True
            )

    async def _fetch_schemas(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch schemas for result storage."""
        try:
            result = await ConnectionFetcher.fetch_schemas(connection_name, memory)

            if result["success"]:
                question_text = "Which schema should I save the comparison results to?"
                response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': 'schemas', 'question': question_text})}"
                memory.last_question = question_text
                return self._create_result(memory, response)
            else:
                return self._create_result(
                    memory,
                    f"Unable to fetch schemas: {result['message']}\n\nPlease try again or specify the schema name directly.",
                    is_error=True
                )
        except Exception as e:
            logger.error(f"Error fetching schemas: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "fetch_schemas", "connection": memory.connection})
            return self._create_result(
                memory,
                f"Unable to fetch schemas: {icc_error.user_message}\n\nPlease try again or specify the schema name directly.",
                is_error=True
            )

    async def _show_confirmation(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """
        Show confirmation summary before executing job.

        Args:
            memory: Conversation memory
            params: Job parameters

        Returns:
            StageHandlerResult with confirmation summary
        """
        logger.info("Showing confirmation summary for CompareSQL job")

        # Merge params into gathered_params
        memory.gathered_params.update(params)

        # Import and use confirmation strategy
        from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy

        # Create confirmation strategy with execution callback
        confirm_strategy = ConfirmJobStrategy(
            job_type="compare_sql",
            execution_callback=lambda m: self._execute_compare_job(m, params)
        )

        # Transition to confirmation stage
        memory.stage = Stage.CONFIRM_COMPARE_SQL_JOB

        # Show summary
        return await confirm_strategy.execute(memory, "")

    async def _execute_compare_job(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """
        Execute the compare_sql job with error handling.

        Uses the API field structure:
        - first_sql_query, second_sql_query: SQL queries
        - first_table_keys, second_table_keys: Comma-separated key columns
        - first_table_columns, second_table_columns: Comma-separated mapped columns
        - case_sensitive, calculate_difference, drop_before_create: Booleans
        - reporting: String (identical, onlyDifference, etc.)
        - schemas, table_name: Result storage location
        """
        job_name = params.get("job_name", "CompareSQL_Job")
        logger.info(f"Executing compare_sql_job with name '{job_name}'...")

        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)

            if not connection_id:
                logger.error(f"Unknown connection: {memory.connection}")
                return self._create_result(
                    memory,
                    f"The connection '{memory.connection}' was not found. Please select a valid connection.",
                    is_error=True,
                    error_code=ErrorCode.CONN_UNKNOWN_CONNECTION.code
                )

            logger.info(f"Using connection: {memory.connection} (ID: {connection_id})")

            # Merge gathered params with params from job agent
            all_params = {**memory.gathered_params, **params}

            request = CompareSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": job_name, "description": ""},
                variables=[CompareSqlVariables(
                    connection=connection_id,
                    first_sql_query=memory.first_sql,
                    second_sql_query=memory.second_sql,
                    first_table_keys=all_params.get("first_table_keys", ""),
                    second_table_keys=all_params.get("second_table_keys", ""),
                    first_table_columns=all_params.get("first_table_columns", ""),
                    second_table_columns=all_params.get("second_table_columns", ""),
                    case_sensitive=all_params.get("case_sensitive", False),
                    calculate_difference=all_params.get("calculate_difference", False),
                    reporting=all_params.get("reporting", "identical"),
                    schemas=all_params.get("schemas", "cache"),
                    table_name=all_params.get("table_name", "cache"),
                    drop_before_create=all_params.get("drop_before_create", True),
                )]
            )

            result = await compare_sql_job(request)

            logger.info(f"compare_sql_job result: {json.dumps(result, indent=2)}")

            if result.get("message") == "Success":
                memory.last_job_id = result.get("job_id")
                memory.last_job_name = job_name
                memory.last_job_folder = memory.job_folder  # Use session-level folder from config

                memory.output_table_info = {
                    "schema": all_params.get("schemas", "cache"),
                    "table": all_params.get("table_name", "cache")
                }
                logger.info(f"Set output_table_info: {memory.output_table_info}")

                # Clear gathered params for next job
                memory.gathered_params = {}

                response = (
                    f"✅ Compare Job '{job_name}' created successfully!\n"
                    f"Job ID: {memory.last_job_id}\n"
                    f"Results saved to: {all_params.get('schemas')}.{all_params.get('table_name')}\n\n"
                    f"What would you like to do next?\n- 'email' - Send results via email\n- 'done' - Finish"
                )
                return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
            else:
                error_msg = result.get("error", "Unknown error")
                return self._create_result(
                    memory,
                    f"❌ Error creating CompareSQL job: {error_msg}",
                    is_error=True
                )

        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name '{job_name}': {e}")
            # Clear only the name - keep all other params for retry
            memory.gathered_params["job_name"] = ""
            memory.last_question = None
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
                f"❌ Error executing CompareSQL job: {str(e)}",
                is_error=True
            )
