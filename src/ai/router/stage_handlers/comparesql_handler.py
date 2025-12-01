"""
CompareSQL flow handler.

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

logger = logging.getLogger(__name__)


class CompareSQLHandler(BaseStageHandler):
    """
    Handler for CompareSQL workflow stages.
    
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
        """
        Initialize CompareSQL handler.
        
        Args:
            sql_agent: SQL agent for query generation (optional)
            job_agent: Job agent for parameter gathering (optional)
        """
        self.sql_agent = sql_agent
        self.job_agent = job_agent
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the CompareSQL stage."""
        logger.info(f"📗 CompareSQLHandler: Processing stage {memory.stage.value}")
        
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
    
    async def _handle_ask_first_sql_method(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_FIRST_SQL_METHOD stage."""
        user_lower = user_input.lower()
        if "create" in user_lower or "generate" in user_lower:
            return self._create_result(
                memory,
                "Describe what data you want for the FIRST query in natural language.",
                Stage.NEED_FIRST_NATURAL_LANGUAGE
            )
        elif "provide" in user_lower or "write" in user_lower:
            return self._create_result(
                memory,
                "Please provide your FIRST SQL query:",
                Stage.NEED_FIRST_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose 'create' or 'provide' for the first query."
            )
    
    async def _handle_need_first_natural_language(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_FIRST_NATURAL_LANGUAGE stage."""
        spec = call_sql_agent(
            user_input,
            connection=memory.connection,
            schema=memory.schema,
            selected_tables=memory.selected_tables
        )
        memory.first_sql = spec.sql
        return self._create_result(
            memory,
            f"I prepared this FIRST SQL:\n```sql\n{spec.sql}\n```\nIs this okay? (yes/no)",
            Stage.CONFIRM_FIRST_GENERATED_SQL
        )
    
    async def _handle_need_first_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_FIRST_USER_SQL stage."""
        memory.first_sql = user_input.strip()
        return self._create_result(
            memory,
            f"You provided this FIRST SQL:\n```sql\n{memory.first_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_FIRST_USER_SQL
        )
    
    async def _handle_confirm_first_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_FIRST_GENERATED_SQL / CONFIRM_FIRST_USER_SQL stage."""
        user_lower = user_input.lower()
        if "yes" in user_lower or "ok" in user_lower:
            return self._create_result(
                memory,
                "Great! Now for the SECOND query, how would you like to proceed?\n• 'create'\n• 'provide'",
                Stage.ASK_SECOND_SQL_METHOD
            )
        elif "no" in user_lower:
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
        if "create" in user_lower or "generate" in user_lower:
            return self._create_result(
                memory,
                "Describe what data you want for the SECOND query in natural language.",
                Stage.NEED_SECOND_NATURAL_LANGUAGE
            )
        elif "provide" in user_lower or "write" in user_lower:
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
        spec = call_sql_agent(
            user_input,
            connection=memory.connection,
            schema=memory.schema,
            selected_tables=memory.selected_tables
        )
        memory.second_sql = spec.sql
        return self._create_result(
            memory,
            f"I prepared this SECOND SQL:\n```sql\n{spec.sql}\n```\nIs this okay? (yes/no)",
            Stage.CONFIRM_SECOND_GENERATED_SQL
        )
    
    async def _handle_need_second_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_SECOND_USER_SQL stage."""
        memory.second_sql = user_input.strip()
        return self._create_result(
            memory,
            f"You provided this SECOND SQL:\n```sql\n{memory.second_sql}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_SECOND_USER_SQL
        )
    
    async def _handle_confirm_second_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_SECOND_GENERATED_SQL / CONFIRM_SECOND_USER_SQL stage."""
        user_lower = user_input.lower()
        if "yes" in user_lower or "ok" in user_lower:
            return await self._fetch_columns_for_both_queries(memory)
        elif "no" in user_lower:
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
        logger.info("📊 Fetching columns for both queries...")
        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                return self._create_result(
                    memory,
                    f"❌ Error: Unknown connection '{memory.connection}'."
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
            
            async with AsyncClient(headers=headers, verify=False) as client:
                repo = QueryRepository(client)
                
                query_payload1 = QueryPayload(connectionId=connection_id, sql=memory.first_sql, folderId="")
                col_resp1 = await QueryRepository.get_column_names(repo, query_payload1)
                memory.first_columns = col_resp1.data.object.columns if col_resp1.success else []
                
                query_payload2 = QueryPayload(connectionId=connection_id, sql=memory.second_sql, folderId="")
                col_resp2 = await QueryRepository.get_column_names(repo, query_payload2)
                memory.second_columns = col_resp2.data.object.columns if col_resp2.success else []
            
            logger.info(f"📊 First columns: {memory.first_columns}")
            logger.info(f"📊 Second columns: {memory.second_columns}")
            
            response = f"Both queries confirmed!\n\nFirst query columns: {', '.join(memory.first_columns)}\nSecond query columns: {', '.join(memory.second_columns)}\n\nWould you like to auto-match columns with the same name? (yes/no)"
            return self._create_result(memory, response, Stage.ASK_AUTO_MATCH)
        
        except Exception as e:
            logger.error(f"❌ Error fetching columns: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"❌ Error fetching columns: {str(e)}"
            )
    
    async def _handle_ask_auto_match(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_AUTO_MATCH stage."""
        user_lower = user_input.lower()
        auto_match = "yes" in user_lower or "auto" in user_lower
        
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
        """Handle WAITING_MAP_TABLE stage."""
        try:
            mapping_data = json.loads(user_input)
            
            memory.key_mappings = mapping_data.get("key_mappings", [])
            memory.column_mappings = mapping_data.get("column_mappings", [])
            
            first_keys = [m["FirstKey"] for m in memory.key_mappings]
            second_keys = [m["SecondKey"] for m in memory.key_mappings]
            memory.gathered_params["first_table_keys"] = ",".join(first_keys)
            memory.gathered_params["second_table_keys"] = ",".join(second_keys)
            
            logger.info(f"📊 Key mappings: {memory.key_mappings}")
            logger.info(f"📊 Column mappings: {memory.column_mappings}")
            
            response = f"Mappings received!\n\nKeys: {first_keys}\nMapped columns: {len(memory.column_mappings)} pairs\n\nNow, what type of reporting do you want?\n• 'identical' - Show only identical records\n• 'onlyDifference' - Show only different values\n• 'onlyInTheFirstDataset' - Show records only in first dataset\n• 'onlyInTheSecondDataset' - Show records only in second dataset\n• 'allDifference' - Show all differences"
            return self._create_result(memory, response, Stage.ASK_REPORTING_TYPE)
        except json.JSONDecodeError:
            return self._create_result(
                memory,
                "Invalid mapping data received. Please use the Map Table popup to configure mappings."
            )
    
    async def _handle_ask_reporting_type(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_REPORTING_TYPE stage."""
        user_lower = user_input.lower()
        
        if "identical" in user_lower:
            memory.gathered_params["reporting"] = "identical"
        elif "onlydifference" in user_lower or "only difference" in user_lower:
            memory.gathered_params["reporting"] = "onlyDifference"
        elif "onlyinthefirstdataset" in user_lower or "only in the first" in user_lower or "first dataset" in user_lower:
            memory.gathered_params["reporting"] = "onlyInTheFirstDataset"
        elif "onlyintheseconddataset" in user_lower or "only in the second" in user_lower or "second dataset" in user_lower:
            memory.gathered_params["reporting"] = "onlyInTheSecondDataset"
        elif "alldifference" in user_lower or "all difference" in user_lower:
            memory.gathered_params["reporting"] = "allDifference"
        else:
            return self._create_result(
                memory,
                "Please choose a valid reporting type: 'identical', 'onlyDifference', 'onlyInTheFirstDataset', 'onlyInTheSecondDataset', or 'allDifference'"
            )
        
        response = f"Reporting type set to '{memory.gathered_params['reporting']}'.\n\nWhich schema do you want to save the comparison results to?"
        return self._create_result(memory, response, Stage.ASK_COMPARE_SCHEMA)
    
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
            "What would you like to name this job? (This will help you find it easily in ICC)",
            Stage.ASK_COMPARE_JOB_NAME
        )
    
    async def _execute_compare_job(self, memory: Memory, job_name: str) -> StageHandlerResult:
        """Execute the compare_sql job."""
        logger.info(f"⚡ Executing compare_sql_job with name '{job_name}'...")
        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                return self._create_result(
                    memory,
                    f"❌ Error: Unknown connection '{memory.connection}'."
                )
            
            params = memory.gathered_params
            first_keys = params.get("first_table_keys", "")
            second_keys = params.get("second_table_keys", "")
            
            request = CompareSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": job_name, "description": ""},
                variables=[CompareSqlVariables(
                    connection=connection_id,
                    first_sql_query=memory.first_sql,
                    second_sql_query=memory.second_sql,
                    first_table_keys=first_keys,
                    second_table_keys=second_keys,
                    first_table_columns=",".join(memory.first_columns) if memory.first_columns else "",
                    second_table_columns=",".join(memory.second_columns) if memory.second_columns else "",
                    case_sensitive=params.get("case_sensitive", False),
                    reporting=params.get("reporting", "identical"),
                    schemas=params.get("schemas", "cache"),
                    table_name=params.get("table_name", "cache"),
                    drop_before_create=params.get("drop_before_create", True),
                    calculate_difference=params.get("calculate_difference", False)
                )]
            )
            
            result = await compare_sql_job(request)
            
            if result.get("message") == "Success":
                memory.last_job_id = result.get("job_id")
                memory.gathered_params = {}
                response = f"✅ Compare Job '{job_name}' created successfully!\n🆔 Job ID: {memory.last_job_id}\n\nWhat next? (email / done)"
                return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
            else:
                error = result.get('error', 'Unknown error')
                if "same name" in str(error).lower():
                    return self._create_result(
                        memory,
                        f"❌ A job named '{job_name}' already exists in this folder.\nPlease provide a different name:"
                    )
                return self._create_result(
                    memory,
                    f"❌ Error: {error}"
                )
        
        except Exception as e:
            logger.error(f"❌ Error in compare_sql: {str(e)}", exc_info=True)
            if "same name" in str(e).lower():
                return self._create_result(
                    memory,
                    f"❌ A job named '{job_name}' already exists in this folder.\nPlease provide a different name:"
                )
            return self._create_result(
                memory,
                f"❌ Error: {str(e)}"
            )
