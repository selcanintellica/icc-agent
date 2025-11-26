"""
Main staged router - orchestrates the conversation flow through different stages.
"""
import logging
import json
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from src.ai.router.sql_agent import call_sql_agent
from src.ai.router.job_agent import call_job_agent
from src.ai.toolkits.icc_toolkit import read_sql_job, write_data_job, send_email_job, compare_sql_job
from src.utils.connections import get_connection_id
from src.models.natural_language import (
    ReadSqlLLMRequest,
    ReadSqlVariables,
    WriteDataLLMRequest,
    WriteDataVariables,
    SendEmailLLMRequest,
    SendEmailVariables,
    CompareSqlLLMRequest,
    CompareSqlVariables,
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
        memory.stage = Stage.ASK_JOB_TYPE
        return memory, "How would you like to proceed? 'readsql' or 'comparesql'?"
    
    # ========== STAGE: ASK_JOB_TYPE ==========
    if memory.stage == Stage.ASK_JOB_TYPE:
        user_lower = user_utterance.lower()
        
        if "compare" in user_lower:
            logger.info("📝 User chose: COMPARE SQL")
            memory.job_type = "comparesql"
            memory.stage = Stage.ASK_FIRST_SQL_METHOD
            return memory, "For the FIRST query, how would you like to proceed?\n• Type 'create' - I'll generate SQL\n• Type 'provide' - You provide the SQL"
        
        elif "read" in user_lower:
            logger.info("📝 User chose: READ SQL")
            memory.job_type = "readsql"
            memory.stage = Stage.ASK_SQL_METHOD
            return memory, "How would you like to proceed?\n• Type 'create' - I'll generate SQL from your natural language\n• Type 'provide' - You provide the SQL query directly"
            
        else:
            return memory, "Please choose: 'readsql' or 'comparesql'"

    # ==================================================================================
    #                              READ SQL FLOW
    # ==================================================================================

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
    
    # ==================================================================================
    #                              COMPARE SQL FLOW
    # ==================================================================================
    
    # ========== STAGE: ASK_FIRST_SQL_METHOD ==========
    if memory.stage == Stage.ASK_FIRST_SQL_METHOD:
        user_lower = user_utterance.lower()
        if "create" in user_lower or "generate" in user_lower:
            memory.stage = Stage.NEED_FIRST_NATURAL_LANGUAGE
            return memory, "Describe what data you want for the FIRST query in natural language."
        elif "provide" in user_lower or "write" in user_lower:
            memory.stage = Stage.NEED_FIRST_USER_SQL
            return memory, "Please provide your FIRST SQL query:"
        else:
            return memory, "Please choose 'create' or 'provide' for the first query."

    # ========== STAGE: NEED_FIRST_NATURAL_LANGUAGE ==========
    if memory.stage == Stage.NEED_FIRST_NATURAL_LANGUAGE:
        spec = call_sql_agent(user_utterance, connection=memory.connection, schema=memory.schema, selected_tables=memory.selected_tables)
        memory.first_sql = spec.sql
        memory.stage = Stage.CONFIRM_FIRST_GENERATED_SQL
        return memory, f"I prepared this FIRST SQL:\n```sql\n{spec.sql}\n```\nIs this okay? (yes/no)"

    # ========== STAGE: NEED_FIRST_USER_SQL ==========
    if memory.stage == Stage.NEED_FIRST_USER_SQL:
        memory.first_sql = user_utterance.strip()
        memory.stage = Stage.CONFIRM_FIRST_USER_SQL
        return memory, f"You provided this FIRST SQL:\n```sql\n{memory.first_sql}\n```\nIs this correct? (yes/no)"

    # ========== STAGE: CONFIRM_FIRST_GENERATED_SQL / CONFIRM_FIRST_USER_SQL ==========
    if memory.stage in [Stage.CONFIRM_FIRST_GENERATED_SQL, Stage.CONFIRM_FIRST_USER_SQL]:
        user_lower = user_utterance.lower()
        if "yes" in user_lower or "ok" in user_lower:
            memory.stage = Stage.ASK_SECOND_SQL_METHOD
            return memory, "Great! Now for the SECOND query, how would you like to proceed?\n• 'create'\n• 'provide'"
        elif "no" in user_lower:
            memory.stage = Stage.NEED_FIRST_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_FIRST_GENERATED_SQL else Stage.NEED_FIRST_USER_SQL
            return memory, "No problem! Please provide/describe the first query again:"
        else:
            return memory, "Please say 'yes' to proceed or 'no' to change the first query."

    # ========== STAGE: ASK_SECOND_SQL_METHOD ==========
    if memory.stage == Stage.ASK_SECOND_SQL_METHOD:
        user_lower = user_utterance.lower()
        if "create" in user_lower or "generate" in user_lower:
            memory.stage = Stage.NEED_SECOND_NATURAL_LANGUAGE
            return memory, "Describe what data you want for the SECOND query in natural language."
        elif "provide" in user_lower or "write" in user_lower:
            memory.stage = Stage.NEED_SECOND_USER_SQL
            return memory, "Please provide your SECOND SQL query:"
        else:
            return memory, "Please choose 'create' or 'provide' for the second query."

    # ========== STAGE: NEED_SECOND_NATURAL_LANGUAGE ==========
    if memory.stage == Stage.NEED_SECOND_NATURAL_LANGUAGE:
        spec = call_sql_agent(user_utterance, connection=memory.connection, schema=memory.schema, selected_tables=memory.selected_tables)
        memory.second_sql = spec.sql
        memory.stage = Stage.CONFIRM_SECOND_GENERATED_SQL
        return memory, f"I prepared this SECOND SQL:\n```sql\n{spec.sql}\n```\nIs this okay? (yes/no)"

    # ========== STAGE: NEED_SECOND_USER_SQL ==========
    if memory.stage == Stage.NEED_SECOND_USER_SQL:
        memory.second_sql = user_utterance.strip()
        memory.stage = Stage.CONFIRM_SECOND_USER_SQL
        return memory, f"You provided this SECOND SQL:\n```sql\n{memory.second_sql}\n```\nIs this correct? (yes/no)"

    # ========== STAGE: CONFIRM_SECOND_GENERATED_SQL / CONFIRM_SECOND_USER_SQL ==========
    if memory.stage in [Stage.CONFIRM_SECOND_GENERATED_SQL, Stage.CONFIRM_SECOND_USER_SQL]:
        user_lower = user_utterance.lower()
        if "yes" in user_lower or "ok" in user_lower:
            # Fetch columns for both queries before showing map table
            logger.info("📊 Fetching columns for both queries...")
            try:
                connection_id = get_connection_id(memory.connection)
                if not connection_id:
                    return memory, f"❌ Error: Unknown connection '{memory.connection}'."
                
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
                    
                    # Fetch first query columns
                    query_payload1 = QueryPayload(connectionId=connection_id, sql=memory.first_sql, folderId="")
                    col_resp1 = await QueryRepository.get_column_names(repo, query_payload1)
                    memory.first_columns = col_resp1.data.object.columns if col_resp1.success else []
                    
                    # Fetch second query columns
                    query_payload2 = QueryPayload(connectionId=connection_id, sql=memory.second_sql, folderId="")
                    col_resp2 = await QueryRepository.get_column_names(repo, query_payload2)
                    memory.second_columns = col_resp2.data.object.columns if col_resp2.success else []
                
                logger.info(f"📊 First columns: {memory.first_columns}")
                logger.info(f"📊 Second columns: {memory.second_columns}")
                
                memory.stage = Stage.ASK_AUTO_MATCH
                return memory, f"Both queries confirmed!\n\nFirst query columns: {', '.join(memory.first_columns)}\nSecond query columns: {', '.join(memory.second_columns)}\n\nWould you like to auto-match columns with the same name? (yes/no)"
                
            except Exception as e:
                logger.error(f"❌ Error fetching columns: {str(e)}", exc_info=True)
                return memory, f"❌ Error fetching columns: {str(e)}"
        elif "no" in user_lower:
            memory.stage = Stage.NEED_SECOND_NATURAL_LANGUAGE if memory.stage == Stage.CONFIRM_SECOND_GENERATED_SQL else Stage.NEED_SECOND_USER_SQL
            return memory, "No problem! Please provide/describe the second query again:"
        else:
            return memory, "Please say 'yes' to execute or 'no' to change the second query."

    # ========== STAGE: ASK_AUTO_MATCH ==========
    if memory.stage == Stage.ASK_AUTO_MATCH:
        user_lower = user_utterance.lower()
        auto_match = "yes" in user_lower or "auto" in user_lower
        
        # Prepare response for frontend to show map table popup
        memory.stage = Stage.WAITING_MAP_TABLE
        
        response_data = {
            "action": "show_map_table",
            "first_columns": memory.first_columns,
            "second_columns": memory.second_columns,
            "auto_matched": auto_match
        }
        
        # If auto-match, pre-populate mappings with same-name columns
        if auto_match:
            auto_mappings = []
            for col in memory.first_columns:
                if col in memory.second_columns:
                    auto_mappings.append({"FirstMappedColumn": col, "SecondMappedColumn": col})
            response_data["pre_mappings"] = auto_mappings
        
        import json
        return memory, f"MAP_TABLE_POPUP:{json.dumps(response_data)}"

    # ========== STAGE: WAITING_MAP_TABLE ==========
    if memory.stage == Stage.WAITING_MAP_TABLE:
        # Frontend sends back mapping data as JSON
        try:
            import json
            mapping_data = json.loads(user_utterance)
            
            # Extract key mappings and column mappings
            memory.key_mappings = mapping_data.get("key_mappings", [])
            memory.column_mappings = mapping_data.get("column_mappings", [])
            
            # Extract first_table_keys and second_table_keys from key_mappings
            first_keys = [m["FirstKey"] for m in memory.key_mappings]
            second_keys = [m["SecondKey"] for m in memory.key_mappings]
            memory.gathered_params["first_table_keys"] = ",".join(first_keys)
            memory.gathered_params["second_table_keys"] = ",".join(second_keys)
            
            logger.info(f"📊 Key mappings: {memory.key_mappings}")
            logger.info(f"📊 Column mappings: {memory.column_mappings}")
            
            memory.stage = Stage.ASK_REPORTING_TYPE
            return memory, f"Mappings received!\n\nKeys: {first_keys}\nMapped columns: {len(memory.column_mappings)} pairs\n\nNow, what type of reporting do you want?\n• 'identical' - Show only identical records\n• 'onlyDifference' - Show only different values\n• 'onlyInTheFirstDataset' - Show records only in first dataset\n• 'onlyInTheSecondDataset' - Show records only in second dataset\n• 'allDifference' - Show all differences"
        except json.JSONDecodeError:
            return memory, "Invalid mapping data received. Please use the Map Table popup to configure mappings."
    
    # ========== STAGE: ASK_REPORTING_TYPE ==========
    if memory.stage == Stage.ASK_REPORTING_TYPE:
        user_lower = user_utterance.lower()
        
        # Map user input to reporting type
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
            return memory, "Please choose a valid reporting type: 'identical', 'onlyDifference', 'onlyInTheFirstDataset', 'onlyInTheSecondDataset', or 'allDifference'"
        
        memory.stage = Stage.ASK_COMPARE_SCHEMA
        return memory, f"Reporting type set to '{memory.gathered_params['reporting']}'.\n\nWhich schema do you want to save the comparison results to?"

    # ========== STAGE: ASK_COMPARE_SCHEMA ==========
    if memory.stage == Stage.ASK_COMPARE_SCHEMA:
        schema_name = user_utterance.strip()
        if not schema_name:
            return memory, "Please provide a schema name to save the results:"
        
        memory.gathered_params["schemas"] = schema_name
        memory.stage = Stage.ASK_COMPARE_TABLE_NAME
        return memory, f"Schema set to '{schema_name}'.\n\nWhat table name do you want to use for the comparison results?"

    # ========== STAGE: ASK_COMPARE_TABLE_NAME ==========
    if memory.stage == Stage.ASK_COMPARE_TABLE_NAME:
        table_name = user_utterance.strip()
        if not table_name:
            return memory, "Please provide a table name to save the results:"
        
        memory.gathered_params["table_name"] = table_name
        memory.stage = Stage.EXECUTE_COMPARE_SQL
        return memory, f"Table name set to '{table_name}'.\n\nExecuting compare SQL job..."

    # ========== STAGE: EXECUTE_COMPARE_SQL ==========
    if memory.stage == Stage.EXECUTE_COMPARE_SQL:
        logger.info("⚡ Executing compare_sql_job...")
        try:
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                return memory, f"❌ Error: Unknown connection '{memory.connection}'."
            
            params = memory.gathered_params
            
            # Get keys from gathered params (set by WAITING_MAP_TABLE stage)
            first_keys = params.get("first_table_keys", "")
            second_keys = params.get("second_table_keys", "")
            
            # Convert mappings to JSON strings for the payload
            import json
            keys_mapping_json = json.dumps(memory.key_mappings) if memory.key_mappings else None
            column_mapping_json = json.dumps(memory.column_mappings) if memory.column_mappings else None
            
            # Build request with gathered params and mappings
            request = CompareSqlLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "false", "name": "Compare_Job", "description": ""},
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
                    calculate_difference=params.get("calculate_difference", False),
                    keys_mapping=keys_mapping_json,
                    column_mapping=column_mapping_json
                )]
            )
            
            result = await compare_sql_job(request)
            
            if result.get("message") == "Success":
                memory.last_job_id = result.get("job_id")
                memory.stage = Stage.NEED_WRITE_OR_EMAIL
                memory.gathered_params = {}  # Reset for next steps
                return memory, f"✅ Compare Job executed! Job ID: {memory.last_job_id}\nWhat next? (email / done)"
            else:
                return memory, f"❌ Error: {result.get('error')}"
        
        except Exception as e:
            logger.error(f"❌ Error in compare_sql: {str(e)}", exc_info=True)
            return memory, f"❌ Error: {str(e)}"


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
                    # For compare jobs, we might not have last_columns populated the same way as read_sql
                    # If job_type is comparesql, last_columns might be empty or different.
                    # But user said: "So instead of doing SQL-WRITEDATA-SENDEMAIL..."
                    # Assuming write_data works with compare job results too.
                    columns = [ColumnSchema(columnName=col) for col in (memory.last_columns or [])]
                    
                    request = WriteDataLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": f"Write_{table_name}", "description": ""},
                        variables=[WriteDataVariables(
                            data_set=memory.last_job_id,  # Job ID from read_sql/compare_sql
                            columns=columns,  # Columns from read_sql result (or empty for compare?)
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
                    
                    # Use first_sql if available, else last_sql
                    query_to_use = memory.last_sql or memory.first_sql or "SELECT 1 FROM DUAL"

                    request = SendEmailLLMRequest(
                        rights={"owner": "184431757886694"},
                        props={"active": "true", "name": "Email_Results", "description": ""},
                        variables=[SendEmailVariables(
                            query=query_to_use,  # SQL generated by SQL agent
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
