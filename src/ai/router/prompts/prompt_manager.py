"""
Prompt manager for job parameter extraction.

This module manages prompts for the job agent following SOLID principles:
- Single Responsibility: Only responsible for providing prompts
- Open/Closed: Easy to add new prompts without modifying existing code
"""

from typing import Dict, Protocol
from .job_prompts import WriteDataPrompt, ReadSQLPrompt, SendEmailPrompt, CompareSQLPrompt


class PromptProvider(Protocol):
    """Protocol for prompt providers."""
    
    def get_prompt(self, **kwargs) -> str:
        """Get the formatted prompt."""
        ...





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
            "compare_sql": CompareSQLPrompt(),
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
