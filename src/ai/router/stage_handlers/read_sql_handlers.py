"""
ReadSQL flow stage handlers.
Each handler is responsible for one stage (SRP).
"""
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from src.ai.router.sql_agent import call_sql_agent
from src.ai.router.job_agent import call_job_agent
from .base_handler import StageHandler
from src.models.natural_language import ReadSqlLLMRequest, ReadSqlVariables
import logging
import json

logger = logging.getLogger(__name__)


class AskSqlMethodHandler(StageHandler):
    """Handler for ASK_SQL_METHOD stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        user_lower = user_utterance.lower()
        
        if "create" in user_lower or "generate" in user_lower:
            logger.info("📝 User chose: Agent will generate SQL")
            memory.stage = Stage.NEED_NATURAL_LANGUAGE
            return memory, "Great! Describe what data you want in natural language. (e.g., 'get all customers from USA')"
        
        elif "provide" in user_lower or "write" in user_lower or "my own" in user_lower:
            logger.info("✍️ User chose: Provide SQL directly")
            memory.stage = Stage.NEED_USER_SQL
            return memory, "Please provide your SQL query:"
        
        else:
            return memory, "Please choose:\n• 'create' - I'll generate SQL for you\n• 'provide' - You'll write the SQL"


class NeedNaturalLanguageHandler(StageHandler):
    """Handler for NEED_NATURAL_LANGUAGE stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        logger.info("📝 Generating SQL from natural language...")
        
        spec = call_sql_agent(
            user_utterance, 
            connection=memory.connection,
            schema=memory.schema,
            selected_tables=memory.selected_tables
        )
        memory.last_sql = spec.sql
        
        warning = "\n⚠️ Note: This is a non-SELECT query. " if "select" not in spec.sql.lower() else ""
        memory.stage = Stage.CONFIRM_GENERATED_SQL
        
        response = f"I prepared this SQL:\n```sql\n{spec.sql}\n```{warning}\nIs this okay? (yes/no)\nSay 'no' to modify, or 'yes' to execute."
        logger.info(f"✅ SQL generated: {spec.sql}")
        
        return memory, response


class NeedUserSqlHandler(StageHandler):
    """Handler for NEED_USER_SQL stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        logger.info("✍️ User provided SQL directly")
        
        memory.last_sql = user_utterance.strip()
        
        if not any(keyword in memory.last_sql.lower() for keyword in ["select", "insert", "update", "delete", "create", "drop"]):
            return memory, "⚠️ That doesn't look like a SQL query. Please provide a valid SQL statement:"
        
        warning = "\n⚠️ Note: This is a non-SELECT query. " if "select" not in memory.last_sql.lower() else ""
        memory.stage = Stage.CONFIRM_USER_SQL
        
        response = f"You provided this SQL:\n```sql\n{memory.last_sql}\n```{warning}\nIs this correct? (yes/no)"
        logger.info(f"✅ User SQL received: {memory.last_sql}")
        
        return memory, response


class ConfirmGeneratedSqlHandler(StageHandler):
    """Handler for CONFIRM_GENERATED_SQL stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        user_lower = user_utterance.lower()
        
        if "yes" in user_lower or "ok" in user_lower or "correct" in user_lower or "execute" in user_lower:
            logger.info("✅ User confirmed generated SQL")
            memory.stage = Stage.EXECUTE_SQL
            return memory, "Great! Executing the query..."
        
        elif "no" in user_lower or "change" in user_lower or "modify" in user_lower:
            logger.info("🔄 User wants to modify - going back to natural language input")
            memory.stage = Stage.NEED_NATURAL_LANGUAGE
            return memory, "No problem! Please describe what you want differently:"
        
        else:
            return memory, "Please confirm: Say 'yes' to execute or 'no' to modify the query."


