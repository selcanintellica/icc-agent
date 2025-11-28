"""
Job parameter agent - extracts parameters and asks clarifying questions.
This agent knows how to gather required parameters for each tool.
"""
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Dict, Any, Optional
import json
import logging
from src.ai.router.memory import Memory

logger = logging.getLogger(__name__)

# Job-specific minimal prompts for better performance
WRITE_DATA_PROMPT_TEMPLATE = """Extract params for write_data job.

CRITICAL: IGNORE confirmation words like "ok", "okay", "yes", "no", "sure" - these are NOT parameter values!

Parameters needed (in order) with EXACT types:
1. name (string): Job name to identify it later (NEVER extract "ok"/"okay"/"yes"/"no" as name)
2. table (string): Which table to write data to?
3. connection (string): Which database connection to use? (see list below)
4. schemas (string): Which schema contains the table? (DO NOT ASK - system will fetch available schemas after connection is selected)
5. drop_or_truncate (string): "drop", "truncate", or "none" - Ask "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
6. write_count (boolean): true or false - Ask "Would you like to track the row count for this write operation? (yes/no)"

Available connections:
{connections}

IMPORTANT: 
- After connection is selected, DO NOT ask about schemas. The missing schemas will trigger automatic schema fetching.
- schemas must be a STRING (e.g., "ANONYMOUS"), NOT a list
- write_count must be a BOOLEAN (true/false), not a string

Ask ONE clear, friendly question at a time. Don't list all parameters at once.

Output JSON: {{\"action\": \"ASK\"|\"TOOL\", \"question\": \"...\", \"params\": {{...}}}}"""

READ_SQL_PROMPT = """Extract params for read_sql job.

IMPORTANT: Extract params from user input FIRST, then ask for missing ones.
CRITICAL: IGNORE confirmation words like "ok", "okay", "yes", "no", "sure" - these are NOT parameter values!

Parameters with EXACT types:
- name (string): Job name (NEVER extract "ok"/"okay"/"yes"/"no" as name - ask for a real job name)
- execute_query (boolean): true or false - Ask "Would you like to save the query results to the database?" (yes=true, no=false)
- write_count (boolean): true or false - Ask "Would you like to track the row count?" (yes=true, no=false)
- result_schema (string): ONLY needed if execute_query=true. Extract from user or ask.
- table_name (string): ONLY needed if execute_query=true. Extract from user or ask.
- drop_before_create (boolean): ONLY needed if execute_query=true. Extract yes/no from user or ask.

IMPORTANT: execute_query and write_count must be BOOLEAN (true/false), not strings.

If user provides a REAL value (not just confirmation), extract it into params. Ask ONE question at a time.

Output JSON: {"action": "ASK"|"TOOL", "question": "...", "params": {...}}"""

SEND_EMAIL_PROMPT = """Extract params for send_email job.

CRITICAL: IGNORE confirmation words like "ok", "okay", "yes", "no", "sure" - these are NOT parameter values!

Parameters needed with EXACT types:
- name (string): Job name to identify it later (NEVER extract "ok"/"okay"/"yes"/"no" as name)
- to (string): Recipient email address
- subject (string): Email subject line
- cc (string): CC email addresses (optional, can be empty string)
- text (string): Email body text (optional)

Ask ONE clear, friendly question at a time. Don't list all parameters at once.

Output JSON: {{\"action\": \"ASK\"|\"TOOL\", \"question\": \"...\", \"params\": {{...}}}}"""


