"""
Prompts package for router job agent.

This package provides prompt management for job parameter extraction.
"""

from src.ai.router.prompts.prompt_manager import (
    PromptManager,
    PromptProvider,
    WriteDataPrompt,
    ReadSQLPrompt,
    SendEmailPrompt,
)
from src.ai.router.prompts.conversation_prompts import (
    JobAgentConversationPrompt,
    ParameterEditIdentificationPrompt,
    RouterConversationPrompt,
    SQLGenerationPrompt,
)

__all__ = [
    "PromptManager",
    "PromptProvider",
    "WriteDataPrompt",
    "ReadSQLPrompt",
    "SendEmailPrompt",
    "JobAgentConversationPrompt",
    "ParameterEditIdentificationPrompt",
    "RouterConversationPrompt",
    "SQLGenerationPrompt",
]
