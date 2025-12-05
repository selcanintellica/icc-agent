"""
CompareSQL flow handler with comprehensive error handling.

Handles all stages related to the CompareSQL workflow following SOLID principles.
"""

import logging
import json
from typing import Dict, Any

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.sql_agent import call_sql_agent
from src.ai.toolkits.icc_toolkit import compare_sql_job
from src.models.natural_language import CompareSqlLLMRequest, CompareSqlVariables
from src.errors import (
    ICCBaseError,
    UnknownConnectionError,
    DuplicateJobNameError,
    JobCreationFailedError,
    NetworkTimeoutError,
    InvalidJSONError,
    ErrorHandler,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class CompareSQLHandler(BaseStageHandler):
    """
    Handler for CompareSQL workflow stages with comprehensive error handling.
    
    Following Single Responsibility Principle - only handles CompareSQL-related stages.
    """
    
    MANAGED_STAGES = {
        Stage.ASK_FIRST_SQL_METHOD,
        Stage.NEED_FIRST_NATURAL_LANGUAGE,
        Stage.NEED_FIRST_USER_SQL,
        Stage.CONFIRM_FIRST_GENERATED_SQL,
        Stage.CONFIRM_FIRST_USER_SQL,
        Stage.ASK_SECOND_SQL_METHOD,
        Stage.NEED_SECOND_NATURAL_LANGUAGE,
        Stage.NEED_SECOND_USER_SQL,
        Stage.CONFIRM_SECOND_GENERATED_SQL,
        Stage.CONFIRM_SECOND_USER_SQL,
        Stage.ASK_AUTO_MATCH,
        Stage.WAITING_MAP_TABLE,
        Stage.ASK_REPORTING_TYPE,
        Stage.ASK_COMPARE_SCHEMA,
        Stage.ASK_COMPARE_TABLE_NAME,
        Stage.ASK_COMPARE_JOB_NAME,
        Stage.EXECUTE_COMPARE_SQL,
    }
    
    def __init__(self, sql_agent=None, job_agent=None):
        """Initialize CompareSQL handler."""
        self.sql_agent = sql_agent
        self.job_agent = job_agent
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the CompareSQL stage."""
        logger.info(f"CompareSQLHandler: Processing stage {memory.stage.value}")
        
        try:
            if memory.stage == Stage.ASK_FIRST_SQL_METHOD:
                return await self._handle_ask_first_sql_method(memory, user_input)
            elif memory.stage == Stage.NEED_FIRST_NATURAL_LANGUAGE:
                return await self._handle_need_first_natural_language(memory, user_input)
            elif memory.stage == Stage.NEED_FIRST_USER_SQL:
                return await self._handle_need_first_user_sql(memory, user_input)
            elif memory.stage in [Stage.CONFIRM_FIRST_GENERATED_SQL, Stage.CONFIRM_FIRST_USER_SQL]:
                return await self._handle_confirm_first_sql(memory, user_input)
            elif memory.stage == Stage.ASK_SECOND_SQL_METHOD:
                return await self._handle_ask_second_sql_method(memory, user_input)
            elif memory.stage == Stage.NEED_SECOND_NATURAL_LANGUAGE:
                return await self._handle_need_second_natural_language(memory, user_input)
            elif memory.stage == Stage.NEED_SECOND_USER_SQL:
                return await self._handle_need_second_user_sql(memory, user_input)
            elif memory.stage in [Stage.CONFIRM_SECOND_GENERATED_SQL, Stage.CONFIRM_SECOND_USER_SQL]:
                return await self._handle_confirm_second_sql(memory, user_input)
            elif memory.stage == Stage.ASK_AUTO_MATCH:
                return await self._handle_ask_auto_match(memory, user_input)
            elif memory.stage == Stage.WAITING_MAP_TABLE:
                return await self._handle_waiting_map_table(memory, user_input)
            elif memory.stage == Stage.ASK_REPORTING_TYPE:
                return await self._handle_ask_reporting_type(memory, user_input)
            elif memory.stage == Stage.ASK_COMPARE_SCHEMA:
                return await self._handle_ask_compare_schema(memory, user_input)
            elif memory.stage == Stage.ASK_COMPARE_TABLE_NAME:
                return await self._handle_ask_compare_table_name(memory, user_input)
            elif memory.stage == Stage.ASK_COMPARE_JOB_NAME:
                return await self._handle_ask_compare_job_name(memory, user_input)
            elif memory.stage == Stage.EXECUTE_COMPARE_SQL:
                return await self._handle_execute_compare_sql(memory, user_input)
            
            return self._create_result(memory, "Unhandled stage in CompareSQL flow")
            
        except ICCBaseError as e:
            logger.error(f"ICC error in CompareSQL handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in CompareSQL handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while processing your request. Please try again."
            )
    
    async def _handle_ask_first_sql_method(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_FIRST_SQL_METHOD stage."""
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["create", "generate"]):
            return self._create_result(
                memory,
                "Describe what data you want for the FIRST query in natural language.",
                Stage.NEED_FIRST_NATURAL_LANGUAGE
            )
        elif any(word in user_lower for word in ["provide", "write", "own"]):
            return self._create_result(
                memory,
                "Please provide your FIRST SQL query:",
                Stage.NEED_FIRST_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose:\n- 'create' - I'll generate SQL for you\n- 'provide' - You'll write the SQL"
            )
    
    async def _handle_need_first_natural_language(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_FIRST_NATURAL_LANGUAGE stage."""
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
            return self._create_result(
                memory,
                "I had trouble generating SQL. Please try rephrasing or provide the SQL directly.",
                is_error=True
            )
    
    async def _handle_need_first_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_FIRST_USER_SQL stage."""
        sql = user_input.strip()
        
        if not sql:
            return self._create_result(
                memory,
                "Please provide your FIRST SQL query:"
            )
        
        memory.first_sql = sql
        return self._create_result(
            memory,
            f"You provided this FIRST SQL:\n```sql\n{memory.first_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_FIRST_USER_SQL
        )
    
    async def _handle_confirm_first_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_FIRST_GENERATED_SQL / CONFIRM_FIRST_USER_SQL stage."""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["yes", "ok", "correct"]):
            return self._create_result(
                memory,
                "Great! Now for the SECOND query, how would you like to proceed?\n- 'create' - I'll generate SQL\n- 'provide' - You'll write the SQL",
                Stage.ASK_SECOND_SQL_METHOD
            )
        elif any(word in user_lower for word in ["no", "change", "modify"]):
            next_stage = Stage.NEED_FIRST_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_FIRST_GENERATED_SQL else Stage.NEED_FIRST_USER_SQL
            return self._create_result(
                memory,
                "No problem! Please provide/describe the first query again:",
                next_stage
            )
        else:
            return self._create_result(
                memory,
                "Please say 'yes' to proceed or 'no' to change the first query."
            )
    
    async def _handle_ask_second_sql_method(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_SECOND_SQL_METHOD stage."""
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["create", "generate"]):
            return self._create_result(
                memory,
                "Describe what data you want for the SECOND query in natural language.",
                Stage.NEED_SECOND_NATURAL_LANGUAGE
            )
        elif any(word in user_lower for word in ["provide", "write", "own"]):
            return self._create_result(
                memory,
                "Please provide your SECOND SQL query:",
                Stage.NEED_SECOND_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose 'create' or 'provide' for the second query."
            )
    
    async def _handle_need_second_natural_language(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_SECOND_NATURAL_LANGUAGE stage."""
        if not user_input or not user_input.strip():
            return self._create_result(
                memory,
                "Please describe what data you want for the second query."
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
            
            memory.second_sql = spec.sql
            
            warning = ""
            if spec.error:
                warning = f"\n\nNote: {spec.error}"
            
            return self._create_result(
                memory,
                f"I prepared this SECOND SQL:\n```sql\n{spec.sql}\n```{warning}\nIs this okay? (yes/no)",
                Stage.CONFIRM_SECOND_GENERATED_SQL
            )
        except Exception as e:
            logger.error(f"Error generating second SQL: {e}", exc_info=True)
            return self._create_result(
                memory,
                "I had trouble generating SQL. Please try rephrasing or provide the SQL directly.",
                is_error=True
            )
    
    async def _handle_need_second_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_SECOND_USER_SQL stage."""
        sql = user_input.strip()
        
        if not sql:
            return self._create_result(
                memory,
                "Please provide your SECOND SQL query:"
            )
        
        memory.second_sql = sql
        return self._create_result(
            memory,
            f"You provided this SECOND SQL:\n```sql\n{memory.second_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_SECOND_USER_SQL
        )
    
    async def _handle_confirm_second_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_SECOND_GENERATED_SQL / CONFIRM_SECOND_USER_SQL stage."""
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
            connection_id = get_connection_id(memory.connection)
            
            if not connection_id:
                return self._create_result(
                    memory,
                    self._format_connection_error(memory.connection),
                    is_error=True,
                    error_code=ErrorCode.CONN_UNKNOWN_CONNECTION.code
                )
            
            from src.models.query import QueryPayload
            from src.repositories.query_repository import QueryRepository
            from httpx import AsyncClient
            from src.utils.auth import authenticate
            
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
    
    async def _handle_ask_auto_match(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_AUTO_MATCH stage."""
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
    
    async def _handle_waiting_map_table(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle WAITING_MAP_TABLE stage.
        
        UI sends:
        - key_mappings: [{"FirstKey": "COL1", "SecondKey": "COL2"}] - pairs where key checkboxes are checked
        - column_mappings: [{"FirstMappedColumn": "COL1", "SecondMappedColumn": "COL2"}] - all column pairs
        
        Maps to API fields (COMMA-SEPARATED STRINGS):
        - first_table_keys: comma-separated key column names from first table
        - second_table_keys: comma-separated key column names from second table
        - first_table_columns: comma-separated ALL column names from first table
        - second_table_columns: comma-separated ALL column names from second table
        """
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
    
    async def _handle_ask_reporting_type(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_REPORTING_TYPE stage."""
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
                response = f"Reporting type set to '{value}'.\n\nWhich schema do you want to save the comparison results to?"
                return self._create_result(memory, response, Stage.ASK_COMPARE_SCHEMA)
        
        return self._create_result(
            memory,
            "Please choose a valid reporting type:\n- identical\n- onlyDifference\n- onlyInTheFirstDataset\n- onlyInTheSecondDataset\n- allDifference"
        )
    
    async def _handle_ask_compare_schema(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_COMPARE_SCHEMA stage."""
        schema_name = user_input.strip()
        
        if not schema_name:
            return self._create_result(
                memory,
                "Please provide a schema name to save the results:"
            )
        
        memory.gathered_params["schemas"] = schema_name
        response = f"Schema set to '{schema_name}'.\n\nWhat table name do you want to use for the comparison results?"
        return self._create_result(memory, response, Stage.ASK_COMPARE_TABLE_NAME)
    
    async def _handle_ask_compare_table_name(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_COMPARE_TABLE_NAME stage."""
        table_name = user_input.strip()
        
        if not table_name:
            return self._create_result(
                memory,
                "Please provide a table name to save the results:"
            )
        
        memory.gathered_params["table_name"] = table_name
        response = f"Table name set to '{table_name}'.\n\nFinally, what would you like to name this job? (This will help you find it easily in ICC)"
        return self._create_result(memory, response, Stage.ASK_COMPARE_JOB_NAME)
    
    async def _handle_ask_compare_job_name(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_COMPARE_JOB_NAME stage."""
        job_name = user_input.strip()
        
        if not job_name:
            return self._create_result(
                memory,
                "Please provide a name for this job:"
            )
        
        memory.gathered_params["job_name"] = job_name
        return await self._execute_compare_job(memory, job_name)
    
    async def _handle_execute_compare_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle EXECUTE_COMPARE_SQL stage (backward compatibility)."""
        return self._create_result(
            memory,
            "What would you like to name this job?",
            Stage.ASK_COMPARE_JOB_NAME
        )
    
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
