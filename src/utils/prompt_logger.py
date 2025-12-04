"""
Utility for logging LLM prompts to file.

Saves all prompts sent to LLMs for analysis and debugging.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptLogger:
    """Logger for LLM prompts."""
    
    def __init__(self, log_dir: str = "prompt_logs"):
        """
        Initialize prompt logger.
        
        Args:
            log_dir: Directory to save prompt logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create session-specific directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.log_dir / f"session_{timestamp}"
        self.session_dir.mkdir(exist_ok=True)
        
        # Also create a combined JSONL file
        self.session_file = self.session_dir / "all_prompts.jsonl"
        self.counter = 0
        
        logger.info(f"Prompt logger initialized: {self.session_dir}")
    
    def log_prompt(
        self,
        agent_type: str,
        system_prompt: str,
        user_prompt: str,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a prompt and response to file.
        
        Args:
            agent_type: Type of agent (sql_agent, job_agent)
            system_prompt: System message content
            user_prompt: User message content
            response: LLM response (optional)
            metadata: Additional metadata (optional)
        """
        self.counter += 1
        
        log_entry = {
            "id": self.counter,
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "full_prompt": f"{system_prompt}\n\n{user_prompt}",
            "response": response,
            "metadata": metadata or {}
        }
        
        try:
            # Save to individual file
            individual_file = self.session_dir / f"{self.counter:04d}_{agent_type}.txt"
            with open(individual_file, "w", encoding="utf-8") as f:
                f.write(f"=" * 80 + "\n")
                f.write(f"PROMPT #{self.counter} - {agent_type.upper()}\n")
                f.write(f"Timestamp: {log_entry['timestamp']}\n")
                f.write(f"=" * 80 + "\n\n")
                
                if metadata:
                    f.write("METADATA:\n")
                    f.write(json.dumps(metadata, indent=2) + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("SYSTEM PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(system_prompt + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("USER PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(user_prompt + "\n\n")
                
                if response:
                    f.write("=" * 80 + "\n")
                    f.write("RESPONSE:\n")
                    f.write("=" * 80 + "\n")
                    f.write(response + "\n")
            
            # Also append to combined JSONL file
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged prompt #{self.counter} to {individual_file}")
            
        except Exception as e:
            logger.error(f"Failed to log prompt: {e}")
    
    def log_full_conversation(
        self,
        agent_type: str,
        messages: list,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a full conversation with multiple messages.
        
        Args:
            agent_type: Type of agent
            messages: List of message objects
            response: LLM response
            metadata: Additional metadata
        """
        self.counter += 1
        
        # Extract system and user messages
        system_msgs = [m.content for m in messages if hasattr(m, 'type') and 'system' in m.type.lower()]
        user_msgs = [m.content for m in messages if hasattr(m, 'type') and 'human' in m.type.lower()]
        
        system_prompt = "\n\n".join(system_msgs) if system_msgs else ""
        user_prompt = "\n\n".join(user_msgs) if user_msgs else ""
        
        log_entry = {
            "id": self.counter,
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "full_prompt": f"{system_prompt}\n\n{user_prompt}",
            "messages": [
                {
                    "type": getattr(m, 'type', 'unknown'),
                    "content": m.content if hasattr(m, 'content') else str(m)
                }
                for m in messages
            ],
            "response": response,
            "metadata": metadata or {}
        }
        
        try:
            # Save to individual file
            individual_file = self.session_dir / f"{self.counter:04d}_{agent_type}.txt"
            with open(individual_file, "w", encoding="utf-8") as f:
                f.write(f"=" * 80 + "\n")
                f.write(f"PROMPT #{self.counter} - {agent_type.upper()}\n")
                f.write(f"Timestamp: {log_entry['timestamp']}\n")
                f.write(f"=" * 80 + "\n\n")
                
                if metadata:
                    f.write("METADATA:\n")
                    f.write(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("SYSTEM PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(system_prompt + "\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("USER PROMPT:\n")
                f.write("=" * 80 + "\n")
                f.write(user_prompt + "\n\n")
                
                if response:
                    f.write("=" * 80 + "\n")
                    f.write("RESPONSE:\n")
                    f.write("=" * 80 + "\n")
                    f.write(response + "\n")
            
            # Also append to combined JSONL file
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged conversation #{self.counter} to {individual_file}")
            
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")


# Global instance
_prompt_logger: Optional[PromptLogger] = None


def get_prompt_logger() -> PromptLogger:
    """Get or create global prompt logger instance."""
    global _prompt_logger
    if _prompt_logger is None:
        _prompt_logger = PromptLogger()
    return _prompt_logger


def enable_prompt_logging(log_dir: str = "prompt_logs") -> None:
    """
    Enable prompt logging globally.
    
    Args:
        log_dir: Directory to save logs
    """
    global _prompt_logger
    _prompt_logger = PromptLogger(log_dir)
    logger.info(f"Prompt logging enabled: {_prompt_logger.session_file}")


def disable_prompt_logging() -> None:
    """Disable prompt logging globally."""
    global _prompt_logger
    _prompt_logger = None
    logger.info("Prompt logging disabled")


def is_prompt_logging_enabled() -> bool:
    """Check if prompt logging is enabled."""
    return _prompt_logger is not None
