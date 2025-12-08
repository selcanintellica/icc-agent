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

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
   - Be flexible with typos and abbreviations (e.g., "drp" → "drop", "trunc" → "truncate")
   - Match the intent even if spelling is imperfect
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS answering a yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing (question will be auto-generated)

Required params:
1. name: Job name (any string the user provides)
2. table: Target table name
3. connection: Database connection (UI shows dropdown)
4. schemas: Schema name (system fetches after connection)
5. drop_or_truncate: "drop", "truncate", or "none" (accept typos: "drp"="drop", "trunc"="truncate", variations like "clear"="truncate", "append"="none")
6. write_count: Track row count? (yes=true, no=false)

{write_count_hint}

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self, connections: str = "", write_count: bool = False) -> str:
        """Get the write_data prompt with conditional hints."""
        write_count_hint = ""
        if write_count:
            write_count_hint = """IF write_count=true, ALSO need:
- write_count_connection: Connection for row count (can be different from main)
- write_count_schema: Schema for row count table
- write_count_table: Table name to store row count"""
        return self.TEMPLATE.format(write_count_hint=write_count_hint)


class ReadSQLPrompt:
    """Prompt for read_sql job parameter extraction."""
    
    TEMPLATE = """Extract params for read_sql job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS they are answering a yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing (question will be auto-generated)

Required params:
- name: Job name (any string the user provides)
- execute_query: Save results to DB? (yes=true, no=false)
- write_count: Track row count? (yes=true, no=false)

{execute_query_hint}

{write_count_hint}

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self, execute_query: bool = False, write_count: bool = False) -> str:
        """Get the read_sql prompt with conditional hints."""
        execute_query_hint = ""
        if execute_query:
            execute_query_hint = """IF execute_query=true, ALSO need:
- result_schema (string): Schema to write query results
- table_name (string): Table name to store query results
- drop_before_create (boolean): Drop table before creating? (yes=true, no=false)"""
        
        write_count_hint = ""
        if write_count:
            write_count_hint = """IF write_count=true, ALSO need:
- write_count_connection (string): Connection for row count (default: same as query connection)
- write_count_schema (string): Schema for row count table
- write_count_table (string): Table name to store row count"""
        
        return self.TEMPLATE.format(execute_query_hint=execute_query_hint, write_count_hint=write_count_hint)


class SendEmailPrompt:
    """Prompt for send_email job parameter extraction."""
    
    TEMPLATE = """Extract params for send_email job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS answering a yes/no question
3. For optional params like CC: if user says "no"/"none"/"skip", set to empty string ""
4. Do NOT invent or assume parameter values
5. Return action="ASK" if any params missing (question will be auto-generated)

Parameters needed:
- name: Job name (any string the user provides, NEVER "ok"/"okay"/"yes"/"no")
- to: Recipient email address
- subject: Email subject line
- text: Email body text (can be empty, but must be provided)
- cc: CC email addresses (optional, can be empty string)

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self) -> str:
        """Get the send_email prompt."""
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
