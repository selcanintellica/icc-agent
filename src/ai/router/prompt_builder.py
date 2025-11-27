"""
Prompt Builder - Single Responsibility Principle
Handles all prompt construction logic for different tools.
"""
import json
from typing import List
from langchain_core.messages import HumanMessage, SystemMessage
from src.ai.router.memory import Memory


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

IMPORTANT: execute_query and write_count must be BOOLEAN (true/false), not strings.

If user provides a REAL value (not just confirmation), extract it into params. Ask ONE question at a time.

Output JSON: {{"action": "ASK"|"TOOL", "question": "...", "params": {{...}}}}"""

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


class PromptBuilder:
    """Builds prompts for different job types."""
    
    @staticmethod
    def build_write_data_prompt(memory: Memory, user_input: str) -> List:
        """
        Build prompt for write_data job.
        
        Args:
            memory: Conversation memory
            user_input: User's message
            
        Returns:
            List of messages for LLM
        """
        # Build missing params list
        params = memory.gathered_params
        missing = []
        if not params.get("name"): missing.append("name")
        if not params.get("table"): missing.append("table")
        if not params.get("schemas"): missing.append("schemas")
        if not params.get("connection"): missing.append("connection")
        if not params.get("drop_or_truncate"): missing.append("drop_or_truncate")
        
        # Get connection list and inject into system prompt
        connection_list = memory.get_connection_list_for_llm() if memory.connections else "(Using connection from previous job)"
        system_prompt = WRITE_DATA_PROMPT_TEMPLATE.format(connections=connection_list)
        
        # Include last question for context if available
        last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
        
        prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt_text)
        ]
    
    @staticmethod
    def build_read_sql_prompt(memory: Memory, user_input: str) -> List:
        """
        Build prompt for read_sql job.
        
        Args:
            memory: Conversation memory
            user_input: User's message
            
        Returns:
            List of messages for LLM
        """
        params = memory.gathered_params
        missing = []
        if not params.get("name"): missing.append("name")
        if "execute_query" not in params: missing.append("execute_query")
        if "write_count" not in params: missing.append("write_count")
        
        # Include last question for context if available
        last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
        
        prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(params)}
Missing: {', '.join(missing) if missing else 'none'}

Example - If user says "read23", extract: {{"name": "read23"}}
Example - If user says "yes", extract: {{"execute_query": true}} or {{"write_count": true}}

Output JSON only:"""
        
        return [
            SystemMessage(content=READ_SQL_PROMPT),
            HumanMessage(content=prompt_text)
        ]
    
    @staticmethod
    def build_send_email_prompt(memory: Memory, user_input: str) -> List:
        """
        Build prompt for send_email job.
        
        Args:
            memory: Conversation memory
            user_input: User's message
            
        Returns:
            List of messages for LLM
        """
        params = memory.gathered_params
        missing = []
        if not params.get("name"): missing.append("name")
        if not params.get("to"): missing.append("to")
        if not params.get("subject"): missing.append("subject")
        
        # Include last question for context if available
        last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
        
        prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
        
        return [
            SystemMessage(content=SEND_EMAIL_PROMPT),
            HumanMessage(content=prompt_text)
        ]
    
    @staticmethod
    def build_prompt(tool_name: str, memory: Memory, user_input: str) -> List:
        """
        Build appropriate prompt based on tool name.
        
        Args:
            tool_name: Name of the tool (write_data, read_sql, send_email)
            memory: Conversation memory
            user_input: User's message
            
        Returns:
            List of messages for LLM
        """
        if tool_name == "write_data":
            return PromptBuilder.build_write_data_prompt(memory, user_input)
        elif tool_name == "read_sql":
            return PromptBuilder.build_read_sql_prompt(memory, user_input)
        elif tool_name == "send_email":
            return PromptBuilder.build_send_email_prompt(memory, user_input)
        else:
            # Fallback for unknown tools
            return [
                SystemMessage(content=f"Extract parameters for {tool_name} job."),
                HumanMessage(content=f"User input: {user_input}\nCurrent params: {json.dumps(memory.gathered_params)}")
            ]
