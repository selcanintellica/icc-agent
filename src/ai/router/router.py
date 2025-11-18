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
        memory.stage = Stage.NEED_QUERY
        return memory, "What SQL query would you like to execute? (e.g., 'get customers from USA')"
    
    # ========== STAGE: NEED_QUERY ==========
    if memory.stage == Stage.NEED_QUERY:
        logger.info("📝 Generating SQL from natural language...")
        
        # Generate SQL using SQL agent
        spec = call_sql_agent(user_utterance)
        memory.last_sql = spec.sql
        
        # Check if it's a SELECT query
        if "select" not in spec.sql.lower():
            warning = "\n⚠️ Note: This is a non-SELECT query. "
        else:
            warning = ""
        
        memory.stage = Stage.HAVE_SQL
        
        response = f"I prepared this SQL:\n```sql\n{spec.sql}\n```{warning}\nShall I execute it?"
        logger.info(f"✅ SQL generated: {spec.sql}")
        
        return memory, response
    
    # ========== STAGE: HAVE_SQL ==========
    if memory.stage == Stage.HAVE_SQL:
        logger.info("🔧 Gathering parameters for read_sql...")
        
        # Use job agent to gather parameters
        action = call_job_agent(memory, user_utterance, tool_name="read_sql")
        
        if action.get("action") == "ASK":
            # Need more parameters
            return memory, action["question"]
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "read_sql":
            logger.info("⚡ Executing read_sql_job...")
            
            try:
                # Build the request - use connection from memory (set externally)
                request = ReadSqlLLMRequest(
                    rights={"owner": "184431757886694"},
                    props={"active": "true", "name": f"Query_{memory.last_sql[:20]}", "description": ""},
                    variables=[ReadSqlVariables(
                        query=memory.last_sql,
                        connection=memory.connection,  # Use connection from memory
                        execute_query=True
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
                    
                    # Convert columns to ColumnSchema format
                    columns = [ColumnSchema(columnName=col) for col in memory.last_columns]
                    
                    request = WriteDataLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": f"Write_{params.get('table', 'table')}", "description": ""},
                        variables=[WriteDataVariables(
                            connection=params.get("connection", "default"),
                            table=params.get("table", "output_table"),
                            data_set=memory.last_job_id,
                            columns=columns,
                            drop_or_truncate=params.get("drop_or_truncate", "none"),
                            only_dataset_columns=True
                        )]
                    )
                    
                    result = await write_data_job(request)
                    
                    logger.info(f"📊 write_data_job result: {json.dumps(result, indent=2, default=str)}")
                    
                    return memory, f"✅ Data written successfully to table '{params.get('table')}'!\nAnything else? (email / done)"
                    
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
                    
                    request = SendEmailLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": "Email_Results", "description": ""},
                        variables=[SendEmailVariables(
                            query=memory.last_sql,
                            to=params.get("to"),
                            subject=params.get("subject", "Query Results"),
                            text=params.get("text", "Please find the query results attached."),
                            connection=params.get("connection", "default"),
                            attachment=True
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
