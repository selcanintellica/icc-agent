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

read_sql (ONLY these parameters):
- name (job name for props.name) - REQUIRED
- execute_query (true/false) - Ask: "Would you like to save the query results to the database?" - REQUIRED
  * If user says yes/true: set execute_query=true and ask for result_schema, table_name, drop_before_create
  * If user says no/false: set execute_query=false, skip other write-related questions
- result_schema (target schema name) - REQUIRED only if execute_query=true
- table_name (target table name) - REQUIRED only if execute_query=true  
- drop_before_create (true/false) - REQUIRED only if execute_query=true. Ask: "Should I drop the table before creating it? (yes/no)"
- only_dataset_columns (true/false) - defaults to false if execute_query=true, do NOT ask
- write_count (true/false) - Ask: "Would you like to track the row count?" - REQUIRED
  * If user says yes/true: set write_count=true and ask for write_count_schema, write_count_table, write_count_connection
  * If user says no/false: set write_count=false, skip write_count-related questions
- write_count_schema (schema name) - REQUIRED only if write_count=true
- write_count_table (table name) - REQUIRED only if write_count=true
- write_count_connection (connection name) - REQUIRED only if write_count=true. Use memory.connection as default suggestion.
- query and connection are provided automatically

write_data (ONLY these parameters):
- name (job name for props.name) - REQUIRED
- table (table name to write to) - REQUIRED
- schemas (schema name) - REQUIRED
- drop_or_truncate ("drop", "truncate", or "none") - REQUIRED
- connection (database connection name) - Ask user to select from available connections - REQUIRED
- data_set (job_id from previous read_sql) - already available in memory, do NOT ask for it
- columns (from previous read_sql) - already available in memory, do NOT ask for it
- only_dataset_columns (true/false) - defaults to false, do NOT ask for it
- write_count (true/false) - Ask: "Would you like to track the row count for this write operation?" - REQUIRED
  * If user says yes/true: set write_count=true and ask for write_count_schemas, write_count_table, write_count_connection
  * If user says no/false: set write_count=false, skip write_count-related questions
