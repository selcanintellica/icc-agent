"""
Router conversational prompt builder with stage context.
"""

from typing import Dict, Any, Optional


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