PARAMETER_EXTRACTION_PROMPT = """You are a parameter extraction assistant. Your job is to extract required parameters from user input or ask for missing ones.

You are given:
1. The current tool we need to execute (read_sql, write_data, send_email, or compare_sql)
2. Parameters we already have
3. User's latest message

Your task:
- CAREFULLY READ the user's message and extract ANY parameters they mention
- Look for patterns like "name is X", "table is Y", "schema is Z", "insert/drop/truncate"
- Check which REQUIRED parameters are STILL missing FOR THE CURRENT TOOL ONLY
- If parameters are missing, ask ONE clear question
- If all required parameters are present, return action "TOOL"

IMPORTANT: 
- ONLY check for parameters that belong to the current tool!
- ALWAYS extract parameters from the user's message into the "params" field
- Even if asking a question, include any extracted params in your response

Required parameters by tool:

read_sql (ONLY these parameters with EXACT types):
- name (string) - job name for props.name - REQUIRED
- execute_query (boolean) - true or false - Ask: "Would you like to save the query results to the database?" - REQUIRED
  * If user says yes/true: set execute_query=true and ask for result_schema, table_name, drop_before_create
  * If user says no/false: set execute_query=false, skip other write-related questions
- result_schema (string) - target schema name - REQUIRED only if execute_query=true
- table_name (string) - target table name - REQUIRED only if execute_query=true  
- drop_before_create (boolean) - true or false - REQUIRED only if execute_query=true. Ask: "Should I drop the table before creating it? (yes/no)"
- only_dataset_columns (boolean) - defaults to false if execute_query=true, do NOT ask
- write_count (boolean) - true or false - Ask: "Would you like to track the row count?" - REQUIRED
  * If user says yes/true: set write_count=true and ask for write_count_schema, write_count_table, write_count_connection
  * If user says no/false: set write_count=false, skip write_count-related questions
- write_count_schema (string) - schema name - REQUIRED only if write_count=true
- write_count_table (string) - table name - REQUIRED only if write_count=true
- write_count_connection (string) - connection name - REQUIRED only if write_count=true. Use memory.connection as default suggestion.
- query (string) and connection (string) are provided automatically

write_data (ONLY these parameters with EXACT types):
- name (string) - job name for props.name - REQUIRED
- table (string) - table name to write to - REQUIRED
- schemas (string) - schema name - REQUIRED - MUST BE STRING, NOT LIST
- drop_or_truncate (string) - "drop", "truncate", or "none" - REQUIRED
- connection (string) - database connection name - Ask user to select from available connections - REQUIRED
- write_count (boolean) - true or false - Ask: "Would you like to track the row count for this write operation?" - REQUIRED
  * If user says yes/true: set write_count=true and ask for write_count_schemas, write_count_table, write_count_connection
  * If user says no/false: set write_count=false, skip write_count-related questions
- write_count_schemas (string) - schema name - REQUIRED only if write_count=true
- write_count_table (string) - table name - REQUIRED only if write_count=true
- write_count_connection (string) - connection name - REQUIRED only if write_count=true. Use memory.connection as default suggestion.
- data_set (string) - job_id from previous read_sql - already available in memory, do NOT ask for it
- columns (array) - from previous read_sql - already available in memory, do NOT ask for it
- only_dataset_columns (boolean) - defaults to false, do NOT ask for it

send_email (ONLY these parameters):
- name (job name for props.name) - REQUIRED
- to (recipient email) - REQUIRED
- subject (email subject) - REQUIRED
- cc (CC email addresses) - OPTIONAL (if user says no/none, leave empty)
- query (SQL query) - already available in memory
- text (email body) - optional
- connection (database connection) - optional
- attachment (true/false) - defaults to true

compare_sql (ONLY these parameters):
- first_table_keys (comma separated columns for first table key) - REQUIRED
- second_table_keys (comma separated columns for second table key) - REQUIRED
- case_sensitive (true/false) - optional, default false
- reporting (identical, difference, etc.) - optional, default identical
- drop_before_create (true/false) - optional, default true
- calculate_difference (true/false) - optional, default false
- connection - optional, uses context

Response format (JSON):
{
  "action": "ASK" or "TOOL",
  "question": "your question if ASK",
  "tool_name": "read_sql|write_data|send_email|compare_sql if TOOL",
  "params": {...extracted params...}
}

EXAMPLES:

Example 1 - Extracting multiple params:
User: "name of the job is writedata_ss, target table is target_tt, schema name is target_ss, you can insert the table"
Response: {"action": "TOOL", "tool_name": "write_data", "params": {"name": "writedata_ss", "table": "target_tt", "schemas": "target_ss", "drop_or_truncate": "none"}}

Example 2 - Extracting partial params:
User: "call it my_job and write to users table"
Response: {"action": "ASK", "question": "What schema should I write to?", "params": {"name": "my_job", "table": "users"}}

Example 3 - User provides just one param:
User: "writedata_ss"
Response: {"action": "ASK", "question": "What table should I write the data to?", "params": {"name": "writedata_ss"}}

Example 4 - ReadSQL with execute_query flow:
User: "yes" (answering if they want to save results)
Response: {"action": "ASK", "question": "What schema should I write the results to?", "params": {"execute_query": true}}

Example 5 - ReadSQL without saving:
User: "no" (answering if they want to save results)
Response: {"action": "ASK", "question": "Would you like to track the row count of the query results? (yes/no)", "params": {"execute_query": false, "name": "my_readsql_job"}}

Example 6 - ReadSQL with write_count flow:
User: "yes" (answering if they want to track row count)
Response: {"action": "ASK", "question": "What schema should I write the row count to?", "params": {"write_count": true}}

Example 7 - WriteData with write_count:
User: "yes" (answering if they want to track row count for write operation)
Response: {"action": "ASK", "question": "What schema should I write the row count to?", "params": {"name": "my_write_job", "table": "dest_table", "schemas": "dest_schema", "drop_or_truncate": "none", "write_count": true}}

CRITICAL RULES:
- Output ONLY valid, complete JSON with proper closing braces
- Keep questions under 80 characters for speed
- No markdown, no explanations, just JSON
- Always include extracted params
- Ask for ONE missing parameter at a time
- DO NOT ask for parameters that belong to a different tool!
"""


