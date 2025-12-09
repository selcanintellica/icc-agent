"""
Stage strategy pattern for handling individual stages.

This refactoring follows SOLID principles by:
- Single Responsibility: Each strategy handles ONE stage's logic
- Open/Closed: Easy to add new stage strategies without modifying handlers
- Liskov Substitution: All strategies are interchangeable
- Interface Segregation: Clear, focused interface for stage processing
- Dependency Inversion: Handlers depend on strategy abstraction
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional

from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.stage_handlers.base_handler import StageHandlerResult
from src.ai.router.utils.help_handler import HelpHandler, is_help_request

logger = logging.getLogger(__name__)


class StageStrategy(ABC):
    """
    Abstract base class for individual stage processing strategies.
    
    Each concrete strategy encapsulates the logic for handling
    a specific stage, making the codebase more modular and testable.
    """
    
    def __init__(self):
        """Initialize strategy with help handler."""
        self._help_handler = HelpHandler()
    
    async def handle_with_help(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle user input with automatic help detection.
        
        This is the main entry point that checks for help requests
        before delegating to the strategy's execute method.
        
        Args:
            memory: Current conversation memory
            user_input: User's input message
            
        Returns:
            StageHandlerResult: Result with updated memory and response
        """
        # Check if user is requesting help
        if is_help_request(user_input):
            logger.debug(f"Help request detected in stage {memory.stage.value}")
            try:
                help_response = await self._help_handler.get_help_response(memory, user_input)
                return self._create_result(memory, help_response)
            except Exception as e:
                logger.error(f"Error handling help request: {e}")
                # Fall through to normal execution if help fails
        
        # Normal execution
        return await self.execute(memory, user_input)
    
    @abstractmethod
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Execute the stage-specific logic.
        
        Subclasses implement this method with their stage-specific logic.
        This method is called after help detection.
        
        Args:
            memory: Current conversation memory
            user_input: User's input message
            
        Returns:
            StageHandlerResult: Result with updated memory and response
        """
        pass
    
    def _create_result(
        self,
        memory: Memory,
        response: str,
        next_stage: Optional[Stage] = None,
        is_error: bool = False,
        error_code: Optional[str] = None
    ) -> StageHandlerResult:
        """
        Helper to create a StageHandlerResult.
        
        Args:
            memory: Current memory state
            response: Response message
            next_stage: Next stage to transition to (optional)
            is_error: Whether this is an error response
            error_code: Error code if applicable
            
        Returns:
            StageHandlerResult: Configured result object
        """
        return StageHandlerResult(
            memory=memory,
            response=response,
            next_stage=next_stage,
            is_error=is_error,
            error_code=error_code
        )
    
    def _check_navigation_commands(self, user_input: str) -> Optional[str]:
        """
        Check if user input is a navigation command (back/reset).
        
        Args:
            user_input: User's input
            
        Returns:
            Optional[str]: 'back', 'reset', or None if not a navigation command
        """
        user_lower = user_input.lower().strip()
        if user_lower in ["back", "go back", "previous"]:
            return "back"
        elif user_lower in ["reset", "start over", "cancel", "restart"]:
            return "reset"
        return None


class StageStrategyRegistry:
    """
    Registry for managing stage strategies.
    
    Follows the Registry pattern to decouple stage handlers from
    specific strategy implementations.
    """
    
    def __init__(self):
        """Initialize empty strategy registry."""
        self._strategies: Dict[Stage, StageStrategy] = {}
    
    def register(self, stage: Stage, strategy: StageStrategy) -> None:
        """
        Register a strategy for a specific stage.
        
        Args:
            stage: The stage this strategy handles
            strategy: The strategy instance
        """
        logger.debug(f"Registering strategy for stage {stage.value}")
        self._strategies[stage] = strategy
    
    def get_strategy(self, stage: Stage) -> Optional[StageStrategy]:
        """
        Get the strategy for a specific stage.
        
        Args:
            stage: The stage to get strategy for
            
        Returns:
            Optional[StageStrategy]: Strategy instance or None if not found
        """
        return self._strategies.get(stage)
    
    def has_strategy(self, stage: Stage) -> bool:
        """
        Check if a strategy exists for a stage.
        
        Args:
            stage: The stage to check
            
        Returns:
            bool: True if strategy exists
        """
        return stage in self._strategies
    
    def clear(self) -> None:
        """Clear all registered strategies."""
        self._strategies.clear()
    
    def get_all_stages(self) -> set:
        """
        Get all stages that have registered strategies.
        
        Returns:
            set: Set of Stage enums with strategies
        """
        return set(self._strategies.keys())
