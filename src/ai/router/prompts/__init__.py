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
    ParameterExtractionPrompt,
)

__all__ = [
    "PromptManager",
    "PromptProvider",
    "WriteDataPrompt",
    "ReadSQLPrompt",
    "SendEmailPrompt",
    "ParameterExtractionPrompt",
]
