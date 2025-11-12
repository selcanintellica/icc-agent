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
- Identify which REQUIRED parameters are still missing
- If parameters are missing, ask ONE clear question
- If all required parameters are present, output the action

Required parameters by tool:

read_sql:
- query (SQL query) - already known from SQL generation
- connection (database connection name)
- template_id (default: "2223045341865624")

write_data:
- connection (database connection name)
- table (table name to write to)
- data_set (job_id from previous read_sql)
- columns (from previous read_sql)
- drop_or_truncate ("drop", "truncate", or "none")
- only_dataset_columns (true/false)

send_email:
- query (SQL query)
- to (recipient email)
- subject (email subject)
- text (email body)
- connection (database connection)
- attachment (true/false, default: true)

Response format (JSON):
{
  "action": "ASK" or "TOOL" or "FINISH",
  "question": "your question if ASK",
  "tool_name": "read_sql|write_data|send_email if TOOL",
  "params": {...extracted params...},
  "message": "completion message if FINISH"
}

Be conversational but concise. Ask for ONE missing parameter at a time.
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
                
                # Update gathered params
                if "params" in result and result["params"]:
                    memory.gathered_params.update(result["params"])
                
                logger.info(f"✅ Job Agent action: {result.get('action')}")
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Job Agent: Could not parse JSON: {e}")
                logger.error(f"Raw content: {content}")
                
                # Fallback: Ask for parameters manually
                return self._fallback_param_check(memory, tool_name)
                
        except Exception as e:
            logger.error(f"❌ Job Agent error: {str(e)}")
            return self._fallback_param_check(memory, tool_name)
    
    def _fallback_param_check(self, memory: Memory, tool_name: str) -> Dict[str, Any]:
        """Fallback parameter checking if LLM fails."""
        params = memory.gathered_params
        
        if tool_name == "read_sql":
            if not params.get("connection"):
                return {
                    "action": "ASK",
                    "question": "What database connection should I use? (e.g., 'oracle_prod', 'mysql_dev')"
                }
            # Have all required params
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": {
                    "query": memory.last_sql,
                    "connection": params["connection"],
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