class JobAgent:
    """Agent that gathers parameters and determines when to invoke tools."""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=os.getenv("MODEL_NAME", "qwen3:1.7b"),
            temperature=0.1,  # Lower temperature for more consistent JSON
            base_url="http://localhost:11434",
            num_predict=6000,  # Increased to 4096 - qwen3:8b is a thinking model that needs more tokens
            model_kwargs={
                "think": False,        
                "stream": False      
            }
        )
    
    def gather_params(
        self,
        memory: Memory,
        user_input: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Extract parameters from user input and determine next action.
        
        Args:
            memory: Conversation memory with context
            user_input: Latest user message
            tool_name: Which tool we're gathering params for
            
        Returns:
            Dict with action (ASK/TOOL/FINISH), question, params, etc.
        """
        logger.info(f"🔍 Job Agent: Gathering params for '{tool_name}'")
        logger.info(f"📋 Current params: {memory.gathered_params}")
        
        # Build minimal context (avoid overwhelming small models)
        context = {
            "tool_name": tool_name,
            "already_have": memory.gathered_params
        }
        
        # Only add relevant context for specific tools
        if tool_name in ["write_data", "send_email"]:
            if memory.last_job_id:
                context["has_previous_job"] = True
        
        context_str = json.dumps(context, indent=2)
        
        try:
            # Use job-specific minimal prompts for better performance
            if tool_name == "write_data":
                # Build missing params list
                missing = []
                if not memory.gathered_params.get("name"): missing.append("name")
                if not memory.gathered_params.get("table"): missing.append("table")
                if not memory.gathered_params.get("schemas"): missing.append("schemas")
                if not memory.gathered_params.get("connection"): missing.append("connection")
                if not memory.gathered_params.get("drop_or_truncate"): missing.append("drop_or_truncate")
                if not memory.gathered_params.get("write_count"): missing.append("write_count")
                
                # Get connection list and inject into system prompt
                connection_list = memory.get_connection_list_for_llm() if memory.connections else "(Using connection from previous job)"
                system_prompt = WRITE_DATA_PROMPT_TEMPLATE.format(connections=connection_list)
                
                # SIMPLIFIED prompt - just ask for missing param
                # Include last question for context if available
                last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
                
                prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}
Output JSON only:"""


                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt_text)
                ]
                
            elif tool_name == "read_sql":
                # SIMPLIFIED prompt for read_sql
                missing = []
                if not memory.gathered_params.get("name"): missing.append("name")
                if "execute_query" not in memory.gathered_params: missing.append("execute_query")
                if memory.gathered_params.get("execute_query") and not memory.gathered_params.get("result_schema"): missing.append("result_schema")
                if memory.gathered_params.get("execute_query") and not memory.gathered_params.get("table_name"): missing.append("table_name")
                if memory.gathered_params.get("execute_query") and "drop_before_create" not in memory.gathered_params: missing.append("drop_before_create")
                if "write_count" not in memory.gathered_params: missing.append("write_count")
                
                # Include last question for context if available
                last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
                
                prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}

