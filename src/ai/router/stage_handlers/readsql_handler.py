"""
ReadSQL flow handler.

Handles all stages related to the ReadSQL workflow following SOLID principles.
"""

import logging
import json
from typing import Dict, Any
from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.sql_agent import call_sql_agent
from src.ai.router.job_agent import call_job_agent
from src.ai.toolkits.icc_toolkit import read_sql_job
from src.ai.router.utils.connection_fetcher import ConnectionFetcher
from src.models.natural_language import (
    ReadSqlLLMRequest,
    ReadSqlVariables,
    ColumnSchema
)

logger = logging.getLogger(__name__)


class ReadSQLHandler(BaseStageHandler):
    """
    Handler for ReadSQL workflow stages.
    
    Following Single Responsibility Principle - only handles ReadSQL-related stages.
    """
    
    # Define which stages this handler manages
    MANAGED_STAGES = {
        Stage.ASK_SQL_METHOD,
        Stage.NEED_NATURAL_LANGUAGE,
        Stage.NEED_USER_SQL,
        Stage.CONFIRM_GENERATED_SQL,
        Stage.CONFIRM_USER_SQL,
        Stage.EXECUTE_SQL,
        Stage.SHOW_RESULTS,
        Stage.NEED_WRITE_OR_EMAIL,
    }
    
    def __init__(self, sql_agent=None, job_agent=None):
        """
        Initialize ReadSQL handler.
        
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
        """Process the ReadSQL stage."""
        logger.info(f"📘 ReadSQLHandler: Processing stage {memory.stage.value}")
        
        if memory.stage == Stage.ASK_SQL_METHOD:
            return await self._handle_ask_sql_method(memory, user_input)
        elif memory.stage == Stage.NEED_NATURAL_LANGUAGE:
            return await self._handle_need_natural_language(memory, user_input)
        elif memory.stage == Stage.NEED_USER_SQL:
            return await self._handle_need_user_sql(memory, user_input)
        elif memory.stage == Stage.CONFIRM_GENERATED_SQL:
            return await self._handle_confirm_generated_sql(memory, user_input)
        elif memory.stage == Stage.CONFIRM_USER_SQL:
            return await self._handle_confirm_user_sql(memory, user_input)
        elif memory.stage == Stage.EXECUTE_SQL:
            return await self._handle_execute_sql(memory, user_input)
        elif memory.stage == Stage.SHOW_RESULTS:
            return await self._handle_show_results(memory, user_input)
        elif memory.stage == Stage.NEED_WRITE_OR_EMAIL:
            return await self._handle_need_write_or_email(memory, user_input)
        
        return self._create_result(memory, "Unhandled stage in ReadSQL flow")
    
    async def _handle_ask_sql_method(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle ASK_SQL_METHOD stage."""
        user_lower = user_input.lower()
        
        if "create" in user_lower or "generate" in user_lower:
            logger.info("📝 User chose: Agent will generate SQL")
            return self._create_result(
                memory,
                "Great! Describe what data you want in natural language. (e.g., 'get all customers from USA')",
                Stage.NEED_NATURAL_LANGUAGE
            )
        elif "provide" in user_lower or "write" in user_lower or "my own" in user_lower:
            logger.info("✍️ User chose: Provide SQL directly")
            return self._create_result(
                memory,
                "Please provide your SQL query:",
                Stage.NEED_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please choose:\n• 'create' - I'll generate SQL for you\n• 'provide' - You'll write the SQL"
            )
    
    async def _handle_need_natural_language(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_NATURAL_LANGUAGE stage."""
        logger.info("📝 Generating SQL from natural language...")
        
        spec = call_sql_agent(
            user_input,
            connection=memory.connection,
            schema=memory.schema,
            selected_tables=memory.selected_tables
        )
        memory.last_sql = spec.sql
        
        warning = "" if "select" in spec.sql.lower() else "\n⚠️ Note: This is a non-SELECT query. "
        
        response = f"I prepared this SQL:\n```sql\n{spec.sql}\n```{warning}\nIs this okay? (yes/no)\nSay 'no' to modify, or 'yes' to execute."
        logger.info(f"✅ SQL generated: {spec.sql}")
        
        return self._create_result(memory, response, Stage.CONFIRM_GENERATED_SQL)
    
    async def _handle_need_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_USER_SQL stage."""
        logger.info("✍️ User provided SQL directly")
        
        memory.last_sql = user_input.strip()
        
        if not any(keyword in memory.last_sql.lower() for keyword in ["select", "insert", "update", "delete", "create", "drop"]):
            return self._create_result(
                memory,
                "⚠️ That doesn't look like a SQL query. Please provide a valid SQL statement:"
            )
        
        warning = "" if "select" in memory.last_sql.lower() else "\n⚠️ Note: This is a non-SELECT query. "
        
        response = f"You provided this SQL:\n```sql\n{memory.last_sql}\n```{warning}\nIs this correct? (yes/no)"
        logger.info(f"✅ User SQL received: {memory.last_sql}")
        
        return self._create_result(memory, response, Stage.CONFIRM_USER_SQL)
    
    async def _handle_confirm_generated_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_GENERATED_SQL stage."""
        user_lower = user_input.lower()
        
        if "yes" in user_lower or "ok" in user_lower or "correct" in user_lower or "execute" in user_lower:
            logger.info("✅ User confirmed generated SQL")
            return self._create_result(memory, "Great! Executing the query...", Stage.EXECUTE_SQL)
        elif "no" in user_lower or "change" in user_lower or "modify" in user_lower:
            logger.info("🔄 User wants to modify - going back to natural language input")
            return self._create_result(
                memory,
                "No problem! Please describe what you want differently:",
                Stage.NEED_NATURAL_LANGUAGE
            )
        else:
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to execute or 'no' to modify the query."
            )
    
    async def _handle_confirm_user_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle CONFIRM_USER_SQL stage."""
        user_lower = user_input.lower()
        
        if "yes" in user_lower or "ok" in user_lower or "correct" in user_lower or "execute" in user_lower:
            logger.info("✅ User confirmed their SQL")
            return self._create_result(memory, "Great! Executing the query...", Stage.EXECUTE_SQL)
        elif "no" in user_lower or "change" in user_lower or "modify" in user_lower:
            logger.info("🔄 User wants to modify their SQL")
            return self._create_result(
                memory,
                "Please provide the corrected SQL query:",
                Stage.NEED_USER_SQL
            )
        else:
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to execute or 'no' to provide a different query."
            )
    
    async def _handle_execute_sql(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle EXECUTE_SQL stage."""
        logger.info("🔧 Gathering parameters for read_sql...")
        
        # If no parameters gathered yet and user just confirmed (said "yes"/"okay"), 
        # ignore that confirmation message and start fresh
        if not memory.gathered_params and user_input.lower().strip() in ["yes", "ok", "okay", "sure", "correct"]:
            logger.info(f"🔄 Ignoring confirmation message '{user_input}' - starting fresh parameter gathering")
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
            return await self._execute_read_sql_job(memory, action.get("params", {}))
        
        return self._create_result(
            memory,
            "To execute, I need the database connection name. What connection should I use?"
        )
    
    async def _execute_read_sql_job(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """Execute the read_sql job."""
        logger.info("⚡ Executing read_sql_job...")
        
        try:
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                logger.error(f"❌ Unknown connection: {memory.connection}")
                return self._create_result(
                    memory,
                    f"❌ Error: Unknown connection '{memory.connection}'. Please select a valid connection."
                )
            
            logger.info(f"🔌 Using connection: {memory.connection} (ID: {connection_id})")
            
            execute_query = params.get("execute_query", False)
            write_count = params.get("write_count", False)
            
            read_sql_vars = ReadSqlVariables(
                query=memory.last_sql,
                connection=connection_id,
                execute_query=execute_query,
                write_count=write_count
            )
            
            if execute_query:
                # Results are saved to the SAME connection as the query
                # Only schema can be different
                read_sql_vars.result_schema = params.get("result_schema")
                read_sql_vars.table_name = params.get("table_name")
                read_sql_vars.drop_before_create = params.get("drop_before_create", False)
                read_sql_vars.only_dataset_columns = params.get("only_dataset_columns", False)
                logger.info(f"📝 ReadSQL with execute_query=true: connection={memory.connection}, schema={read_sql_vars.result_schema}, table={read_sql_vars.table_name}")
            
            if write_count:
                write_count_conn_name = params.get("write_count_connection", memory.connection)
                write_count_conn_id = get_connection_id(write_count_conn_name)
                if not write_count_conn_id:
                    logger.error(f"❌ Unknown write_count connection: {write_count_conn_name}")
                    return self._create_result(
                        memory,
                        f"❌ Error: Unknown connection '{write_count_conn_name}' for write_count."
                    )
                
                read_sql_vars.write_count_connection = write_count_conn_id
                read_sql_vars.write_count_schema = params.get("write_count_schema")
                read_sql_vars.write_count_table = params.get("write_count_table")
                logger.info(f"📊 ReadSQL with write_count=true: schema={read_sql_vars.write_count_schema}, table={read_sql_vars.write_count_table}")
            
            request = ReadSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": params.get("name", "ReadSQL_Job"), "description": ""},
                variables=[read_sql_vars]
            )
            
            result = await read_sql_job(request)
            
            logger.info(f"📊 read_sql_job result: {json.dumps(result, indent=2)}")
            
            if result.get("message") == "Success":
                memory.last_job_id = result.get("job_id")
                memory.last_job_name = params.get("name", "ReadSQL_Job")
                memory.last_job_folder = "3023602439587835"
                memory.last_columns = result.get("columns", [])
                memory.execute_query_enabled = execute_query
                
                # Track output table info for send_email query generation
                # When execute_query=true, data is written to result_schema.table_name
                if execute_query:
                    memory.output_table_info = {
                        "schema": params.get("result_schema"),
                        "table": params.get("table_name")
                    }
                    logger.info(f"📝 Set output_table_info from ReadSQL: {memory.output_table_info}")
                
                cols_str = ", ".join(memory.last_columns[:5])
                if len(memory.last_columns) > 5:
                    cols_str += f"... ({len(memory.last_columns)} total)"
                
                if execute_query:
                    response = f"✅ Query executed and data saved to {params.get('result_schema')}.{params.get('table_name')}!\n📊 Columns: {cols_str}\n🆔 Job ID: {memory.last_job_id}"
                else:
                    response = f"✅ Query executed successfully!\n📊 Columns: {cols_str}\n🆔 Job ID: {memory.last_job_id}"
                
                return self._create_result(memory, response, Stage.SHOW_RESULTS)
            else:
                error_msg = result.get("error", "Unknown error")
                return self._create_result(
                    memory,
                    f"❌ Error executing query: {error_msg}\nWould you like to try a different query?"
                )
        
        except Exception as e:
            logger.error(f"❌ Error in read_sql: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"❌ Error: {str(e)}\nPlease try again or rephrase your request."
            )
    
    async def _handle_show_results(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle SHOW_RESULTS stage."""
        memory.current_tool = None
        
        if memory.execute_query_enabled:
            response = "✅ Data has been written to the table automatically!\n\nWhat would you like to do next?\n• 'email' - Send results via email\n• 'done' - Finish"
        else:
            response = "What would you like to do next?\n• 'write' - Save results to a table\n• 'email' - Send results via email\n• 'both' - Write and email\n• 'done' - Finish"
        
        return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
    
    async def _handle_need_write_or_email(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle NEED_WRITE_OR_EMAIL stage."""
        user_lower = user_input.lower()
        
        if "done" in user_lower or "finish" in user_lower or "complete" in user_lower:
            return self._create_result(
                memory,
                "✅ All done! Say 'new query' to start again.",
                Stage.DONE
            )
        
        if memory.execute_query_enabled and ("write" in user_lower or "save" in user_lower):
            return self._create_result(
                memory,
                "⚠️ Data was already written to the table by the ReadSQL job (execute_query=true).\n\nWould you like to:\n• 'email' - Send results via email\n• 'done' - Finish"
            )
        
        wants_write = memory.current_tool == "write_data" or ("write" in user_lower or "save" in user_lower)
        wants_email = memory.current_tool == "send_email" or ("email" in user_lower or "send" in user_lower)
        
        if wants_write:
            # Set tool context and signal router to delegate to WriteDataHandler
            memory.current_tool = "write_data"
            logger.info("🔄 Delegating to WriteDataHandler...")
            # Return a special marker that router will recognize
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_WRITEDATA__",
                next_stage=memory.stage
            )
        elif wants_email:
            # Set tool context and signal router to delegate to SendEmailHandler
            memory.current_tool = "send_email"
            logger.info("🔄 Delegating to SendEmailHandler...")
            # Return a special marker that router will recognize
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_SENDEMAIL__",
                next_stage=memory.stage
            )
        
        return self._create_result(
            memory,
            "Please specify: 'write to <table>', 'email to <address>', or 'done'"
        )
    
    async def _fetch_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch all available connections for write_count."""
        # Only fetch from API if not already in memory
        if not memory.connections:
            result = await ConnectionFetcher.fetch_connections(memory)
            if not result["success"]:
                return self._create_result(
                    memory,
                    f"❌ Error: {result['message']}\nPlease try again."
                )
        
        # For read_sql, connections are only needed for write_count
        param_name = "write_count_connection"
        question_text = "Which connection should I use for the row count?"
        
        # Return special format for UI to show dropdown
        connections_list = list(memory.connections.keys())
        response = f"CONNECTION_DROPDOWN:{json.dumps({'connections': connections_list, 'param_name': param_name, 'question': question_text})}"
        memory.last_question = question_text
        return self._create_result(memory, response)
    
    async def _fetch_schemas_for_result(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch schemas for result connection (read_sql with execute_query or write_count)."""
        result = await ConnectionFetcher.fetch_schemas(connection_name, memory)
        
        if result["success"]:
            # Determine purpose based on what's missing in params
            params = memory.gathered_params
            if params.get("write_count") and not params.get("write_count_schema") and params.get("write_count_connection"):
                purpose = "write_count"
                param_name = "write_count_schema"
            else:
                purpose = "result"
                param_name = "result_schema"
            
            # Return special format for UI to show dropdown
            question_text = "Which schema should I write the results to?" if purpose == "result" else "Which schema should I write the row count to?"
            response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': param_name, 'question': question_text})}"
            memory.last_question = question_text
            return self._create_result(memory, response)
        else:
            return self._create_result(
                memory,
                f"❌ Error: {result['message']}\nPlease try again."
            )
