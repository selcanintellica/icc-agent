"""
LLM Client abstraction - Dependency Inversion Principle
Allows easy swapping of LLM providers without changing business logic.
"""
import os
from abc import ABC, abstractmethod
from typing import List
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def invoke(self, messages: List[BaseMessage]) -> str:
        """
        Send messages to LLM and get response.
        
        Args:
            messages: List of chat messages
            
        Returns:
            LLM response as string
        """
        pass


class OllamaClient(LLMClient):
    """Ollama LLM client implementation."""
    
    def __init__(
        self, 
        model: str = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434",
        num_predict: int = 4096,
        **kwargs
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Model name (e.g., "qwen3:8b")
            temperature: Sampling temperature (0.0-1.0)
            base_url: Ollama server URL
            num_predict: Maximum tokens to generate
            **kwargs: Additional model arguments
        """
        self.model = model or os.getenv("MODEL_NAME", "qwen3:1.7b")
        self.llm = ChatOllama(
            model=self.model,
            temperature=temperature,
            base_url=base_url,
            num_predict=num_predict,
            model_kwargs={
                "think": False,
                "stream": True,
                **kwargs
            }
        )
    
    def invoke(self, messages: List[BaseMessage]) -> str:
        """
        Send messages to Ollama and get response.
        
        Args:
            messages: List of chat messages
            
        Returns:
            LLM response content as string
        """
        response = self.llm.invoke(messages)
        return response.content.strip()


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self, mock_response: str = None):
        """
        Initialize mock client.
        
        Args:
            mock_response: Fixed response to return
        """
        self.mock_response = mock_response or '{"action": "ASK", "question": "Mock question", "params": {}}'
    
    def invoke(self, messages: List[BaseMessage]) -> str:
        """Return mock response."""
        return self.mock_response
