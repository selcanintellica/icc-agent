"""
Parameter edit identification prompt builder.
"""

from typing import Dict, Any


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
