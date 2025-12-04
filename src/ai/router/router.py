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

logger = logging.getLogger(__name__)


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
            
            # Handle initial stages
            if memory.stage == Stage.START:
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
