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
from src.ai.router.prompts.job_agent_conversation_prompt import JobAgentConversationPrompt
from src.ai.router.prompts.parameter_edit_identification_prompt import ParameterEditIdentificationPrompt
from src.ai.router.prompts.router_conversation_prompt import RouterConversationPrompt
from src.ai.router.prompts.sql_generation_prompt import SQLGenerationPrompt

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
