"""
Job agent conversational prompt builder for dynamic context-aware responses.
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
