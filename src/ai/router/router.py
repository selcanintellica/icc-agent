"""
Main staged router - orchestrates the conversation flow through different stages.
"""
import logging
import json
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from src.ai.router.sql_agent import call_sql_agent
from src.ai.router.job_agent import call_job_agent
from src.ai.toolkits.icc_toolkit import read_sql_job, write_data_job, send_email_job
from src.utils.connections import get_connection_id
from src.models.natural_language import (
    ReadSqlLLMRequest,
    ReadSqlVariables,
    WriteDataLLMRequest,
    WriteDataVariables,
    SendEmailLLMRequest,
    SendEmailVariables,
    ColumnSchema
)

logger = logging.getLogger(__name__)


async def handle_turn(memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
    """
    One conversational turn. Returns updated memory and a response string.
    
    Args:
        memory: Current conversation memory
        user_utterance: User's input message
        
    Returns:
        Tuple of (updated memory, response message)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 ROUTER: Stage={memory.stage.value}, Input='{user_utterance[:50]}...'")
    logger.info(f"{'='*60}")
    
    # ========== STAGE: START ==========
    if memory.stage == Stage.START:
        memory.stage = Stage.ASK_SQL_METHOD
        return memory, "How would you like to proceed?\n• Type 'create' - I'll generate SQL from your natural language\n• Type 'provide' - You provide the SQL query directly"
    
    # ========== STAGE: ASK_SQL_METHOD ==========
    if memory.stage == Stage.ASK_SQL_METHOD:
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
            # User didn't clearly indicate, ask again
            return memory, "Please choose:\n• 'create' - I'll generate SQL for you\n• 'provide' - You'll write the SQL"
    
    # ========== STAGE: NEED_NATURAL_LANGUAGE ==========
    if memory.stage == Stage.NEED_NATURAL_LANGUAGE:
        logger.info("📝 Generating SQL from natural language...")
        
        # Generate SQL using SQL agent with selected tables context
        spec = call_sql_agent(
            user_utterance, 
            connection=memory.connection,
            schema=memory.schema,
            selected_tables=memory.selected_tables
        )
        memory.last_sql = spec.sql
        
        # Check if it's a SELECT query
        if "select" not in spec.sql.lower():
            warning = "\n⚠️ Note: This is a non-SELECT query. "
        else:
            warning = ""
        
        memory.stage = Stage.CONFIRM_GENERATED_SQL
        
        response = f"I prepared this SQL:\n```sql\n{spec.sql}\n```{warning}\nIs this okay? (yes/no)\nSay 'no' to modify, or 'yes' to execute."
        logger.info(f"✅ SQL generated: {spec.sql}")
        
        return memory, response
    
    # ========== STAGE: NEED_USER_SQL ==========
    if memory.stage == Stage.NEED_USER_SQL:
        logger.info("✍️ User provided SQL directly")
        
        # Store the user's SQL
        memory.last_sql = user_utterance.strip()
        
        # Check if it looks like SQL (basic validation)
        if not any(keyword in memory.last_sql.lower() for keyword in ["select", "insert", "update", "delete", "create", "drop"]):
            return memory, "⚠️ That doesn't look like a SQL query. Please provide a valid SQL statement:"
        
        # Check if it's a SELECT query
        if "select" not in memory.last_sql.lower():
            warning = "\n⚠️ Note: This is a non-SELECT query. "
        else:
            warning = ""
        
        memory.stage = Stage.CONFIRM_USER_SQL
        
        response = f"You provided this SQL:\n```sql\n{memory.last_sql}\n```{warning}\nIs this correct? (yes/no)"
        logger.info(f"✅ User SQL received: {memory.last_sql}")
        
        return memory, response
    
    # ========== STAGE: CONFIRM_GENERATED_SQL ==========
    if memory.stage == Stage.CONFIRM_GENERATED_SQL:
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
    
    # ========== STAGE: CONFIRM_USER_SQL ==========
    if memory.stage == Stage.CONFIRM_USER_SQL:
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
    
    # ========== STAGE: EXECUTE_SQL ==========
    if memory.stage == Stage.EXECUTE_SQL:
        logger.info("🔧 Gathering parameters for read_sql...")
        
        # Use job agent to gather parameters
        action = call_job_agent(memory, user_utterance, tool_name="read_sql")
        
        if action.get("action") == "ASK":
            # Need more parameters
            return memory, action["question"]
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "read_sql":
            logger.info("⚡ Executing read_sql_job...")
            
            try:
                # Get connection ID from connection name
                connection_id = get_connection_id(memory.connection)
                if not connection_id:
                    logger.error(f"❌ Unknown connection: {memory.connection}")
                    return memory, f"❌ Error: Unknown connection '{memory.connection}'. Please select a valid connection."
                
                logger.info(f"🔌 Using connection: {memory.connection} (ID: {connection_id})")
                
                # Build the request - use connection ID for API
                request = ReadSqlLLMRequest(
                    rights={"owner": "184431757886694"},
                    props={"active": "true", "name": f"Query_{memory.last_sql[:20]}", "description": ""},
                    variables=[ReadSqlVariables(
                        query=memory.last_sql,
                        connection=connection_id,  # Use connection ID for API
                        execute_query=True,
                        table_name=""  # Always empty as per requirements
                    )]
                )
                
                # Execute the tool directly (no @tool decorator)
                result = await read_sql_job(request)
                
                logger.info(f"📊 read_sql_job result: {json.dumps(result, indent=2)}")
                
                if result.get("message") == "Success":
                    # Save job_id and columns for later use
                    memory.last_job_id = result.get("job_id")
                    memory.last_columns = result.get("columns", [])
                    memory.stage = Stage.SHOW_RESULTS
                    
                    cols_str = ", ".join(memory.last_columns[:5])
                    if len(memory.last_columns) > 5:
                        cols_str += f"... ({len(memory.last_columns)} total)"
                    
                    return memory, f"✅ Query executed successfully!\n📊 Columns: {cols_str}\n🆔 Job ID: {memory.last_job_id}"
                else:
                    error_msg = result.get("error", "Unknown error")
                    return memory, f"❌ Error executing query: {error_msg}\nWould you like to try a different query?"
                    
            except Exception as e:
                logger.error(f"❌ Error in read_sql: {str(e)}", exc_info=True)
                return memory, f"❌ Error: {str(e)}\nPlease try again or rephrase your request."
        
        return memory, "To execute, I need the database connection name. What connection should I use?"
    
    # ========== STAGE: SHOW_RESULTS ==========
    if memory.stage == Stage.SHOW_RESULTS:
        memory.stage = Stage.NEED_WRITE_OR_EMAIL
        memory.gathered_params = {}  # Reset for next operation
        
        return memory, "What would you like to do next?\n• 'write' - Save results to a table\n• 'email' - Send results via email\n• 'both' - Write and email\n• 'done' - Finish"
    
    # ========== STAGE: NEED_WRITE_OR_EMAIL ==========
    if memory.stage == Stage.NEED_WRITE_OR_EMAIL:
        user_lower = user_utterance.lower()
        
        # Check user intent
        if "done" in user_lower or "finish" in user_lower or "complete" in user_lower:
            memory.stage = Stage.DONE
            return memory, "✅ All done! Say 'new query' to start again."
        
        # Determine which tool to use
        wants_write = "write" in user_lower or "save" in user_lower or "store" in user_lower
        wants_email = "email" in user_lower or "send" in user_lower
        
        if wants_write:
            logger.info("📝 Processing write_data request...")
            
            action = call_job_agent(memory, user_utterance, tool_name="write_data")
            
            if action.get("action") == "ASK":
                return memory, action["question"]
            
            if action.get("action") == "TOOL" and action.get("tool_name") == "write_data":
                logger.info("⚡ Executing write_data_job...")
                
                try:
                    params = memory.gathered_params
                    
                    # Get connection ID from connection name
                    connection_id = get_connection_id(memory.connection)
                    if not connection_id:
                        logger.error(f"❌ Unknown connection: {memory.connection}")
                        return memory, f"❌ Error: Unknown connection '{memory.connection}'. Please select a valid connection."
                    
                    logger.info(f"🔌 Using connection: {memory.connection} (ID: {connection_id})")
                    
                    # Get table name from params (user provides destination table)
                    table_name = params.get("table", "output_table")
                    
                    # Get and validate drop_or_truncate - must be DROP, TRUNCATE, or INSERT
                    drop_or_truncate = params.get("drop_or_truncate", "INSERT").upper()
                    if drop_or_truncate not in ["DROP", "TRUNCATE", "INSERT"]:
                        logger.warning(f"⚠️ Invalid drop_or_truncate value: {drop_or_truncate}, defaulting to INSERT")
                        drop_or_truncate = "INSERT"
                    
                    # Convert columns to ColumnSchema format
                    columns = [ColumnSchema(columnName=col) for col in memory.last_columns]
                    
                    request = WriteDataLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": f"Write_{table_name}", "description": ""},
                        variables=[WriteDataVariables(
                            data_set=memory.last_job_id,  # Job ID from read_sql
                            columns=columns,  # Columns from read_sql result
                            add_columns=[],  # Always empty as per requirements
                            connection=connection_id,  # Use connection ID for API
                            schemas=memory.schema,  # Use schema from UI selection
                            table=table_name,  # Destination table from user
                            drop_or_truncate=drop_or_truncate,  # DROP, TRUNCATE, or INSERT
                            only_dataset_columns=True  # Fixed value
                        )]
                    )
                    
                    result = await write_data_job(request)
                    
                    logger.info(f"📊 write_data_job result: {json.dumps(result, indent=2, default=str)}")
                    
                    return memory, f"✅ Data written successfully to table '{table_name}' in {memory.schema} schema!\nAnything else? (email / done)"
                    
                except Exception as e:
                    logger.error(f"❌ Error in write_data: {str(e)}", exc_info=True)
                    return memory, f"❌ Error: {str(e)}\nPlease try again."
        
        elif wants_email:
            logger.info("📧 Processing send_email request...")
            
            action = call_job_agent(memory, user_utterance, tool_name="send_email")
            
            if action.get("action") == "ASK":
                return memory, action["question"]
            
            if action.get("action") == "TOOL" and action.get("tool_name") == "send_email":
                logger.info("⚡ Executing send_email_job...")
                
                try:
                    params = memory.gathered_params
                    
                    # Get connection ID from connection name
                    connection_id = get_connection_id(memory.connection)
                    if not connection_id:
                        logger.error(f"❌ Unknown connection: {memory.connection}")
                        return memory, f"❌ Error: Unknown connection '{memory.connection}'. Please select a valid connection."
                    
                    logger.info(f"🔌 Using connection: {memory.connection} (ID: {connection_id})")
                    
                    request = SendEmailLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": "Email_Results", "description": ""},
                        variables=[SendEmailVariables(
                            query=memory.last_sql,  # SQL generated by SQL agent
                            connection=connection_id,  # Use connection ID for API
                            to=params.get("to"),  # Email recipient from user
                            subject=params.get("subject", "Query Results"),  # Subject from user or default
                            text=params.get("text", "Please find the query results attached."),  # Message from user or default
                            attachment=True  # Always attach results
                        )]
                    )
                    
                    result = await send_email_job(request)
                    
                    logger.info(f"📊 send_email_job result: {json.dumps(result, indent=2, default=str)}")
                    
                    return memory, f"✅ Email sent to {params.get('to')}!\nAnything else? (write / done)"
                    
                except Exception as e:
                    logger.error(f"❌ Error in send_email: {str(e)}", exc_info=True)
                    return memory, f"❌ Error: {str(e)}\nPlease try again."
        
        return memory, "Please specify: 'write to <table>', 'email to <address>', or 'done'"
    
    # ========== STAGE: DONE ==========
    if memory.stage == Stage.DONE:
        if "new" in user_utterance.lower() or "again" in user_utterance.lower():
            memory.reset()
            return memory, "Starting fresh! What query would you like to run?"
        
        return memory, "Session complete. Say 'new query' to start again."
    
    # Fallback
    return memory, "I didn't quite catch that. Could you rephrase?"
