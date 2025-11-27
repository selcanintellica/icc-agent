"""
SOLID-compliant Router using Dependency Injection and Strategy Pattern.

This refactored router:
- ✅ SRP: Each handler has one responsibility
- ✅ OCP: Add stages by adding handlers (no router modification)
- ✅ LSP: All handlers implement StageHandler interface
- ✅ ISP: Services have focused interfaces
- ✅ DIP: Depends on abstractions, not concrete implementations

Before: 900+ lines monolithic handle_turn() function
After: ~100 lines coordinator using strategy pattern
"""
import logging
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from src.ai.router.stage_handlers import HANDLER_REGISTRY
from src.ai.router.services import (
    ConnectionService,
    ICCConnectionService,
    SchemaService,
    ICCSchemaService,
    AuthService,
    ICCAuthService,
    JobExecutionService,
    ICCJobExecutionService,
)

logger = logging.getLogger(__name__)


class Router:
    """
    Main router class - orchestrates conversation flow using dependency injection.
    
    Uses Strategy Pattern: Each stage has its own handler class.
    Uses Dependency Injection: Services injected for testing/flexibility.
    """
    
    def __init__(
        self,
        connection_service: ConnectionService = None,
        schema_service: SchemaService = None,
        auth_service: AuthService = None,
        job_execution_service: JobExecutionService = None,
    ):
        """
        Initialize router with injected services.
        
        Args:
            connection_service: Service for connection ID lookups
            schema_service: Service for schema fetching
            auth_service: Service for authentication
            job_execution_service: Service for job execution
        """
        # Use defaults if not provided (Dependency Injection)
        self.connection_service = connection_service or ICCConnectionService()
        self.schema_service = schema_service or ICCSchemaService()
        self.auth_service = auth_service or ICCAuthService()
        self.job_execution_service = job_execution_service or ICCJobExecutionService()
        
        # Package services for handlers
        self.services = {
            "connection_service": self.connection_service,
            "schema_service": self.schema_service,
            "auth_service": self.auth_service,
            "job_execution_service": self.job_execution_service,
        }
    
    async def handle_turn(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        """
        Handle one conversational turn by delegating to appropriate stage handler.
        
        This is the ONLY method that needs to know about stages.
        All stage-specific logic is in handler classes (SRP).
        
        Args:
            memory: Current conversation memory
            user_utterance: User's input message
            
        Returns:
            Tuple of (updated memory, response message)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 ROUTER: Stage={memory.stage.value}, Input='{user_utterance[:50]}...'")
        logger.info(f"{'='*60}")
        
        # Get handler for current stage (Strategy Pattern)
        handler_class = HANDLER_REGISTRY.get(memory.stage)
        
        if not handler_class:
            # Fallback if stage not registered
            logger.error(f"❌ No handler registered for stage: {memory.stage}")
            return memory, "I didn't quite catch that. Could you rephrase?"
        
        # Instantiate handler with injected services (DI)
        handler = handler_class(services=self.services)
        
        # Delegate to handler (each handler has single responsibility)
        try:
            return await handler.handle(memory, user_utterance)
        except Exception as e:
            logger.error(f"❌ Error in handler for {memory.stage}: {e}", exc_info=True)
            return memory, f"❌ An error occurred: {str(e)}\nPlease try again."


# Global function for backwards compatibility
async def handle_turn(memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
    """
    Backwards-compatible global function.
    Creates router with default services and delegates to it.
    """
    router = Router()
    return await router.handle_turn(memory, user_utterance)
