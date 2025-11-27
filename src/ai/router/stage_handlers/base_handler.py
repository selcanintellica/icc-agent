"""
Base stage handler abstraction.
Implements Single Responsibility Principle - each handler has one job.
"""
from abc import ABC, abstractmethod
from typing import Tuple
from src.ai.router.memory import Memory
import logging

logger = logging.getLogger(__name__)


class StageHandler(ABC):
    """
    Abstract base class for stage handlers.
    Each handler is responsible for processing one conversation stage.
    """
    
    def __init__(self, services: dict = None):
        """
        Initialize handler with injected services.
        
        Args:
            services: Dictionary of service instances (connection_service, schema_service, etc.)
        """
        self.services = services or {}
        self.connection_service = self.services.get("connection_service")
        self.schema_service = self.services.get("schema_service")
        self.auth_service = self.services.get("auth_service")
        self.job_execution_service = self.services.get("job_execution_service")
    
    @abstractmethod
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        """
        Handle the current stage.
        
        Args:
            memory: Current conversation memory
            user_utterance: User's input message
            
        Returns:
            Tuple of (updated memory, response message)
        """
        pass
