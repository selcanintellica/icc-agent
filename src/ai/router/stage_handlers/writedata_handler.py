"""
WriteData flow handler with comprehensive error handling.

Handles all stages related to writing query results to database tables.
"""

import logging
import json
from typing import Dict, Any

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.router.utils.connection_fetcher import ConnectionFetcher
from src.ai.router.global_command_handler import GlobalCommandHandler
from src.ai.router.utils.edit_target_resolver import EditTargetResolver
from src.ai.toolkits.icc_toolkit import write_data_job
from src.models.natural_language import WriteDataLLMRequest, WriteDataVariables, ColumnSchema
from src.errors import (
    ICCBaseError,
    UnknownConnectionError,
    DuplicateJobNameError,
    JobCreationFailedError,
    NetworkTimeoutError,
    MissingDatasetError,
    ErrorHandler,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class WriteDataHandler(BaseStageHandler):
    """
    Handler for WriteData workflow with comprehensive error handling.
    
    Following Single Responsibility Principle - only handles write_data operations.
    """
    
    MANAGED_STAGES = {
        Stage.NEED_WRITE_OR_EMAIL,  # Handle when current_tool="write_data" (parameter gathering)
        Stage.CONFIRM_WRITE_DATA_JOB,
    }

    def __init__(self, job_agent=None):
        """Initialize WriteData handler."""
        self.job_agent = job_agent

    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the WriteData workflow."""
        logger.info("WriteDataHandler: Processing write_data request")

        try:

            # Handle confirmation stage separately
            if memory.stage == Stage.CONFIRM_WRITE_DATA_JOB:
                from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
                confirm_strategy = ConfirmJobStrategy(
                    job_type="write_data",
                    execution_callback=lambda m: self._execute_write_data_job(m, m.gathered_params)
                )
                return await confirm_strategy.execute(memory, user_input)

            # Check for global commands first (back, reset, edit, review)
            global_cmd = GlobalCommandHandler.check_global_command(memory, user_input)

            if global_cmd == "reset":
                result = GlobalCommandHandler.handle_reset(memory)
                return self._create_result(
                    memory,
                    result["message"],
                    result.get("transition_to")
                )

            elif global_cmd == "back":
                result = GlobalCommandHandler.handle_back(memory)

                # If we need to re-gather parameters (during parameter gathering)
                if result.get("re_gather"):
                    logger.info("Re-gathering parameters after back command")
                    # Continue below to re-run job agent with empty input
                    user_input = ""
                # If we transitioned to a new stage, re-run handler with empty input to trigger that stage's prompt
                elif result.get("transition_to"):
                    memory.stage = result["transition_to"]
                    logger.info(f"Re-running handler after back to stage: {memory.stage.value}")
                    return await self.handle(memory, "")  # Re-run with empty input
                else:
                    # No transition - just show the message
                    return self._create_result(memory, result["message"])

            elif global_cmd == "review":
                result = GlobalCommandHandler.handle_review(memory)
                return self._create_result(memory, result["message"])

            elif global_cmd == "edit":
                # If we're in confirmation stage, don't intercept - let ConfirmJobStrategy handle it
                if memory.stage != Stage.CONFIRM_WRITE_DATA_JOB:
                    edit_resolver = EditTargetResolver()
                    result = GlobalCommandHandler.handle_edit(memory, user_input, edit_resolver)

                    # If editing a parameter during parameter gathering (no stage transition)
                    if not result.get("transition_to") and memory.current_tool:
                        logger.info("Edited parameter during parameter gathering - continuing to re-gather")
                        # Clear last_question to trigger fresh parameter gathering
                        memory.last_question = None
                        # Continue below to re-run job agent with empty input
                        user_input = ""
                    else:
                        return self._create_result(
                            memory,
                            result["message"],
                            result.get("transition_to")
                        )

            # Clear params when starting fresh or switching from read_sql
            has_read_sql_only_params = (
                "execute_query" in memory.gathered_params and
                not any(k in memory.gathered_params for k in ["connection", "schemas", "table", "drop_or_truncate"])
            )

            # Also clear if we have old write_data params (from previous write) but no active job in progress
            has_old_write_params = any(k in memory.gathered_params for k in ["connection", "schemas", "table", "drop_or_truncate"])

            if has_read_sql_only_params or (has_old_write_params and memory.current_tool != "write_data"):
                logger.info("Clearing gathered_params for fresh write_data flow")
                memory.gathered_params = {}
                memory.last_question = None

            memory.current_tool = "write_data"
            logger.info("Processing write_data request...")

            # Validate prerequisites
            if not memory.last_job_id:
                return self._create_result(
                    memory,
                    "No data available to write. Please run a query first (ReadSQL or CompareSQL) to generate data.",
                    is_error=True,
                    error_code=ErrorCode.JOB_MISSING_DATASET.code
                )

            # Get action from job agent
            action = call_job_agent(memory, user_input, tool_name="write_data")

            # Handle different action types
            if action.get("action") == "FETCH_CONNECTIONS":
                return await self._fetch_connections(memory)

            if action.get("action") == "FETCH_SCHEMAS":
                return await self._fetch_schemas(memory, action.get("connection"))

            if action.get("action") == "ASK":
                memory.last_question = action["question"]
                return self._create_result(memory, action["question"])

            if action.get("action") == "TOOL" and action.get("tool_name") == "write_data":
                # Store params and transition to confirmation stage
                params = action.get("params", {})
                memory.gathered_params.update(params)
                memory.stage = Stage.CONFIRM_WRITE_DATA_JOB
                logger.info("All write_data params gathered, transitioning to confirmation")

                # Import and use confirmation strategy
                from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
                confirm_strategy = ConfirmJobStrategy(
                    job_type="write_data",
                    execution_callback=lambda m: self._execute_write_data_job(m, m.gathered_params)
                )
                return await confirm_strategy.execute(memory, "")
            
            return self._create_result(memory, "Please provide write_data parameters. What should I name this job?")

        except ICCBaseError as e:
            logger.error(f"ICC error in WriteData handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in WriteData handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": "write_data"},
                fallback_message="An error occurred while setting up the write operation. Please try again."
            )
    
    async def _fetch_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch all available connections and show dropdown."""
        try:
            # Only fetch from API if not already in memory
            if not memory.connections:
                result = await ConnectionFetcher.fetch_connections(memory)
                if not result["success"]:
                    return self._create_result(
                        memory,
                        f"Error: {result['message']}\nPlease try again."
                    )

            # Determine purpose
            params = memory.gathered_params
            if params.get("write_count") and not params.get("write_count_connection"):
                param_name = "write_count_connection"
                question_text = "Which connection should I use for the row count?"
            else:
                param_name = "connection"
                question_text = "Which connection should I use to write the data?"

            # Return special format for UI to show dropdown
            connections_list = list(memory.connections.keys())
            response = f"CONNECTION_DROPDOWN:{json.dumps({'connections': connections_list, 'param_name': param_name, 'question': question_text})}"
            memory.last_question = question_text
            return self._create_result(memory, response)

        except Exception as e:
            logger.error(f"Error fetching connections: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "fetch_connections_writedata"})
            return self._create_result(
                memory,
                f"Unable to fetch connections: {icc_error.user_message}. Please specify the connection name directly.",
                is_error=True
            )

        return self._create_result(
            memory,
            "Unable to fetch available connections. Please specify the connection name directly.",
            is_error=True
        )

    async def _fetch_schemas(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch schemas for the selected connection."""
        try:
            result = await ConnectionFetcher.fetch_schemas(connection_name, memory)

            if result["success"]:
                # Determine purpose
                params = memory.gathered_params
                if params.get("write_count") and not params.get("write_count_schema"):
                    purpose = "write_count"
                    param_name = "write_count_schema"
                    question_text = "Which schema should I write the row count to?"
                else:
                    purpose = "data"
                    param_name = "schemas"
                    question_text = "Which schema should I write the data to?"

                # Return special format for UI to show dropdown
                response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': param_name, 'question': question_text})}"
                memory.last_question = question_text
                return self._create_result(memory, response)
            else:
                return self._create_result(
                    memory,
                    f"Unable to fetch schemas for '{connection_name}': {result['message']}\n\nPlease specify the schema name directly.",
                    is_error=True
                )

        except Exception as e:
            logger.error(f"Error fetching schemas: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "fetch_schemas_writedata", "connection": connection_name})
            return self._create_result(
                memory,
                f"Unable to fetch schemas: {icc_error.user_message}. Please specify the schema name directly.",
                is_error=True
            )

    async def _execute_write_data_job(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """Execute write_data job with error handling."""
        logger.info("Executing write_data_job...")

        job_name = params.get("name", "WriteData_Job")
        
        try:
            # Validate prerequisites
            if not memory.last_job_id:
                raise MissingDatasetError(
                    message="No dataset available for write operation",
                    user_message="No data available to write. Please run a query first."
                )

            # Get connection ID
            connection_name = params.get("connection", memory.connection)
            connection_id = memory.get_connection_id(connection_name)
            
            if not connection_id:
                from src.utils.connections import get_connection_id
                connection_id = get_connection_id(connection_name)
                if not connection_id:
                    raise UnknownConnectionError(
                        connection_name=connection_name,
                        user_message=f"The connection '{connection_name}' was not found. Please select a valid connection."
                    )
            
            # Prepare parameters
            table_name = params.get("table", "output_table")
            drop_or_truncate = params.get("drop_or_truncate", "INSERT").upper()
            
            if drop_or_truncate not in ["DROP", "TRUNCATE", "INSERT"]:
                drop_or_truncate = "INSERT"
            
            columns = [ColumnSchema(columnName=col) for col in (memory.last_columns or [])]
            schemas = params.get("schemas", memory.schema)
            write_count = params.get("write_count", False)
            
            # Create WriteDataVariables
            write_data_vars = WriteDataVariables(
                data_set=memory.last_job_id,
                data_set_job_name=memory.last_job_name,
                data_set_folder=memory.last_job_folder,
                columns=columns,
                add_columns=[],
                connection=connection_id,
                schemas=schemas,
                table=table_name,
                drop_or_truncate=drop_or_truncate,
                write_count=write_count
            )
            
            # Handle write_count parameters if enabled
            if write_count:
                write_count_conn_name = params.get("write_count_connection", memory.connection)
                write_count_conn_id = memory.get_connection_id(write_count_conn_name)
                
                if not write_count_conn_id:
                    from src.utils.connections import get_connection_id as get_conn_id_static
                    write_count_conn_id = get_conn_id_static(write_count_conn_name)
                    if not write_count_conn_id:
                        return self._create_result(
                            memory,
                            f"The connection '{write_count_conn_name}' for row count tracking was not found. Please select a valid connection.",
                            is_error=True
                        )
                
                write_data_vars.write_count_connection = write_count_conn_id
                write_data_vars.write_count_schemas = params.get("write_count_schema")
                write_data_vars.write_count_table = params.get("write_count_table")
            
            # Create request and execute job
            request = WriteDataLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": job_name, "description": ""},
                variables=[write_data_vars],
                folder=memory.job_folder
            )
            
            result = await write_data_job(request)
            logger.info(f"write_data_job result: {json.dumps(result, indent=2, default=str)}")


            if result.get("message") == "Success":
                job_id = result.get("job_id")
                job_folder = memory.job_folder  # Use session-level folder from config
                # Track output table info for send_email query generation
                memory.output_table_info = {
                    "schema": schemas,
                    "table": table_name
                }
                logger.info(f"Set output_table_info: {memory.output_table_info}")

                # Track job for rule creation
                memory.add_created_job(
                    job_id=job_id,
                    job_name=job_name,
                    job_type="write_data",
                    job_folder=job_folder
                )
                logger.info(f"Added write_data job to created_jobs: {job_name} (ID: {job_id})")

                # Clean up memory
                memory.gathered_params = {}
                memory.current_tool = None
                memory.last_question = None

                # Check if we have multiple jobs for rule creation option
                created_jobs = memory.get_created_jobs()
                has_multiple_jobs = len(created_jobs) >= 2 if created_jobs else False

                if has_multiple_jobs:
                    response = (
                        f"Job '{job_name}' created successfully!\n\n"
                        f"Data will be written to table '{table_name}' in {schemas} schema.\n\n"
                        f"What would you like to do next?\n"
                        f"- 'email' - Send results via email\n"
                        f"- 'rule' - Create a rule from your jobs\n"
                        f"- 'done' - Finish"
                    )
                else:

                    response = (
                        f"Job '{job_name}' created successfully!\n\n"
                        f"Data will be written to table '{table_name}' in {schemas} schema.\n\n"
                        f"What would you like to do next?\n"
                        f"- 'email' - Send results via email\n"
                        f"- 'done' - Finish"
                    )
                return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)

            else:
                error_msg = result.get("error", "Unknown error")
                return self._create_result(
                    memory,
                    f"Error creating WriteData job: {error_msg}",
                    is_error=True
                )

        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name '{job_name}': {e}")
            # Clear only the name - keep all other params for retry
            memory.gathered_params["name"] = ""
            memory.last_question = None  # Trigger fresh prompt for name
            return self._create_result(
                memory,
                f"A job named '{job_name}' already exists. Please provide a different name:",
                is_error=True,
                error_code=e.code
            )

        except UnknownConnectionError as e:
            logger.error(f"Unknown connection: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )

        except MissingDatasetError as e:
            logger.error(f"Missing dataset: {e}")
            return self._create_result(
                memory,
                e.user_message,
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
            logger.error(f"ICC error in write_data: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )
        
        except Exception as e:
            logger.error(f"Error in write_data: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                self._format_job_error("WriteData", e, job_name),
                is_error=True
            )
