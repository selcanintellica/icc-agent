"""
Router Orchestrator.

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
        
        Args:
            stage: Current stage
            memory: Current memory
            
        Returns:
            Handler that can handle the stage, or None
        """
        for handler in self._handlers.values():
            if handler.can_handle(stage):
                return handler
        return None
    
    def list_handlers(self) -> list:
        """List all registered handler names."""
        return list(self._handlers.keys())


class RouterOrchestrator:
    """
    Main router orchestrator with proper dependency injection.
    
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
        Handle one conversational turn.
        
        Args:
            memory: Current conversation memory
            user_utterance: User's input message
            
        Returns:
            Tuple of (updated memory, response message)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 ROUTER: Stage={memory.stage.value}, Input='{user_utterance[:50]}...'")
        logger.info(f"{'='*60}")
        
        # Handle initial stages
        if memory.stage == Stage.START:
            memory.stage = Stage.ASK_JOB_TYPE
            return memory, "How would you like to proceed? 'readsql' or 'comparesql'?"
        
        if memory.stage == Stage.ASK_JOB_TYPE:
            return await self._handle_job_type_selection(memory, user_utterance)
        
        # Delegate to appropriate handler
        handler = self.registry.get_handler(memory.stage, memory)
        
        if handler:
            logger.info(f"📋 Delegating to handler: {handler.__class__.__name__}")
            result = await handler.handle(memory, user_utterance)
            
            if result:
                # Check for delegation markers
                if result.response == "__DELEGATE_TO_WRITEDATA__":
                    logger.info("🔄 Detected delegation to WriteDataHandler")
                    writedata_handler = self.registry._handlers.get("writedata")
                    if writedata_handler:
                        result = await writedata_handler.handle(memory, user_utterance)
                        return result.memory, result.response
                    else:
                        return memory, "❌ Error: WriteDataHandler not available."
                
                elif result.response == "__DELEGATE_TO_SENDEMAIL__":
                    logger.info("🔄 Detected delegation to SendEmailHandler")
                    sendemail_handler = self.registry._handlers.get("sendemail")
                    if sendemail_handler:
                        result = await sendemail_handler.handle(memory, user_utterance)
                        return result.memory, result.response
                    else:
                        return memory, "❌ Error: SendEmailHandler not available."
                
                return result.memory, result.response
            else:
                logger.warning(f"⚠️ Handler returned None for stage {memory.stage.value}")
                return memory, "I'm not sure how to proceed. Could you rephrase?"
        
        # No handler found
        logger.warning(f"⚠️ No handler found for stage: {memory.stage.value}")
        return memory, "I'm not sure how to proceed. Could you rephrase?"
    
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
        
        if "compare" in user_lower:
            logger.info("📝 User chose: COMPARE SQL")
            memory.job_type = "comparesql"
            memory.stage = Stage.ASK_FIRST_SQL_METHOD
            return memory, "For the FIRST query, how would you like to proceed?\n• Type 'create' - I'll generate SQL\n• Type 'provide' - You provide the SQL"
        
        elif "read" in user_lower:
            logger.info("📝 User chose: READ SQL")
            memory.job_type = "readsql"
            memory.stage = Stage.ASK_SQL_METHOD
            return memory, "How would you like to proceed?\n• Type 'create' - I'll generate SQL from your natural language\n• Type 'provide' - You provide the SQL query directly"
        
        else:
            return memory, "Please choose: 'readsql' or 'comparesql'"
    
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


# Backward compatibility wrapper
async def handle_turn(memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
    """
    Backward compatibility wrapper for handle_turn.
    
    Creates a router orchestrator and delegates to it.
    
    Args:
        memory: Current conversation memory
        user_utterance: User's input message
        
    Returns:
        Tuple of (updated memory, response message)
    """
    orchestrator = create_router_orchestrator()
    return await orchestrator.handle_turn(memory, user_utterance)
