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
- Extract any NEW parameters from the user's message
- Identify which REQUIRED parameters are still missing FOR THE CURRENT TOOL ONLY
- If parameters are missing, ask ONE clear question
- If all required parameters are present, output the action

IMPORTANT: ONLY check for parameters that belong to the current tool!

Required parameters by tool:

read_sql (ONLY these parameters):
- NO PARAMETERS NEEDED - query and connection are provided automatically
- Do NOT ask for anything, always return action "TOOL"

write_data (ONLY these parameters):
- connection (database connection name) - REQUIRED
- table (table name to write to) - REQUIRED
- drop_or_truncate ("drop", "truncate", or "none") - REQUIRED
- data_set (job_id from previous read_sql) - already available in memory, do NOT ask for it
- columns (from previous read_sql) - already available in memory, do NOT ask for it
- only_dataset_columns (true/false) - defaults to true, do NOT ask for it

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

Be conversational but concise. Ask for ONE missing parameter at a time.
DO NOT ask for parameters that belong to a different tool!
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
                
                # For read_sql, always use fallback to ensure we use memory.connection
                if tool_name == "read_sql":
                    return self._fallback_param_check(memory, tool_name, user_input)
                
                logger.info(f"✅ Job Agent action: {result.get('action')}")
                
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
        
        if tool_name == "read_sql":
            # read_sql: query from SQL agent, connection from memory (external)
            # No need to ask user for anything
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": {
                    "query": memory.last_sql,
                    "connection": memory.connection,  # From memory, not LLM
                    "template": "2223045341865624"
                }
            }
        
        elif tool_name == "write_data":
            if not params.get("table"):
                return {
                    "action": "ASK",
                    "question": "What table should I write the data to?"
                }
            if not params.get("connection"):
                return {
                    "action": "ASK",
                    "question": "What database connection should I use for writing?"
                }
            if not params.get("drop_or_truncate"):
                return {
                    "action": "ASK",
                    "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
                }
            # Have all params
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
