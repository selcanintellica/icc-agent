"""
Prompts module for ICC Agent.

This module provides prompt templates following SOLID principles:
- Single Responsibility: Each prompt class handles one type of prompt
- Open/Closed: Easy to extend with new prompts without modifying existing code
- Interface Segregation: Separate interfaces for different prompt types
"""

from typing import Protocol


class PromptProvider(Protocol):
    """Protocol defining the interface for prompt providers."""
    
    def get_prompt(self) -> str:
        """Returns the prompt template string."""
        ...


class ICCPrompt:
    """Provides the main ICC agent prompt template."""
    
    _prompt_template = """You are an intelligent assistant for the ICC system.
Your role is to help users with data queries, job management, and system operations.

Available tools and capabilities:
- Query data from various connections
- Manage jobs and schedules
- Retrieve connection information
- Execute SQL queries

When responding:
1. Understand the user's intent clearly
2. Use appropriate tools to gather information
3. Provide clear, accurate responses
4. If unsure, ask for clarification

Be helpful, accurate, and efficient in your responses."""
    
    def get_prompt(self) -> str:
        """Returns the ICC agent prompt template."""
        return self._prompt_template


class Prompts:
    """Central registry for all prompts in the system."""
    
    icc_prompt = ICCPrompt().get_prompt()
