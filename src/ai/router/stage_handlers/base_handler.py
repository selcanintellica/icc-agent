"""
Base handler for stage processing.

Defines the interface and common functionality for all stage handlers
following SOLID principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage


@dataclass
class StageHandlerResult:
    """
    Result from a stage handler.
    
    Following the Single Responsibility Principle, this class only
    represents the outcome of stage processing.
    """
    memory: Memory
    response: str
    next_stage: Optional[Stage] = None
    
    def __post_init__(self):
        """Update memory stage if next_stage is provided."""
        if self.next_stage is not None:
            self.memory.stage = self.next_stage


class BaseStageHandler(ABC):
    """
    Abstract base class for stage handlers.
    
    Following SOLID principles:
    - Single Responsibility: Each handler manages one stage type
    - Open/Closed: Easy to extend with new handlers
    - Liskov Substitution: All handlers can be used interchangeably
    - Interface Segregation: Clear, focused interface
    - Dependency Inversion: Depends on abstractions
    """
    
    @abstractmethod
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Args:
            stage: The stage to check
            
        Returns:
            bool: True if this handler can process the stage
        """
        pass
    
    @abstractmethod
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process the stage and return the result.
        
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
        next_stage: Optional[Stage] = None
    ) -> StageHandlerResult:
        """
        Helper to create a stage handler result.
        
        Args:
            memory: Updated memory
            response: Response message
            next_stage: Optional next stage to transition to
            
        Returns:
            StageHandlerResult: The result object
        """
        return StageHandlerResult(
            memory=memory,
            response=response,
            next_stage=next_stage
        )
