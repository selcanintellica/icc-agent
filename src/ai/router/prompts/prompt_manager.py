"""
Prompt manager for job parameter extraction.

This module manages prompts for the job agent following SOLID principles:
- Single Responsibility: Only responsible for providing prompts
- Open/Closed: Easy to add new prompts without modifying existing code
"""

from typing import Dict, Protocol


class PromptProvider(Protocol):
    """Protocol for prompt providers."""
    
    def get_prompt(self, **kwargs) -> str:
        """Get the formatted prompt."""
        ...


class WriteDataPrompt:
    """Prompt for write_data job parameter extraction."""
    
    TEMPLATE = """Extract params for write_data job.

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

Output JSON: {{"action": "ASK"|"TOOL", "question": "...", "params": {{...}}}}"""
    
    def get_prompt(self, connections: str = "") -> str:
        """Get the write_data prompt with connection list injected."""
        return self.TEMPLATE.format(connections=connections)


class ReadSQLPrompt:
    """Prompt for read_sql job parameter extraction."""
    
    TEMPLATE = """Extract params for read_sql job.

IMPORTANT: Extract params from user input FIRST, then ask for missing ones.
CRITICAL: IGNORE confirmation words like "ok", "okay", "yes", "no", "sure" - these are NOT parameter values!

Parameters with EXACT types:
- name (string): Job name (NEVER extract "ok"/"okay"/"yes"/"no" as name - ask for a real job name)
- execute_query (boolean): true or false - Ask "Would you like to save the query results to the database?" (yes=true, no=false)
- write_count (boolean): true or false - Ask "Would you like to track the row count?" (yes=true, no=false)

IMPORTANT: execute_query and write_count must be BOOLEAN (true/false), not strings.

If user provides a REAL value (not just confirmation), extract it into params. Ask ONE question at a time.

Output JSON: {{"action": "ASK"|"TOOL", "question": "...", "params": {{...}}}}"""
    
    def get_prompt(self) -> str:
        """Get the read_sql prompt."""
        return self.TEMPLATE


class SendEmailPrompt:
    """Prompt for send_email job parameter extraction."""
    
    TEMPLATE = """Extract params for send_email job.

CRITICAL: IGNORE confirmation words like "ok", "okay", "yes", "no", "sure" - these are NOT parameter values!

Parameters needed with EXACT types:
- name (string): Job name to identify it later (NEVER extract "ok"/"okay"/"yes"/"no" as name)
- to (string): Recipient email address
- subject (string): Email subject line
- cc (string): CC email addresses (optional, can be empty string)
- text (string): Email body text (optional)

Ask ONE clear, friendly question at a time. Don't list all parameters at once.

Output JSON: {{"action": "ASK"|"TOOL", "question": "...", "params": {{...}}}}"""
    
    def get_prompt(self) -> str:
        """Get the send_email prompt."""
        return self.TEMPLATE


class ParameterExtractionPrompt:
    """General parameter extraction prompt for all job types."""
    
    TEMPLATE = """You are a parameter extraction assistant. Your job is to extract required parameters from user input or ask for missing ones.

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
  * Note: Results will be saved to the SAME connection as the SQL query, only schema can be different
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
{{
  "action": "ASK" or "TOOL",
  "question": "your question if ASK",
  "tool_name": "read_sql|write_data|send_email|compare_sql if TOOL",
  "params": {{...extracted params...}}
}}

EXAMPLES:

Example 1 - Extracting multiple params:
User: "name of the job is writedata_ss, target table is target_tt, schema name is target_ss, you can insert the table"
Response: {{"action": "TOOL", "tool_name": "write_data", "params": {{"name": "writedata_ss", "table": "target_tt", "schemas": "target_ss", "drop_or_truncate": "none"}}}}

Example 2 - Extracting partial params:
User: "call it my_job and write to users table"
Response: {{"action": "ASK", "question": "What schema should I write to?", "params": {{"name": "my_job", "table": "users"}}}}

Example 3 - User provides just one param:
User: "writedata_ss"
Response: {{"action": "ASK", "question": "What table should I write the data to?", "params": {{"name": "writedata_ss"}}}}

Example 4 - ReadSQL with execute_query flow:
User: "yes" (answering if they want to save results)
Response: {{"action": "ASK", "question": "What schema should I write the results to?", "params": {{"execute_query": true}}}}

Example 5 - ReadSQL without saving:
User: "no" (answering if they want to save results)
Response: {{"action": "ASK", "question": "Would you like to track the row count of the query results? (yes/no)", "params": {{"execute_query": false, "name": "my_readsql_job"}}}}

Example 6 - ReadSQL with write_count flow:
User: "yes" (answering if they want to track row count)
Response: {{"action": "ASK", "question": "What schema should I write the row count to?", "params": {{"write_count": true}}}}

Example 7 - WriteData with write_count:
User: "yes" (answering if they want to track row count for write operation)
Response: {{"action": "ASK", "question": "What schema should I write the row count to?", "params": {{"name": "my_write_job", "table": "dest_table", "schemas": "dest_schema", "drop_or_truncate": "none", "write_count": true}}}}

CRITICAL RULES:
- Output ONLY valid, complete JSON with proper closing braces
- Keep questions under 80 characters for speed
- No markdown, no explanations, just JSON
- Always include extracted params
- Ask for ONE missing parameter at a time
- DO NOT ask for parameters that belong to a different tool!"""
    
    def get_prompt(self) -> str:
        """Get the parameter extraction prompt."""
        return self.TEMPLATE


class PromptManager:
    """
    Manager for all job agent prompts.
    
    Following SOLID principles:
    - Single Responsibility: Only manages prompts
    - Open/Closed: Easy to add new prompts
    - Dependency Inversion: Returns prompts through protocol interface
    """
    
    def __init__(self):
        self._prompts: Dict[str, PromptProvider] = {
            "write_data": WriteDataPrompt(),
            "read_sql": ReadSQLPrompt(),
            "send_email": SendEmailPrompt(),
            "parameter_extraction": ParameterExtractionPrompt(),
        }
    
    def get_prompt(self, tool_name: str, **kwargs) -> str:
        """
        Get a prompt for the specified tool.
        
        Args:
            tool_name: Name of the tool (write_data, read_sql, send_email, parameter_extraction)
            **kwargs: Additional parameters to pass to the prompt (e.g., connections list)
            
        Returns:
            str: The formatted prompt
            
        Raises:
            KeyError: If tool_name is not found
        """
        prompt_provider = self._prompts.get(tool_name)
        if not prompt_provider:
            raise KeyError(f"No prompt found for tool: {tool_name}")
        
        return prompt_provider.get_prompt(**kwargs)
    
    def register_prompt(self, tool_name: str, prompt_provider: PromptProvider) -> None:
        """
        Register a new prompt provider.
        
        Args:
            tool_name: Name of the tool
            prompt_provider: Prompt provider instance
        """
        self._prompts[tool_name] = prompt_provider
    
    def has_prompt(self, tool_name: str) -> bool:
        """
        Check if a prompt exists for the tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            bool: True if prompt exists
        """
        return tool_name in self._prompts