- write_count_schemas (schema name) - REQUIRED only if write_count=true
- write_count_table (table name) - REQUIRED only if write_count=true
- write_count_connection (connection name) - REQUIRED only if write_count=true. Use memory.connection as default suggestion.

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
            num_predict=800,  # Allow space for thinking + JSON (qwen3:8b thinks out loud)
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
            # Simplified prompt for better LLM performance
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
            content = response.content.strip()
            
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
                
                # Update gathered params (filter out None values)
                if "params" in result and result["params"]:
                    # Only update with non-None values
                    new_params = {k: v for k, v in result["params"].items() if v is not None}
                    memory.gathered_params.update(new_params)
                    logger.info(f"📝 Updated gathered_params: {memory.gathered_params}")
                
                # For read_sql, always use fallback to ensure we use memory.connection
                if tool_name == "read_sql":
                    return self._fallback_param_check(memory, tool_name, user_input)
                
                logger.info(f"✅ Job Agent action: {result.get('action')}, params: {result.get('params')}")
                
                # For write_data, use fallback to ensure proper validation
                if tool_name == "write_data":
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
    
    def _fallback_param_check(self, memory: Memory, tool_name: str, user_input: str = "") -> Dict[str, Any]:
        """Fallback parameter checking if LLM fails."""
        params = memory.gathered_params
        logger.info(f"🔧 Fallback check for {tool_name}, current params: {params}")
        
        # Simple heuristic: if user gives a single word answer, try to match it to missing params
        if user_input and tool_name == "write_data":
            user_lower = user_input.strip().lower()
            
            # Check for drop_or_truncate values
            if not params.get("drop_or_truncate"):
                if user_lower in ["drop", "truncate", "none", "insert", "append"]:
                    # Map user input to expected values
                    if user_lower in ["insert", "append"]:
                        params["drop_or_truncate"] = "none"
                    else:
                        params["drop_or_truncate"] = user_lower
                    logger.info(f"✅ Detected drop_or_truncate from user input: {params['drop_or_truncate']}")
        
        if tool_name == "read_sql":
            # Direct parameter extraction ONLY for non-confirmation words
            if user_input and user_input.strip() and len(user_input.strip().split()) == 1:
                user_value = user_input.strip().lower()
                # Skip common confirmation/filler words that aren't actual parameters
                skip_words = ["yes", "y", "no", "n", "ok", "okay", "sure", "fine", "done", "next"]
                
                if user_value not in skip_words:
                    user_value = user_input.strip()  # Preserve original case
                    # Determine which single parameter is currently missing
                    missing_params = []
                    if not params.get("name"): missing_params.append("name")
                    if params.get("execute_query") and not params.get("result_schema"): missing_params.append("result_schema")
                    if params.get("execute_query") and not params.get("table_name"): missing_params.append("table_name")
                    if params.get("write_count") and not params.get("write_count_schema"): missing_params.append("write_count_schema")
                    if params.get("write_count") and not params.get("write_count_table"): missing_params.append("write_count_table")
                    
                    # Only use direct extraction if exactly ONE param is missing
                    if len(missing_params) == 1:
                        param_name = missing_params[0]
                        params[param_name] = user_value
                        logger.info(f"📝 Direct extraction (single missing): {param_name}={user_value}")
            
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
            
            # Normalize execute_query response
            execute_query_value = params.get("execute_query", False)
            if isinstance(execute_query_value, str):
                execute_query_value = execute_query_value.lower().strip() in ["yes", "true", "y", "1"]
                params["execute_query"] = execute_query_value
                logger.info(f"📝 Normalized execute_query to: {execute_query_value}")
            
            # If execute_query is true, we need additional parameters
            if params.get("execute_query"):
                if not params.get("result_schema"):
                    logger.info("❌ Missing: result_schema (execute_query=true)")
                    return {
                        "action": "ASK",
                        "question": "What schema should I write the results to?"
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
                
                # Normalize drop_before_create response
                drop_value = params.get("drop_before_create", False)
                if isinstance(drop_value, str):
                    drop_value = drop_value.lower().strip() in ["yes", "true", "y", "1", "drop"]
                    params["drop_before_create"] = drop_value
                    logger.info(f"📝 Normalized drop_before_create to: {drop_value}")
            
            # Check user_input directly FIRST for yes/no responses (more reliable than LLM extraction)
            if user_input and "write_count" not in params:
                user_lower = user_input.lower().strip()
                if user_lower in ["yes", "y", "true", "1"]:
                    params["write_count"] = True
                    logger.info("📝 Set write_count=True from direct user input")
                elif user_lower in ["no", "n", "false", "0"]:
                    params["write_count"] = False
                    logger.info("📝 Set write_count=False from direct user input")
            
            # Normalize write_count if it exists from LLM extraction
            if "write_count" in params:
                write_count_value = params.get("write_count")
                if isinstance(write_count_value, str):
                    user_lower = write_count_value.lower().strip()
                    write_count_value = user_lower in ["yes", "true", "y", "1"]
                    params["write_count"] = write_count_value
                    logger.info(f"📝 Normalized write_count from LLM extraction to: {write_count_value}")
            
            # Check if we should ask about write_count
            if "write_count" not in params:
                logger.info("❓ Asking about write_count")
                return {
                    "action": "ASK",
                    "question": "Would you like to track the row count of the query results? (yes/no)"
                }
            
            # If write_count is true, we need additional parameters
            if params.get("write_count"):
                if not params.get("write_count_schema"):
                    logger.info("❌ Missing: write_count_schema (write_count=true)")
                    return {
                        "action": "ASK",
                        "question": "What schema should I write the row count to?"
                    }
                if not params.get("write_count_table"):
                    logger.info("❌ Missing: write_count_table (write_count=true)")
                    return {
                        "action": "ASK",
                        "question": "What table should I write the row count to?"
                    }
                if not params.get("write_count_connection"):
                    logger.info(f"❌ Missing: write_count_connection (write_count=true), suggesting: {memory.connection}")
                    return {
                        "action": "ASK",
                        "question": f"What connection should I use for the row count? (Press enter for '{memory.connection}')"
                    }
                
                # If user just pressed enter or said "same", use memory.connection
                if params.get("write_count_connection", "").strip() in ["", "same", "default"]:
                    params["write_count_connection"] = memory.connection
                    logger.info(f"📝 Using default connection for write_count: {memory.connection}")
            
            # Have all required params
            logger.info(f"✅ All read_sql params present: {params}")
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": params
            }
        
        elif tool_name == "write_data":
            # Direct parameter extraction ONLY for non-confirmation words
            if user_input and user_input.strip() and len(user_input.strip().split()) == 1:
                user_value = user_input.strip().lower()
                # Skip common confirmation/filler words that aren't actual parameters
                skip_words = ["yes", "y", "no", "n", "ok", "okay", "sure", "fine", "done", "next", "write", "both", "email"]
                
                if user_value not in skip_words:
                    user_value = user_input.strip()  # Preserve original case
                    # If we're missing ONE parameter and user gives ONE word, it's likely the answer
                    missing_params = []
                    if not params.get("name"): missing_params.append("name")
                    if not params.get("table"): missing_params.append("table")
                    if not params.get("schemas"): missing_params.append("schemas")
                    if not params.get("connection"): missing_params.append("connection")
                    if not params.get("drop_or_truncate"): missing_params.append("drop_or_truncate")
                    
                    # Only use direct extraction if exactly ONE param is missing
                    if len(missing_params) == 1:
                        param_name = missing_params[0]
                        if param_name == "drop_or_truncate" and user_value.lower() in ["drop", "truncate", "none", "insert"]:
                            params[param_name] = user_value.upper()
                            logger.info(f"📝 Direct extraction (single missing): {param_name}={params[param_name]}")
                        elif param_name != "drop_or_truncate":
                            params[param_name] = user_value
                            logger.info(f"📝 Direct extraction (single missing): {param_name}={user_value}")
            
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
            if not params.get("schemas"):
                logger.info("❌ Missing: schemas")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the data to?"
                }
            # Ask user for connection from available dynamic connections
            if not params.get("connection"):
                logger.info("❌ Missing: connection for write_data")
                # Get available connections from memory
                connection_list = memory.get_connection_list_for_llm()
                if connection_list:
                    return {
                        "action": "ASK",
                        "question": f"Which connection should I use to write the data?\n\nAvailable connections:\n{connection_list}"
                    }
                else:
                    # Fallback: use the same connection as read_sql
                    params["connection"] = memory.connection
                    logger.info(f"⚠️ No dynamic connections available, using read_sql connection: {memory.connection}")
            if not params.get("drop_or_truncate"):
                logger.info("❌ Missing: drop_or_truncate")
                return {
                    "action": "ASK",
                    "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
                }
            
            # Check user_input directly FIRST for yes/no responses (more reliable than LLM extraction)
            if user_input and "write_count" not in params:
                user_lower = user_input.lower().strip()
                if user_lower in ["yes", "y", "true", "1"]:
                    params["write_count"] = True
                    logger.info("📝 Set write_count=True from direct user input")
                elif user_lower in ["no", "n", "false", "0"]:
                    params["write_count"] = False
                    logger.info("📝 Set write_count=False from direct user input")
            
            # Normalize write_count if it exists from LLM extraction
            if "write_count" in params:
                write_count_value = params.get("write_count")
                if isinstance(write_count_value, str):
                    user_lower = write_count_value.lower().strip()
                    write_count_value = user_lower in ["yes", "true", "y", "1"]
                    params["write_count"] = write_count_value
                    logger.info(f"📝 Normalized write_count from LLM extraction to: {write_count_value}")
            
            # Check if we should ask about write_count
            if "write_count" not in params:
                logger.info("❓ Asking about write_count for write_data")
                return {
                    "action": "ASK",
                    "question": "Would you like to track the row count for this write operation? (yes/no)"
                }
            
            # If write_count is true, we need additional parameters
            if params.get("write_count"):
                if not params.get("write_count_schemas"):
                    logger.info("❌ Missing: write_count_schemas (write_count=true)")
                    return {
                        "action": "ASK",
                        "question": "What schema should I write the row count to?"
                    }
                if not params.get("write_count_table"):
                    logger.info("❌ Missing: write_count_table (write_count=true)")
                    return {
                        "action": "ASK",
                        "question": "What table should I write the row count to?"
                    }
                if not params.get("write_count_connection"):
                    logger.info(f"❌ Missing: write_count_connection (write_count=true), suggesting: {memory.connection}")
                    return {
                        "action": "ASK",
                        "question": f"What connection should I use for the row count? (Press enter for '{memory.connection}')"
                    }
                
                # If user just pressed enter or said "same", use memory.connection
                if params.get("write_count_connection", "").strip() in ["", "same", "default"]:
                    params["write_count_connection"] = memory.connection
                    logger.info(f"📝 Using default connection for write_count: {memory.connection}")
            
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