class ConfirmUserSqlHandler(StageHandler):
    """Handler for CONFIRM_USER_SQL stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        user_lower = user_utterance.lower()
        
        if "yes" in user_lower or "ok" in user_lower or "correct" in user_lower or "execute" in user_lower:
            logger.info("✅ User confirmed their SQL")
            memory.stage = Stage.EXECUTE_SQL
            return memory, "Great! Executing the query..."
        
        elif "no" in user_lower or "change" in user_lower or "modify" in user_lower:
            logger.info("🔄 User wants to modify their SQL")
            memory.stage = Stage.NEED_USER_SQL
            return memory, "Please provide the corrected SQL query:"
        
        else:
            return memory, "Please confirm: Say 'yes' to execute or 'no' to provide a different query."


class ExecuteSqlHandler(StageHandler):
    """Handler for EXECUTE_SQL stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        logger.info("🔧 Gathering parameters for read_sql...")
        
        action = call_job_agent(memory, user_utterance, tool_name="read_sql")
        
        if action.get("action") == "ASK":
            memory.last_question = action["question"]
            return memory, action["question"]
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "read_sql":
            logger.info("⚡ Executing read_sql_job...")
            params = action.get("params", {})

            try:
                connection_id = self.connection_service.get_connection_id(memory.connection)
                if not connection_id:
                    logger.error(f"❌ Unknown connection: {memory.connection}")
                    return memory, f"❌ Error: Unknown connection '{memory.connection}'. Please select a valid connection."
                
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
                    read_sql_vars.result_schema = params.get("result_schema")
                    read_sql_vars.table_name = params.get("table_name")
                    read_sql_vars.drop_before_create = params.get("drop_before_create", False)
                    read_sql_vars.only_dataset_columns = params.get("only_dataset_columns", False)
                    logger.info(f"📝 ReadSQL with execute_query=true")

                if write_count:
                    write_count_conn_name = params.get("write_count_connection", memory.connection)
                    write_count_conn_id = self.connection_service.get_connection_id(write_count_conn_name)
                    if not write_count_conn_id:
                        logger.error(f"❌ Unknown write_count connection: {write_count_conn_name}")
                        return memory, f"❌ Error: Unknown connection '{write_count_conn_name}' for write_count."

                    read_sql_vars.write_count_connection = write_count_conn_id
                    read_sql_vars.write_count_schema = params.get("write_count_schema")
                    read_sql_vars.write_count_table = params.get("write_count_table")

                request = ReadSqlLLMRequest(
                    rights={"owner": "184431757886694"},
                    props={"active": "true", "name": params.get("name", "ReadSQL_Job"), "description": ""},
                    variables=[read_sql_vars]
                )
                
                result = await self.job_execution_service.execute_read_sql(request)
                
                logger.info(f"📊 read_sql_job result: {json.dumps(result, indent=2)}")
                
                if result.get("message") == "Success":
                    memory.last_job_id = result.get("job_id")
                    memory.last_job_name = params.get("name", "ReadSQL_Job")
                    memory.last_job_folder = "3023602439587835"
                    memory.last_columns = result.get("columns", [])
                    memory.execute_query_enabled = execute_query
                    memory.stage = Stage.SHOW_RESULTS
                    
                    cols_str = ", ".join(memory.last_columns[:5])
                    if len(memory.last_columns) > 5:
                        cols_str += f"... ({len(memory.last_columns)} total)"
                    
                    if execute_query:
                        return memory, f"✅ Query executed and data saved!\n📊 Columns: {cols_str}\n🆔 Job ID: {memory.last_job_id}"
                    else:
                        return memory, f"✅ Query executed successfully!\n📊 Columns: {cols_str}\n🆔 Job ID: {memory.last_job_id}"
                else:
                    error_msg = result.get("error", "Unknown error")
                    return memory, f"❌ Error executing query: {error_msg}\nWould you like to try a different query?"
                    
            except Exception as e:
                logger.error(f"❌ Error in read_sql: {str(e)}", exc_info=True)
                return memory, f"❌ Error: {str(e)}\nPlease try again or rephrase your request."
        
        return memory, "To execute, I need the database connection name. What connection should I use?"
