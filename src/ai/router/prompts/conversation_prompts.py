"""
Conversational prompt builders for dynamic context-aware responses.

These prompts are built dynamically at runtime with actual conversation context.
"""

from typing import Dict, Any, Optional
import json


class JobAgentConversationPrompt:
    """Builder for job agent conversational prompts."""
    
    @staticmethod
    def build(
        tool_name: str,
        gathered_params: Dict[str, Any],
        last_question: Optional[str],
        user_input: str
    ) -> str:
        """
        Build conversational prompt for job parameter gathering.
        
        Args:
            tool_name: Current tool being configured
            gathered_params: Parameters collected so far
            last_question: Last question asked to user
            user_input: User's conversational input
            
        Returns:
            Formatted prompt string
        """
        return f"""
You are helping the user configure a '{tool_name}' job.

Current progress:
{json.dumps(gathered_params, indent=2)}

Last question asked: {last_question or "(none yet)"}

The user said: "{user_input}"

Respond naturally to their question or comment, then remind them what we're working on and what information you still need.

Be conversational and helpful. After your response, restate the last question or ask the next needed parameter.

Output format:
{{
    "action": "ASK",
    "question": "Your conversational response here...",
    "params": {{}}
}}
"""


class ParameterEditIdentificationPrompt:
    """Builder for parameter edit identification prompts."""
    
    @staticmethod
    def build(user_input: str, params: Dict[str, Any]) -> str:
        """
        Build prompt to identify which parameter user wants to edit.
        
        Args:
            user_input: User's edit request
            params: Current parameters
            
        Returns:
            Formatted prompt string
        """
        param_list = '\n'.join([f"- {key}: {value}" for key, value in params.items()])
        
        return f"""You are helping identify which parameter a user wants to edit.

Current parameters:
{param_list}

User input: "{user_input}"

Identify which parameter the user wants to edit. Respond with ONLY the exact parameter name from the list above, or "NONE" if you cannot determine it.

Examples:
User: "edit job name" → job_name
User: "change the connection" → connection
User: "fix folder" → folder
User: "edit name" → job_name
User: "update execute" → execute_query
User: "change something random" → NONE

Response (parameter name only):"""


class RouterConversationPrompt:
    """Builder for router conversational prompts with stage context."""
    
    @staticmethod
    def build_param_gathering_context(
        current_tool: str,
        last_question: str,
        gathered_params: Dict[str, Any],
        connection: Optional[str],
        schema: Optional[str],
        selected_tables: Optional[list],
        user_input: str
    ) -> str:
        """
        Build conversational prompt for parameter gathering stage.
        
        Args:
            current_tool: Current tool being configured
            last_question: Last question asked
            gathered_params: Parameters collected so far
            connection: Database connection
            schema: Database schema
            selected_tables: Selected tables
            user_input: User's question/input
            
        Returns:
            Formatted prompt string
        """
        param_list = ', '.join(gathered_params.keys()) if gathered_params else 'none yet'
        
        prompt = f"""Currently gathering parameters for '{current_tool}' job.

Last question asked: "{last_question}"

Current parameters collected: {param_list}

Database configuration:"""
        
        if connection:
            prompt += f"\n- Connection: {connection}"
        if schema:
            prompt += f"\n- Schema: {schema}"
        if selected_tables:
            prompt += f"\n- Tables: {', '.join(selected_tables)}"
        
        prompt += f"""

User is asking: "{user_input}"

Provide helpful context-aware guidance about the last question asked. 
Explain what parameter is needed, what the options mean, and how it affects the job.
Be specific and reference the actual database configuration above."""
        
        return prompt
    
    @staticmethod
    def build_stage_context(
        stage_value: str,
        connection: Optional[str],
        schema: Optional[str],
        selected_tables: Optional[list],
        user_input: str,
        **kwargs
    ) -> str:
        """
        Build conversational prompt for stage-based help.
        
        Args:
            stage_value: Current stage name
            connection: Database connection
            schema: Database schema
            selected_tables: Selected tables
            user_input: User's question
            **kwargs: Additional stage-specific context (first_sql, second_sql, etc.)
            
        Returns:
            Formatted prompt string
        """
        stage_context = f"Current stage: {stage_value}"
        
        # Add database configuration context
        if connection or schema or selected_tables:
            stage_context += f"\n\nCurrent database configuration:"
            if connection:
                stage_context += f"\n- Connection: {connection}"
            if schema:
                stage_context += f"\n- Schema: {schema}"
            if selected_tables:
                stage_context += f"\n- Tables: {', '.join(selected_tables)}"
        
        # Add stage-specific context
        if 'stage_specific_help' in kwargs:
            stage_context += f"\n\n{kwargs['stage_specific_help']}"
        
        prompt = f"""{stage_context}

User question/input: "{user_input}"

Respond naturally and helpfully to guide the user based on the context above. 
Be specific about what they need to do at this stage.
Keep it conversational but informative."""
        
        return prompt


class SQLGenerationPrompt:
    """Builder for SQL generation prompts."""
    
    TEMPLATE = """You are a SQL query generator. Convert natural language requests into SQL queries.

You have access to the following database tables with their complete definitions:

{schema_definitions}

IMPORTANT RULES:
- Generate valid SQL queries using ONLY the tables and columns defined above
- Use proper table and column names exactly as shown in the schema
- Pay attention to data types and constraints
- Use JOINs when querying related tables (check Foreign Keys section)
- Be conservative - if unclear, use simple SELECT queries
- Qualify table names with schema if provided (e.g., SALES.customers)
- Only use tables that are listed in the schema above
- Follow the example queries provided for each table as guidance

RESPONSE FORMAT:
Respond with JSON only: {{"sql": "YOUR_SQL_HERE", "reasoning": "brief explanation"}}

Examples of good responses:
{{"sql": "SELECT * FROM customers WHERE country = 'USA'", "reasoning": "Filtering customers by country column"}}
{{"sql": "SELECT c.first_name, c.last_name, SUM(o.total_amount) as total FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name", "reasoning": "Joining customers with orders to calculate total per customer"}}

Now generate SQL for the user's request below:
"""
    
    @staticmethod
    def build(schema_definitions: str) -> str:
        """
        Build SQL generation prompt with schema definitions.
        
        Args:
            schema_definitions: Complete schema definitions
            
        Returns:
            Formatted prompt string
        """
        return SQLGenerationPrompt.TEMPLATE.format(schema_definitions=schema_definitions)
