"""
Help handling utility for providing context-aware assistance.

This module provides a centralized help system following SOLID principles:
- Single Responsibility: Only handles help/conversational responses
- Open/Closed: Easy to extend with new help contexts
- Dependency Inversion: Uses abstractions (prompts, LLM)
"""

import logging
from typing import Optional
from langchain_ollama import ChatOllama

from src.ai.router.memory import Memory
from src.ai.router.prompts import RouterConversationPrompt
from src.ai.router.context.stage_context import Stage
from src.errors import ErrorHandler

logger = logging.getLogger(__name__)


def is_help_request(user_input: str) -> bool:
    """
    Detect if user input is requesting help or clarification.
    
    Args:
        user_input: User's input
        
    Returns:
        True if help is requested, False otherwise
    """
    input_lower = user_input.lower().strip()
    
    # Ignore common commands that are valid answers
    commands = [
        "readsql", "comparesql", "create", "provide", "write", "email",
        "done", "both", "new query", "start", "yes", "no", "skip",
        "okay", "ok", "sure", "proceed", "back", "reset", "cancel"
    ]
    if input_lower in commands:
        return False
    
    # Question patterns - must start with these
    question_starters = [
        "what ", "why ", "how ", "when ", "where ", "who ",
        "can you", "could you", "would you", "will you",
        "tell me", "explain", "show me"
    ]
    
    for pattern in question_starters:
        if input_lower.startswith(pattern):
            return True
    
    # Help and confusion indicators (anywhere in text)
    help_phrases = [
        "help", "i don't understand", "i'm confused", "not sure what",
        "i don't know", "i do not know", "don't know what",
        "no idea", "unsure", "what does", "what is", "what are"
    ]
    
    for phrase in help_phrases:
        if phrase in input_lower:
            return True
    
    # Question mark
    if "?" in input_lower:
        return True
    
    return False


class HelpHandler:
    """
    Centralized help handler for providing context-aware assistance.
    
    Following Single Responsibility Principle - only handles help responses.
    """
    
    def __init__(self, llm_model: str = "qwen3:8b"):
        """
        Initialize help handler.
        
        Args:
            llm_model: LLM model to use for help responses
        """
        self.llm_model = llm_model
    
    def _create_llm(self) -> ChatOllama:
        """Create LLM instance for help responses."""
        return ChatOllama(
            model=self.llm_model,
            temperature=0.3,
            num_predict=512,
            timeout=15.0
        )
    
    async def get_help_response(
        self,
        memory: Memory,
        user_input: str
    ) -> str:
        """
        Generate context-aware help response.
        
        Args:
            memory: Current conversation memory
            user_input: User's help request
            
        Returns:
            str: Help response message
        """
        logger.debug(f"Generating help response for stage: {memory.stage.value}")
        
        # Determine if we're in parameter gathering mode
        post_job_stages = {Stage.SHOW_RESULTS, Stage.NEED_WRITE_OR_EMAIL, Stage.DONE}
        in_param_gathering = (
            memory.last_question and 
            memory.gathered_params is not None and 
            memory.stage not in post_job_stages
        )
        
        try:
            if in_param_gathering:
                # Parameter gathering help
                prompt = RouterConversationPrompt.build_param_gathering_context(
                    current_tool=memory.current_tool or "unknown",
                    last_question=memory.last_question or "",
                    gathered_params=memory.gathered_params or {},
                    connection=memory.connection,
                    schema=memory.schema,
                    selected_tables=memory.selected_tables,
                    user_input=user_input
                )
            else:
                # Stage-based help with enhanced context
                stage_desc = self._get_stage_description(memory.stage.value)
                
                # Build enhanced context
                stage_help_text = f"You are currently {stage_desc}."
                
                # Add first_sql context for CompareSQL second query stages
                if "second" in memory.stage.value and hasattr(memory.job_context, 'get'):
                    first_sql = memory.job_context.get("first_sql_query", "")
                    if first_sql:
                        stage_help_text += f"\n\nYou already provided the FIRST SQL query:\n```sql\n{first_sql}\n```"
                        stage_help_text += "\n\nNow you need to provide the SECOND SQL query to compare against the first one."
                
                prompt = RouterConversationPrompt.build_stage_context(
                    stage_value=memory.stage.value,
                    connection=memory.connection,
                    schema=memory.schema,
                    selected_tables=memory.selected_tables,
                    user_input=user_input,
                    stage_specific_help=stage_help_text
                )
            
            llm = self._create_llm()
            response = llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating help response: {e}")
            ErrorHandler.handle(
                e,
                {
                    "context": "help_generation",
                    "stage": memory.stage.value,
                    "tool": memory.current_tool
                }
            )
            
            # Fallback to simple help message
            return self._get_fallback_help(memory)
    
    def _get_stage_description(self, stage_value: str) -> str:
        """
        Get human-readable description for a stage.
        
        Args:
            stage_value: Stage enum value
            
        Returns:
            str: Human-readable stage description
        """
        stage_descriptions = {
            # ReadSQL stages
            "ask_sql_method": "choosing how to provide your SQL query (generate or provide manually)",
            "need_natural_language": "describing what data you want in natural language",
            "need_user_sql": "providing your SQL query",
            "confirm_generated_sql": "confirming the generated SQL query",
            "confirm_user_sql": "confirming your SQL query",
            "execute_sql": "executing the SQL query",
            "show_results": "reviewing query results",
            
            # CompareSQL stages
            "ask_first_sql_method": "choosing how to provide the FIRST SQL query",
            "need_first_natural_language": "describing the FIRST query in natural language",
            "need_first_user_sql": "providing your FIRST SQL query for comparison",
            "confirm_first_generated_sql": "confirming the FIRST generated SQL",
            "confirm_first_user_sql": "confirming your FIRST SQL query",
            
            "ask_second_sql_method": "choosing how to provide the SECOND SQL query",
            "need_second_natural_language": "describing the SECOND query in natural language",
            "need_second_user_sql": "providing your SECOND SQL query for comparison",
            "confirm_second_generated_sql": "confirming the SECOND generated SQL",
            "confirm_second_user_sql": "confirming your SECOND SQL query",
            
            "ask_auto_match": "deciding whether to auto-match columns between queries",
            "waiting_map_table": "providing manual column mappings",
            "ask_reporting_type": "selecting the comparison reporting type",
            "ask_compare_schema": "choosing the schema for comparison results",
            "ask_compare_table_name": "naming the comparison results table",
            "ask_compare_job_name": "naming the comparison job",
            "execute_compare_sql": "executing the comparison",
            
            # Post-execution stages
            "need_write_or_email": "deciding what to do with the results (write to DB or email)",
        }
        
        return stage_descriptions.get(stage_value, f"at stage: {stage_value}")
    
    def _get_fallback_help(self, memory: Memory) -> str:
        """
        Get fallback help message when LLM fails.
        
        Args:
            memory: Current conversation memory
            
        Returns:
            str: Simple fallback help message
        """
        stage_desc = self._get_stage_description(memory.stage.value)
        
        if memory.last_question:
            return f"I'm here to help! Currently {stage_desc}.\n\nThe question is: {memory.last_question}\n\nPlease provide your answer, or type 'back' to go back."
        else:
            return f"I'm here to assist you. Currently {stage_desc}.\n\nLet me know what you need help with, or type 'back' to go back."