Example - If user says "read23", extract: {{"name": "read23"}}
Example - If user says "yes", extract: {{"execute_query": true}} or {{"write_count": true}}

Output JSON only:"""
                
                messages = [
                    SystemMessage(content=READ_SQL_PROMPT),
                    HumanMessage(content=prompt_text)
                ]
                logger.info(f"📝 -------------- Read SQL prompt: {messages}--------------------")
                
            elif tool_name == "send_email":
                # Minimal prompt for send_email
                missing = []
                if not memory.gathered_params.get("name"): missing.append("name")
                if not memory.gathered_params.get("to"): missing.append("to")
                if not memory.gathered_params.get("subject"): missing.append("subject")
                
                # Include last question for context if available
                last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
                
                prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
                
                messages = [
                    SystemMessage(content=SEND_EMAIL_PROMPT),
                    HumanMessage(content=prompt_text)
                ]
            else:
                # Fallback to original prompt for compare_sql or unknown tools
                prompt_text = f"""Tool: {tool_name}
Current params: {json.dumps(memory.gathered_params)}
User said: "{user_input}"

IMPORTANT: Output ONLY the JSON response. Do NOT include any thinking, explanation, or commentary.
Just output the JSON object directly.

Extract parameters or ask for missing ones."""
                
                messages = [
                    SystemMessage(content=PARAMETER_EXTRACTION_PROMPT),
                    HumanMessage(content=prompt_text)
                ]
            
            response = self.llm.invoke(messages)
            logger.info(f"📝 Job Agent raw response: {response}")
            content = response.content.strip()
            final_answer = response.additional_kwargs.get("content")
            logger.info(f"📝 Final answer from LLM: {final_answer}")
            
            logger.info(f"🤖 Job Agent raw response: {content[:300]}...")
            
            # Check for empty response
            if not content:
                logger.error("❌ LLM returned empty response, using fallback")
                return self._fallback_param_check(memory, tool_name, user_input)
            
            # Parse JSON response
            try:
                # Clean markdown if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # qwen3:8b often includes thinking before/after JSON - extract just the JSON
                if "{" in content:
                    # Find the first { and last } to extract complete JSON
                    start_idx = content.find("{")
                    # Find matching closing brace
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(content)):
                        if content[i] == "{":
                            brace_count += 1
                        elif content[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    content = content[start_idx:end_idx]
                    logger.info(f"📝 Extracted JSON from {start_idx} to {end_idx}")
                
                # Handle truncated JSON by attempting to complete it
                content = content.strip()
                if content and not content.endswith("}"):
                    # Try to close unterminated JSON
                    open_braces = content.count("{") - content.count("}")
                    open_brackets = content.count("[") - content.count("]")
                    # Close any unterminated strings
                    if content.count('"') % 2 != 0:
                        content += '"'
                    # Close brackets and braces
                    content += "]" * open_brackets
                    content += "}" * open_braces
                    logger.warning(f"⚠️ Attempted to fix truncated JSON")
                
                result = json.loads(content)
                
                # Normalize: if LLM returns "message" instead of "question", fix it
                if "message" in result and "question" not in result:
                    result["question"] = result["message"]
                
                # Normalize params before updating memory
                if "params" in result and result["params"]:
                    params = result["params"]
                    
                    # Fix: LLM sometimes returns schemas as list instead of string
                    if "schemas" in params and isinstance(params["schemas"], list):
                        params["schemas"] = params["schemas"][0] if params["schemas"] else ""
                        logger.info(f"📝 Normalized schemas from list to string: {params['schemas']}")
                    
                    # Only update with non-None values
                    new_params = {k: v for k, v in params.items() if v is not None}
                    memory.gathered_params.update(new_params)
                    logger.info(f"📝 Updated gathered_params: {memory.gathered_params}")
                
                logger.info(f"✅ Job Agent action: {result.get('action')}, params: {result.get('params')}")
                
                # Check for direct yes/no answers BEFORE using LLM's question
                # This handles cases where LLM doesn't extract yes/no into params
                if user_input and user_input.lower().strip() in ["yes", "y", "no", "n", "true", "false", "1", "0"]:
                    user_lower = user_input.lower().strip()
                    
                    # For read_sql: Handle parameter flow carefully
                    if tool_name == "read_sql":
                        # Check what we're currently asking for based on current params
                        if not memory.gathered_params.get("name"):
                            # Asking for name - don't treat yes/no as name
                            pass
                        elif "execute_query" not in memory.gathered_params:
                            # Currently asking for execute_query
                            if user_lower in ["yes", "y", "true", "1"]:
                                memory.gathered_params["execute_query"] = True
                                logger.info("📝 Set execute_query=True from direct user input")
                            elif user_lower in ["no", "n", "false", "0"]:
                                memory.gathered_params["execute_query"] = False
                                logger.info("📝 Set execute_query=False from direct user input")
                        elif memory.gathered_params.get("execute_query") and not memory.gathered_params.get("result_schema"):
                            # execute_query=true but missing result_schema - don't treat yes/no as schema name
                            pass
                        elif memory.gathered_params.get("execute_query") and memory.gathered_params.get("result_schema") and not memory.gathered_params.get("table_name"):
                            # Have result_schema but missing table_name - don't treat yes/no as table name
                            pass
                        elif memory.gathered_params.get("execute_query") and "drop_before_create" not in memory.gathered_params:
                            # Currently asking for drop_before_create
                            if user_lower in ["yes", "y", "true", "1"]:
                                memory.gathered_params["drop_before_create"] = True
                                logger.info("📝 Set drop_before_create=True from direct user input")
                            elif user_lower in ["no", "n", "false", "0"]:
                                memory.gathered_params["drop_before_create"] = False
                                logger.info("📝 Set drop_before_create=False from direct user input")
                        elif "write_count" not in memory.gathered_params:
                            # Currently asking for write_count (after all execute_query params)
                            if user_lower in ["yes", "y", "true", "1"]:
                                memory.gathered_params["write_count"] = True
                                logger.info("📝 Set write_count=True from direct user input")
                            elif user_lower in ["no", "n", "false", "0"]:
                                memory.gathered_params["write_count"] = False
                                logger.info("📝 Set write_count=False from direct user input")
                    
                    # For write_data: only write_count uses yes/no
                    elif tool_name == "write_data" and "write_count" not in memory.gathered_params:
                        if user_lower in ["yes", "y", "true", "1"]:
                            memory.gathered_params["write_count"] = True
                            logger.info("📝 Set write_count=True from direct user input")
                        elif user_lower in ["no", "n", "false", "0"]:
                            memory.gathered_params["write_count"] = False
                            logger.info("📝 Set write_count=False from direct user input")
                
                # If LLM returned a valid question, use it directly
                if result.get("action") == "ASK" and result.get("question"):
                    logger.info(f"📝 Using LLM's question: {result['question']}")
                    # But check if we just handled a yes/no - if so, don't ask the same question again
                    if user_input and user_input.lower().strip() in ["yes", "y", "no", "n", "true", "false", "1", "0"]:
                        # Re-run gathering to get next question (with EMPTY user_input to avoid re-processing)
                        logger.info("📝 Just handled yes/no, checking for next required param")
                        return self._fallback_param_check(memory, tool_name, user_input="")
                    
                    # If asking for connection for write_data, append available connections list
                    question = result.get("question", "")
                    if tool_name == "write_data" and "connection" in question.lower() and "connection" not in memory.gathered_params:
                        connection_list = memory.get_connection_list_for_llm()
                        if connection_list:
                            result["question"] = f"Which connection should I use to write the data?\n\nAvailable connections:\n{connection_list}"
                            logger.info("📝 Enhanced connection question with available connections list")
                    
                    return result
                
                # If LLM says all params ready (TOOL), validate with fallback
                # This ensures we have all required params and apply business rules
                if result.get("action") == "TOOL":
                    return self._fallback_param_check(memory, tool_name, user_input)
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Job Agent: Could not parse JSON: {e}")
                logger.error(f"Raw content: {content}")
                
                # Fallback: Ask for parameters manually
                return self._fallback_param_check(memory, tool_name, user_input)
                
        except Exception as e:
            logger.error(f"❌ Job Agent error: {str(e)}")
            return self._fallback_param_check(memory, tool_name, user_input)
    
    def _check_write_count_params(self, params: Dict[str, Any], memory: Memory, param_prefix: str = "write_count") -> Optional[Dict[str, Any]]:
        """Check write_count related parameters. Returns ASK action if missing, None if complete.
        
        Args:
            params: Current gathered parameters
            memory: Conversation memory
            param_prefix: Prefix for parameter names ('write_count' or 'write_count')
        """
        schema_param = f"{param_prefix}_schema" if param_prefix == "write_count" else f"{param_prefix}_schemas"
        
        if not params.get(schema_param):
            logger.info(f"❌ Missing: {schema_param} (write_count=true)")
            return {
                "action": "ASK",
                "question": "What schema should I write the row count to?"
            }
        if not params.get(f"{param_prefix}_table"):
            logger.info(f"❌ Missing: {param_prefix}_table (write_count=true)")
            return {
                "action": "ASK",
                "question": "What table should I write the row count to?"
            }
        if not params.get(f"{param_prefix}_connection"):
            logger.info(f"❌ Missing: {param_prefix}_connection (write_count=true), suggesting: {memory.connection}")
            return {
                "action": "ASK",
                "question": f"What connection should I use for the row count? (Press enter for '{memory.connection}')"
            }
        
        # If user just pressed enter or said "same", use memory.connection
        if params.get(f"{param_prefix}_connection", "").strip() in ["", "same", "default"]:
            params[f"{param_prefix}_connection"] = memory.connection
            logger.info(f"📝 Using default connection for write_count: {memory.connection}")
        
        return None  # All params present
    
    def _fallback_param_check(self, memory: Memory, tool_name: str, user_input: str = "") -> Dict[str, Any]:
        """Fallback parameter checking if LLM fails. Just asks questions, doesn't try to extract."""
        params = memory.gathered_params
        logger.info(f"🔧 Fallback check for {tool_name}, current params: {params}")
        
        if tool_name == "read_sql":
            # Check if we have name parameter from user
            if not params.get("name"):
                logger.info("❌ Missing: name")
                return {
                    "action": "ASK",
                    "question": "What should I name this read_sql job?"
                }
            
            # Check if we should ask about execute_query
            if "execute_query" not in params:
                logger.info("❓ Asking about execute_query")
                return {
                    "action": "ASK",
                    "question": "Would you like to save the query results to the database? (yes/no)"
                }
            
            # If execute_query is true, we need additional parameters
            if params.get("execute_query"):
                if not params.get("result_schema"):
                    logger.info("❌ Missing: result_schema (execute_query=true)")
                    # Get available schemas from db_config.json for the selected connection
                    try:
                        from src.utils.config_loader import get_config_loader
                        config_loader = get_config_loader()
                        available_schemas = config_loader.get_schemas_for_connection(memory.connection)
                        
                        if available_schemas:
                            schema_list = "\n".join([f"• {schema}" for schema in available_schemas])
                            question = f"What schema should I write the results to?\n\nAvailable schemas in {memory.connection}:\n{schema_list}"
                            logger.info(f"📋 Showing {len(available_schemas)} available schemas for result_schema")
                        else:
                            question = "What schema should I write the results to?"
                            logger.warning(f"⚠️ No schemas found in db_config.json for connection {memory.connection}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not load schema list from db_config.json: {e}")
                        question = "What schema should I write the results to?"
                    
                    return {
                        "action": "ASK",
                        "question": question
                    }
                if not params.get("table_name"):
                    logger.info("❌ Missing: table_name (execute_query=true)")
                    return {
                        "action": "ASK",
                        "question": "What table should I write the results to?"
                    }
                if "drop_before_create" not in params:
                    logger.info("❓ Asking about drop_before_create")
                    return {
                        "action": "ASK",
                        "question": "Should I drop the table before creating it? (yes/no)"
                    }
                # All execute_query params complete, fall through to check write_count
            
            # Check if we should ask about write_count
            # NOTE: This is asked AFTER all execute_query parameters are complete
            if "write_count" not in params:
                logger.info("❓ Asking about write_count")
                return {
                    "action": "ASK",
                    "question": "Would you like to track the row count of the query results? (yes/no)"
                }
            
            # If write_count is true, we need additional parameters
            if params.get("write_count"):
                result = self._check_write_count_params(params, memory, "write_count")
                if result:  # Missing parameters
                    return result
            
            # Have all required params
            logger.info(f"✅ All read_sql params present: {params}")
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": params
            }
        
        elif tool_name == "write_data":
            if not params.get("name"):
                logger.info("❌ Missing: name")
                return {
                    "action": "ASK",
                    "question": "What should I name this write_data job?"
                }
            if not params.get("table"):
                logger.info("❌ Missing: table")
                return {
                    "action": "ASK",
                    "question": "What table should I write the data to?"
                }
            
            # Ask user for connection from available dynamic connections FIRST
            if not params.get("connection"):
                logger.info("❌ Missing: connection for write_data")
                # Get available connections from memory
                logger.info(f"📋 Memory has {len(memory.connections)} connections: {list(memory.connections.keys())[:5] if memory.connections else 'EMPTY'}")
                connection_list = memory.get_connection_list_for_llm()
                logger.info(f"📋 Connection list for LLM: {connection_list[:200] if connection_list else 'EMPTY'}...")
                # Check if we have actual connections (not just the "No connections available" message)
                if connection_list and memory.connections:
                    return {
                        "action": "ASK",
                        "question": f"Which connection should I use to write the data?\n\nAvailable connections:\n{connection_list}"
                    }
                else:
                    # Fallback: use the same connection as read_sql
                    params["connection"] = memory.connection
                    logger.info(f"⚠️ No dynamic connections available, using read_sql connection: {memory.connection}")
            
            # Now that we have connection, fetch schemas if not already cached
            if not params.get("schemas"):
                # Check if we need to fetch schemas for the selected connection
                connection_name = params.get("connection")
                if connection_name and not memory.available_schemas:
                    # Need to fetch schemas - signal to router to do async fetch
                    logger.info(f"📋 Need to fetch schemas for connection: {connection_name}")
                    return {
                        "action": "FETCH_SCHEMAS",
                        "connection": connection_name,
                        "question": "Fetching available schemas..."
                    }
                elif memory.available_schemas:
                    # We have schemas, ask user to choose
                    logger.info("❌ Missing: schemas (have cached list)")
                    schema_list = memory.get_schema_list_for_llm()
                    return {
                        "action": "ASK",
                        "question": f"Which schema should I write the data to?\n\nAvailable schemas:\n{schema_list}"
                    }
                else:
                    # No connection ID available, ask for schema without list
                    logger.info("❌ Missing: schemas (no cached list)")
                    return {
                        "action": "ASK",
                        "question": "What schema should I write the data to?"
                    }
            if not params.get("drop_or_truncate"):
                logger.info("❌ Missing: drop_or_truncate")
                return {
                    "action": "ASK",
                    "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
                }
            
            # Check if we should ask about write_count
            if "write_count" not in params:
                logger.info("❓ Asking about write_count for write_data")
                return {
                    "action": "ASK",
                    "question": "Would you like to track the row count for this write operation? (yes/no)"
                }
            
            # If write_count is true, we need additional parameters
            if params.get("write_count"):
                result = self._check_write_count_params(params, memory, "write_count")
                if result:  # Missing parameters
                    return result
            
            # Have all params
            logger.info(f"✅ All write_data params present: {params}")
            return {
                "action": "TOOL",
                "tool_name": "write_data",
                "params": params
            }
        
        elif tool_name == "send_email":
            if not params.get("name"):
                logger.info("❌ Missing: name")
                return {
                    "action": "ASK",
                    "question": "What should I name this email job?"
                }
            if not params.get("to"):
                logger.info("❌ Missing: to")
                return {
                    "action": "ASK",
                    "question": "Who should I send the email to?"
                }
            if not params.get("subject"):
                logger.info("❌ Missing: subject")
                return {
                    "action": "ASK",
                    "question": "What should the email subject be?"
                }
            # Check for CC only if not already asked
            if "cc" not in params:
                logger.info("❓ Asking for CC (optional)")
                return {
                    "action": "ASK",
                    "question": "Would you like to add any CC email addresses? (Say 'no' or 'none' to skip, or provide email addresses)"
                }
            # Normalize CC: if user said no/none, set to empty string
            cc_value = params.get("cc", "")
            if isinstance(cc_value, str) and cc_value.lower().strip() in ["no", "none", "skip", "n/a"]:
                params["cc"] = ""
                logger.info("📧 CC normalized to empty string (user declined)")
            # Have all required params (cc might be empty string if user said no)
            logger.info(f"✅ All send_email params present: {params}")
            return {
                "action": "TOOL",
                "tool_name": "send_email",
                "params": params
            }

        elif tool_name == "compare_sql":
            if not params.get("first_table_keys"):
                return {
                    "action": "ASK",
                    "question": "What are the key columns for the first query? (comma separated)"
                }
            if not params.get("second_table_keys"):
                return {
                    "action": "ASK",
                    "question": "What are the key columns for the second query? (comma separated)"
                }
            # Have enough params
            return {
                "action": "TOOL",
                "tool_name": "compare_sql",
                "params": params
            }
        
        return {
            "action": "ASK",
            "question": "I need more information. What would you like to do?"
        }


# Global instance
job_agent = JobAgent()


def call_job_agent(memory: Memory, user_input: str, tool_name: str = "read_sql") -> Dict[str, Any]:
    """
    Call the job parameter agent.
    
    Args:
        memory: Conversation memory
        user_input: User's message
        tool_name: Tool we're gathering params for
        
    Returns:
        Action dict with next steps
    """
    return job_agent.gather_params(memory, user_input, tool_name)
