"""Strategy for EXECUTE_SQL stage."""

import logging
import json
from typing import Dict, Any
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.toolkits.icc_toolkit import read_sql_job
from src.ai.router.utils.connection_fetcher import ConnectionFetcher
from src.models.natural_language import ReadSqlLLMRequest, ReadSqlVariables
from src.errors import (
    DuplicateJobNameError,
    UnknownConnectionError,
    NetworkTimeoutError,
    ICCBaseError,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


class ExecuteSqlStrategy(StageStrategy):
    """Handle SQL execution with job parameter gathering."""
    
    def __init__(self, job_agent=None):
        """
        Initialize strategy with optional job agent.
        
        Args:
            job_agent: Job agent for parameter gathering (optional)
        """
        self.job_agent = job_agent
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Gather parameters and execute the SQL job.
        
        Uses job agent to collect all required parameters,
        then creates and executes the ReadSQL job.
        """
        logger.info("Gathering parameters for read_sql...")

        try:
            # If no parameters gathered yet and user just confirmed, ignore and start fresh
            if not memory.gathered_params and user_input.lower().strip() in ["yes", "ok", "okay", "sure", "correct"]:
                logger.debug(f"Ignoring confirmation message '{user_input}' - starting fresh parameter gathering")
                user_input = ""

            action = call_job_agent(memory, user_input, tool_name="read_sql")

            if action.get("action") == "ASK":
                memory.last_question = action["question"]
                return self._create_result(memory, action["question"])

            if action.get("action") == "FETCH_CONNECTIONS":
                return await self._fetch_connections(memory)

            if action.get("action") == "FETCH_SCHEMAS":
                return await self._fetch_schemas_for_result(memory, action.get("connection"))

            if action.get("action") == "TOOL" and action.get("tool_name") == "read_sql":
                # Store params and invoke confirmation strategy immediately
                params = action.get("params", {})
                memory.gathered_params.update(params)
                memory.stage = Stage.CONFIRM_READ_SQL_JOB
                logger.info("All read_sql params gathered, showing confirmation")

                # Import and invoke confirmation strategy
                from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
                confirm_strategy = ConfirmJobStrategy(
                    job_type="read_sql",
                    execution_callback=lambda m: self._execute_read_sql_job(m, m.gathered_params)
                )
                return await confirm_strategy.execute(memory, "")

            return self._create_result(
                memory,
                "To execute, I need the database connection name. What connection should I use?"
            )
        except Exception as e:
            logger.error(f"Error in execute_sql stage: {e}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"context": "execute_sql_stage", "stage": memory.stage.value})
            return self._create_result(
                memory,
                f"Error: {icc_error.user_message}",
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
        logger.info("Showing confirmation summary for ReadSQL job")

        # Merge params into gathered_params
        memory.gathered_params.update(params)

        # Import and use confirmation strategy
        from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy

        # Create confirmation strategy with execution callback
        confirm_strategy = ConfirmJobStrategy(
            job_type="read_sql",
            execution_callback=lambda m: self._execute_read_sql_job(m, params)
        )

        # Transition to confirmation stage
        memory.stage = Stage.CONFIRM_READ_SQL_JOB

        # Show summary
        return await confirm_strategy.execute(memory, "")

    async def _execute_read_sql_job(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """Execute the read_sql job with error handling."""
        logger.info("Executing read_sql_job...")

        job_name = params.get("name", "ReadSQL_Job")
        
        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)

            if not connection_id:
                logger.error(f"Unknown connection: {memory.connection}")
                return self._create_result(
                    memory,
                    f"The connection '{memory.connection}' was not found. Please select a valid connection.",
                    is_error=True
                )
            
            logger.info(f"Using connection: {memory.connection} (ID: {connection_id})")
            
            execute_query = params.get("execute_query", False)
            write_count = params.get("write_count", False)
            
            read_sql_vars = ReadSqlVariables(
                query=memory.last_sql,
                connection=connection_id,
                execute_query=execute_query,
                write_count=write_count
            )
            
            if execute_query:
                read_sql_vars.result_schema = params.get("result_schema")
                read_sql_vars.table_name = params.get("table_name")
                read_sql_vars.drop_before_create = params.get("drop_before_create", False)
                read_sql_vars.only_dataset_columns = params.get("only_dataset_columns", False)
                logger.info(f"ReadSQL with execute_query=true: schema={read_sql_vars.result_schema}, table={read_sql_vars.table_name}")
            
            if write_count:
                write_count_conn_name = params.get("write_count_connection", memory.connection)
                write_count_conn_id = get_connection_id(write_count_conn_name)
                if not write_count_conn_id:
                    logger.error(f"Unknown write_count connection: {write_count_conn_name}")
                    return self._create_result(
                        memory,
                        f"The connection '{write_count_conn_name}' for row count tracking was not found. Please select a valid connection.",
                        is_error=True
                    )
                
                read_sql_vars.write_count_connection = write_count_conn_id
                read_sql_vars.write_count_schema = params.get("write_count_schema")
                read_sql_vars.write_count_table = params.get("write_count_table")
            
            request = ReadSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": job_name, "description": ""},
                variables=[read_sql_vars]
            )
            
            result = await read_sql_job(request)
            
            logger.info(f"read_sql_job result: {json.dumps(result, indent=2)}")
            
            if result.get("message") == "Success":
                job_id = result.get("job_id")
                job_folder = memory.job_folder  # Use session-level folder from config
                
                memory.last_job_id = job_id
                memory.last_job_name = job_name
                memory.last_job_folder = job_folder
                memory.last_columns = result.get("columns", [])
                memory.execute_query_enabled = execute_query
                
                # Track job for rule creation
                memory.add_created_job(
                    job_id=job_id,
                    job_name=job_name,
                    job_type="read_sql",
                    job_folder=job_folder
                )
                logger.info(f"Added read_sql job to created_jobs: {job_name} (ID: {job_id})")

                if execute_query:
                    memory.output_table_info = {
                        "schema": params.get("result_schema"),
                        "table": params.get("table_name")
                    }
                    logger.info(f"Set output_table_info: {memory.output_table_info}")
                
                cols_str = ", ".join(memory.last_columns[:5])
                if len(memory.last_columns) > 5:
                    cols_str += f"... ({len(memory.last_columns)} total)"
                
                if execute_query:
                    response = f"✅ Job '{job_name}' created successfully!\n\nQuery executed and data saved to {params.get('result_schema')}.{params.get('table_name')}!\nColumns: {cols_str}\nJob ID: {memory.last_job_id}\n\nReady to see options? (Type 'yes' or 'continue')"
                else:
                    response = f"✅ Job '{job_name}' created successfully!\n\nColumns: {cols_str}\nJob ID: {memory.last_job_id}\n\nReady to see what you can do next? (Type 'yes' or 'continue')"
                
                return self._create_result(memory, response, Stage.SHOW_RESULTS)
            else:
                error_msg = result.get("error", "Unknown error")
                return self._create_result(
                    memory,
                    f"❌ Error creating ReadSQL job: {error_msg}",
                    is_error=True
                )

        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name '{job_name}': {e}")
            memory.gathered_params["name"] = ""
            memory.last_question = None
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

        except NetworkTimeoutError as e:
            logger.error(f"Network timeout: {e}")
            return self._create_result(
                memory,
                e.user_message + "\n\nPlease try again.",
                is_error=True,
                error_code=e.code
            )

        except ICCBaseError as e:
            logger.error(f"ICC error in read_sql: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )

        except Exception as e:
            logger.error(f"Error in read_sql: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"❌ Error executing ReadSQL job: {str(e)}",
                is_error=True
            )
    
    async def _fetch_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch all available connections for write_count."""
        if not memory.connections:
            result = await ConnectionFetcher.fetch_connections(memory)
            if not result["success"]:
                return self._create_result(
                    memory,
                    f"❌ Error: {result['message']}\nPlease try again."
                )

        param_name = "write_count_connection"
        question_text = "Which connection should I use for the row count?"

        connections_list = list(memory.connections.keys())
        response = f"CONNECTION_DROPDOWN:{json.dumps({'connections': connections_list, 'param_name': param_name, 'question': question_text})}"
        memory.last_question = question_text
        return self._create_result(memory, response)

    async def _fetch_schemas_for_result(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch schemas for result connection."""
        try:
            result = await ConnectionFetcher.fetch_schemas(connection_name, memory)

            if result["success"]:
                params = memory.gathered_params
                if params.get("write_count") and not params.get("write_count_schema") and params.get("write_count_connection"):
                    purpose = "write_count"
                    param_name = "write_count_schema"
                else:
                    purpose = "result"
                    param_name = "result_schema"

                question_text = "Which schema should I write the results to?" if purpose == "result" else "Which schema should I write the row count to?"
                response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': param_name, 'question': question_text})}"
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
