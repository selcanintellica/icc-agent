"""
Router Orchestrator with comprehensive error handling.

Coordinates stage handlers with proper dependency injection following SOLID principles.
"""

import logging
from typing import Dict, Tuple, Optional, Type
from abc import ABC, abstractmethod

from .memory import Memory, create_memory
from .context.stage_context import Stage
from .stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from .stage_handlers.readsql_handler import ReadSQLHandler
from .stage_handlers.comparesql_handler import CompareSQLHandler
from .stage_handlers.writedata_handler import WriteDataHandler
from .stage_handlers.sendemail_handler import SendEmailHandler
from .sql_agent import create_sql_agent, SQLAgent
from .job_agent import create_job_agent, JobAgent
from src.errors import (
    ICCBaseError,
    ErrorHandler,
    ErrorCode,
    ConfigurationError,
    ValidationError,
)
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def is_conversational_input(user_input: str) -> bool:
    """
    Detect if user input is conversational (question/clarification) vs task answer.
    
    Args:
        user_input: User's input
        
    Returns:
        True if conversational, False if likely task answer
    """
    input_lower = user_input.lower().strip()
    
    # Ignore common commands
    commands = [
        "readsql", "comparesql", "create", "provide", "write", "email",
        "done", "both", "new query", "start", "yes", "no", "skip",
        "okay", "ok", "sure", "proceed"
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


class RouterConfig:
    """
    Configuration for RouterOrchestrator.
    
    Following Dependency Inversion Principle - configuration is injected.
    """
    
    def __init__(
        self,
        sql_agent: Optional[SQLAgent] = None,
        job_agent: Optional[JobAgent] = None
    ):
        """
        Initialize router configuration.
        
        Args:
            sql_agent: SQL agent for query generation
            job_agent: Job agent for parameter gathering
        """
        self.sql_agent = sql_agent or create_sql_agent()
        self.job_agent = job_agent or create_job_agent()


class HandlerRegistry:
    """
    Registry for stage handlers.
    
    Following Open/Closed Principle - easy to add new handlers.
    """
    
    def __init__(self):
        """Initialize handler registry."""
        self._handlers: Dict[str, BaseStageHandler] = {}
    
    def register(self, name: str, handler: BaseStageHandler) -> None:
        """
        Register a handler.
        
        Args:
            name: Handler identifier
            handler: Handler instance
        """
        self._handlers[name] = handler
        logger.debug(f"Registered handler: {name}")
    
    def get_handler(self, stage: Stage, memory: Memory) -> Optional[BaseStageHandler]:
        """
        Get appropriate handler for current stage.
        
        Uses memory.current_tool to disambiguate when multiple handlers
        claim the same stage (e.g., NEED_WRITE_OR_EMAIL).
        
        Args:
            stage: Current stage
            memory: Current memory
            
        Returns:
            Handler that can handle the stage, or None
        """
        # Special handling for NEED_WRITE_OR_EMAIL - use current_tool to disambiguate
        if stage == Stage.NEED_WRITE_OR_EMAIL:
            if memory.current_tool == "write_data":
                logger.debug(f"Routing NEED_WRITE_OR_EMAIL to WriteDataHandler (current_tool={memory.current_tool})")
                return self._handlers.get("writedata")
            elif memory.current_tool == "send_email":
                logger.debug(f"Routing NEED_WRITE_OR_EMAIL to SendEmailHandler (current_tool={memory.current_tool})")
                return self._handlers.get("sendemail")
            else:
                # Default to ReadSQLHandler for initial routing decision
                logger.debug(f"Routing NEED_WRITE_OR_EMAIL to ReadSQLHandler (current_tool={memory.current_tool})")
                return self._handlers.get("readsql")
        
        # For other stages, return first handler that can handle it
        for handler in self._handlers.values():
            if handler.can_handle(stage):
                return handler
        return None
    
    def list_handlers(self) -> list:
        """List all registered handler names."""
        return list(self._handlers.keys())


class RouterOrchestrator:
    """
    Main router orchestrator with proper dependency injection and error handling.
    
    Following SOLID principles:
    - Single Responsibility: Orchestrates handlers, delegates work
    - Open/Closed: Easy to add new handlers via registry
    - Liskov Substitution: All handlers implement BaseStageHandler
    - Interface Segregation: Handlers have focused interface
    - Dependency Inversion: Depends on abstractions (BaseStageHandler, agents)
    """
    
    def __init__(
        self,
        config: RouterConfig,
        handler_registry: Optional[HandlerRegistry] = None
    ):
        """
        Initialize router orchestrator.
        
        Args:
            config: Router configuration with dependencies
            handler_registry: Handler registry (creates default if None)
        """
        self.config = config
        self.registry = handler_registry or self._create_default_registry()
    
    def _create_default_registry(self) -> HandlerRegistry:
        """
        Create default handler registry with all handlers.
        
        Returns:
            HandlerRegistry: Configured registry
        """
        registry = HandlerRegistry()
        
        # Register ReadSQL handler
        registry.register(
            "readsql",
            ReadSQLHandler(
                sql_agent=self.config.sql_agent,
                job_agent=self.config.job_agent
            )
        )
        
        # Register CompareSQL handler
        registry.register(
            "comparesql",
            CompareSQLHandler(
                sql_agent=self.config.sql_agent,
                job_agent=self.config.job_agent
            )
        )
        
        # Register WriteData handler
        registry.register(
            "writedata",
            WriteDataHandler(
                job_agent=self.config.job_agent
            )
        )
        
        # Register SendEmail handler
        registry.register(
            "sendemail",
            SendEmailHandler(
                job_agent=self.config.job_agent
            )
        )
        
        return registry
    
    def _handle_conversational_input(self, memory: Memory, user_input: str) -> str:
        """
        Handle conversational input like questions or help requests.
        
        Args:
            memory: Current conversation memory
            user_input: User's conversational input
            
        Returns:
            Conversational response
        """
        logger.info(f"💬 Detected conversational input: '{user_input}'")
        
        # Build context for conversational response
        stage_context = f"Current stage: {memory.stage.value}"
        
        # Add stage-specific context
        if memory.stage == Stage.ASK_SQL_METHOD:
            stage_context += "\n\nThe user needs to choose between:\n- 'create' - I'll generate SQL from natural language\n- 'provide' - User provides SQL directly"
        elif memory.stage == Stage.ASK_JOB_TYPE:
            stage_context += "\n\nThe user needs to choose between:\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries"
        elif memory.stage == Stage.NEED_WRITE_OR_EMAIL:
            if memory.execute_query_enabled:
                stage_context += "\n\nData was written. User can:\n- 'email' - Send results via email\n- 'done' - Finish"
            else:
                stage_context += "\n\nQuery complete. User can:\n- 'write' - Save results to table\n- 'done' - Finish"
        
        prompt = f"""{stage_context}

User question/input: "{user_input}"

Respond naturally and helpfully to guide the user. Keep it brief and friendly."""
        
        try:
            # Use a simple LLM call for conversational response
            llm = ChatOllama(
                model="qwen3:8b",
                temperature=0.3,
                num_predict=512,
                timeout=15.0
            )
            response = llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error in conversational handler: {e}")
            # Fallback to a helpful default
            return f"I'm here to help! {stage_context.split('User needs to choose')[1] if 'User needs to choose' in stage_context else 'Let me know how I can assist you.'}"
    
    async def handle_turn(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        """
        Handle one conversational turn with comprehensive error handling.
        
        Args:
            memory: Current conversation memory
            user_utterance: User's input message
            
        Returns:
            Tuple of (updated memory, response message)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ROUTER: Stage={memory.stage.value}, Input='{user_utterance[:50]}...'")
        logger.info(f"{'='*60}")
        
        try:
            # Validate input
            if user_utterance is None:
                user_utterance = ""
            
            # Check for conversational input (help, questions, etc.)
            if user_utterance and is_conversational_input(user_utterance):
                response = self._handle_conversational_input(memory, user_utterance)
                return memory, response
            
            # Handle initial stages
            if memory.stage == Stage.START:
                # First interaction - greet and move to ASK_JOB_TYPE
                # The welcome message is shown from app.py, so just transition
                memory.stage = Stage.ASK_JOB_TYPE
                return memory, "How would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries"
            
            # Handle restart from DONE stage
            if memory.stage == Stage.DONE:
                user_lower = user_utterance.lower().strip()
                if any(word in user_lower for word in ["new", "start", "begin", "restart", "fresh"]):
                    logger.info("🔄 User requested fresh start, resetting memory...")
                    # Reset memory to fresh state
                    memory.reset()
                    memory.stage = Stage.ASK_JOB_TYPE
                    return memory, "Starting fresh!\n\nHow would you like to proceed?\n- 'readsql' - Execute a single SQL query\n- 'comparesql' - Compare two SQL queries"
                else:
                    return memory, "I'm in DONE state. Say 'new query' or 'start' to create another job."
            
            if memory.stage == Stage.ASK_JOB_TYPE:
                return await self._handle_job_type_selection(memory, user_utterance)
            
            # Delegate to appropriate handler
            handler = self.registry.get_handler(memory.stage, memory)
            
            if handler:
                logger.info(f"🎯 Delegating to handler: {handler.__class__.__name__}")
                logger.info(f"🎯 Memory state before handler: stage={memory.stage.value}, current_tool={memory.current_tool}, gathered_params={list(memory.gathered_params.keys())}")
                
                result = await handler.handle(memory, user_utterance)
                
                if result:
                    logger.info(f"🎯 Handler result: next_stage={result.next_stage.value if result.next_stage else 'None'}, is_error={result.is_error}")
                    
                    # Log if this was an error response
                    if result.is_error:
                        logger.warning(f"⚠️ Handler returned error: {result.error_code or 'unknown'}")
                    
                    # Check for delegation markers
                    if result.response == "__DELEGATE_TO_WRITEDATA__":
                        logger.info("🔄 Detected delegation to WriteDataHandler")
                        writedata_handler = self.registry._handlers.get("writedata")
                        if writedata_handler:
                            logger.info(f"📝 Calling WriteDataHandler with input: '{user_utterance}'")
                            result = await writedata_handler.handle(memory, user_utterance)
                            logger.info(f"📝 WriteDataHandler returned: next_stage={result.next_stage.value if result.next_stage else 'None'}")
                            return result.memory, result.response
                        else:
                            logger.error("❌ WriteDataHandler not found in registry!")
                            return memory, "Unable to process write request. Please try again."
                    
                    elif result.response == "__DELEGATE_TO_SENDEMAIL__":
                        logger.info("🔄 Detected delegation to SendEmailHandler")
                        sendemail_handler = self.registry._handlers.get("sendemail")
                        if sendemail_handler:
                            logger.info(f"📧 Calling SendEmailHandler with input: '{user_utterance}'")
                            result = await sendemail_handler.handle(memory, user_utterance)
                            logger.info(f"📧 SendEmailHandler returned: next_stage={result.next_stage.value if result.next_stage else 'None'}")
                            return result.memory, result.response
                        else:
                            logger.error("❌ SendEmailHandler not found in registry!")
                            return memory, "Unable to process email request. Please try again."
                    
                    return result.memory, result.response
                else:
                    logger.warning(f"Handler returned None for stage {memory.stage.value}")
                    return memory, "I'm not sure how to proceed. Could you rephrase your request?"
            
            # No handler found
            logger.warning(f"No handler found for stage: {memory.stage.value}")
            return memory, "I'm not sure how to proceed. Could you rephrase your request?"
            
        except ICCBaseError as e:
            logger.error(f"ICC error in router: {e}")
            return memory, f"Error: {e.user_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error in router: {type(e).__name__}: {str(e)}", exc_info=True)
            # Convert to user-friendly message
            icc_error = ErrorHandler.handle(e, {"stage": memory.stage.value, "input": user_utterance[:50]})
            return memory, f"Error: {icc_error.user_message}"
    
    async def _handle_job_type_selection(
        self,
        memory: Memory,
        user_utterance: str
    ) -> Tuple[Memory, str]:
        """
        Handle job type selection stage.
        
        Args:
            memory: Current memory
            user_utterance: User input
            
        Returns:
            Tuple of (updated memory, response)
        """
        user_lower = user_utterance.lower()
        
        if any(word in user_lower for word in ["compare", "comparesql", "diff", "difference"]):
            logger.info("User chose: COMPARE SQL")
            memory.job_type = "comparesql"
            memory.stage = Stage.ASK_FIRST_SQL_METHOD
            return memory, (
                "For the FIRST query, how would you like to proceed?\n"
                "- 'create' - I'll generate SQL from your description\n"
                "- 'provide' - You provide the SQL query directly"
            )
        
        elif any(word in user_lower for word in ["read", "readsql", "query", "select", "get"]):
            logger.info("User chose: READ SQL")
            memory.job_type = "readsql"
            memory.stage = Stage.ASK_SQL_METHOD
            return memory, (
                "How would you like to proceed?\n"
                "- 'create' - I'll generate SQL from your natural language description\n"
                "- 'provide' - You provide the SQL query directly"
            )
        
        else:
            return memory, (
                "Please choose one of the following:\n"
                "- 'readsql' - Execute a single SQL query\n"
                "- 'comparesql' - Compare two SQL queries"
            )
    
    def add_handler(self, name: str, handler: BaseStageHandler) -> None:
        """
        Add a new handler to the registry.
        
        Args:
            name: Handler identifier
            handler: Handler instance
        """
        self.registry.register(name, handler)


# Factory function for creating router orchestrator
def create_router_orchestrator(
    sql_agent: Optional[SQLAgent] = None,
    job_agent: Optional[JobAgent] = None
) -> RouterOrchestrator:
    """
    Create a RouterOrchestrator with default configuration.
    
    Args:
        sql_agent: Optional SQL agent (creates default if None)
        job_agent: Optional job agent (creates default if None)
        
    Returns:
        RouterOrchestrator: Configured orchestrator
    """
    config = RouterConfig(sql_agent=sql_agent, job_agent=job_agent)
    return RouterOrchestrator(config)


# Create singleton agents to reuse LLM instances across all requests
_default_sql_agent = None
_default_job_agent = None
_default_router_orchestrator = None


def get_default_agents() -> tuple:
    """
    Get or create singleton agents with persistent LLM instances.
    
    Returns:
        tuple: (sql_agent, job_agent)
    """
    global _default_sql_agent, _default_job_agent
    
    if _default_sql_agent is None:
        logger.info("🏗️ Creating singleton SQL agent...")
        _default_sql_agent = create_sql_agent()
        logger.info(f"✅ SQL agent created (id: {id(_default_sql_agent)})")
    
    if _default_job_agent is None:
        logger.info("🏗️ Creating singleton Job agent...")
        _default_job_agent = create_job_agent()
        logger.info(f"✅ Job agent created (id: {id(_default_job_agent)})")
    
    return _default_sql_agent, _default_job_agent


def get_default_router_orchestrator() -> RouterOrchestrator:
    """
    Get or create the default router orchestrator singleton.
    
    This ensures LLM instances are reused across requests, keeping them loaded in memory
    and respecting the keep_alive setting.
    
    Returns:
        RouterOrchestrator: Singleton router instance
    """
    global _default_router_orchestrator
    if _default_router_orchestrator is None:
        logger.info("🏗️ Creating singleton router orchestrator...")
        # Get singleton agents to ensure LLM instances are reused
        sql_agent, job_agent = get_default_agents()
        _default_router_orchestrator = create_router_orchestrator(
            sql_agent=sql_agent,
            job_agent=job_agent
        )
        logger.info(f"✅ Created singleton router orchestrator (id: {id(_default_router_orchestrator)})")
    else:
        logger.debug(f"♻️ Reusing existing router orchestrator (id: {id(_default_router_orchestrator)})")
    return _default_router_orchestrator


# Backward compatibility wrapper
async def handle_turn(memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
    """
    Backward compatibility wrapper for handle_turn.
    
    Uses singleton router orchestrator to maintain persistent LLM instances.
    
    Args:
        memory: Current conversation memory
        user_utterance: User's input message
        
    Returns:
        Tuple of (updated memory, response message)
    """
    orchestrator = get_default_router_orchestrator()
    return await orchestrator.handle_turn(memory, user_utterance)
