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
1. The current tool we need to execute (read_sql, write_data, or send_email)
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
- NO OTHER PARAMETERS NEEDED - query and connection are provided automatically

write_data (ONLY these parameters):
- name (job name for props.name) - REQUIRED
- table (table name to write to) - REQUIRED
- schemas (schema name) - REQUIRED
- drop_or_truncate ("drop", "truncate", or "none") - REQUIRED
- connection (database connection name) - already available in memory (same as read_sql), do NOT ask for it
- data_set (job_id from previous read_sql) - already available in memory, do NOT ask for it
- columns (from previous read_sql) - already available in memory, do NOT ask for it
- only_dataset_columns (true/false) - defaults to false, do NOT ask for it
- write_count (true/false) - defaults to false, do NOT ask for it
- write_count_connection, write_count_schemas, write_count_table - only needed if write_count is true, do NOT ask for these

send_email (ONLY these parameters):
- to (recipient email) - REQUIRED
- subject (email subject) - REQUIRED
- query (SQL query) - already available in memory
- text (email body) - optional
- connection (database connection) - optional
- attachment (true/false) - defaults to true

Response format (JSON):
{
  "action": "ASK" or "TOOL",
  "question": "your question if ASK",
  "tool_name": "read_sql|write_data|send_email if TOOL",
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

Be conversational but concise. Ask for ONE missing parameter at a time.
DO NOT ask for parameters that belong to a different tool!
ALWAYS include extracted params in your response!
"""


class JobAgent:
    """Agent that gathers parameters and determines when to invoke tools."""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=os.getenv("MODEL_NAME", "qwen3:1.7b"),
            temperature=0.3,
            base_url="http://localhost:11434",
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
        
        # Build context
        context = {
            "tool_name": tool_name,
            "already_have": memory.gathered_params,
            "last_sql": memory.last_sql,
            "last_job_id": memory.last_job_id,
            "last_columns": memory.last_columns
        }
        
        context_str = json.dumps(context, indent=2)
        
        try:
            messages = [
                SystemMessage(content=PARAMETER_EXTRACTION_PROMPT),
                HumanMessage(content=f"Context:\n{context_str}\n\nUser input: {user_input}")
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            logger.info(f"🤖 Job Agent raw response: {content[:300]}...")
            
            # Parse JSON response
            try:
                # Clean markdown if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
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
            # Check if we have name parameter from user
            if not params.get("name"):
                return {
                    "action": "ASK",
                    "question": "What should I name this read_sql job?"
                }
            # Have all params
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": {
                    "query": memory.last_sql,
                    "connection": memory.connection,  # From memory, not LLM
                    "template": "2223045341865624",
                    "name": params["name"]
                }
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
            if not params.get("schemas"):
                logger.info("❌ Missing: schemas")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the data to?"
                }
            # Connection is inherited from memory (same as read_sql), not asked from user
            if not params.get("connection"):
                params["connection"] = memory.connection
            if not params.get("drop_or_truncate"):
                logger.info("❌ Missing: drop_or_truncate")
                return {
                    "action": "ASK",
                    "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
                }
            # Have all params
            logger.info(f"✅ All write_data params present: {params}")
            return {
                "action": "TOOL",
                "tool_name": "write_data",
                "params": params
            }
        
        elif tool_name == "send_email":
            if not params.get("to"):
                return {
                    "action": "ASK",
                    "question": "Who should I send the email to?"
                }
            if not params.get("subject"):
                return {
                    "action": "ASK",
                    "question": "What should the email subject be?"
                }
            # Have enough params
            return {
                "action": "TOOL",
                "tool_name": "send_email",
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
