"""
Session management service for handling user sessions.

Extracts session-related business logic from app.py following SOLID principles:
- Single Responsibility: Only handles session operations
- Open/Closed: Easy to extend with different storage backends
"""

import logging
from typing import Dict, Optional, Any
from src.ai.router import Memory, create_memory

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions and their associated memory states.
    
    This service encapsulates session storage and retrieval logic,
    making it easy to swap storage backends (e.g., Redis, database)
    without changing the application logic.
    """
    
    def __init__(self, storage: Optional[Dict[str, Memory]] = None):
        """
        Initialize session manager.
        
        Args:
            storage: Optional storage backend. If None, uses in-memory dict.
        """
        self._storage = storage if storage is not None else {}
    
    def get_or_create_session(self, session_id: str) -> Memory:
        """
        Get existing session memory or create new one.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Memory: Session memory object
        """
        if session_id not in self._storage:
            logger.info(f"Creating new session: {session_id}")
            self._storage[session_id] = create_memory()
        else:
            logger.debug(f"Retrieved existing session: {session_id}")
        
        return self._storage[session_id]
    
    def get_session(self, session_id: str) -> Optional[Memory]:
        """
        Get existing session memory without creating new one.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Memory if session exists, None otherwise
        """
        return self._storage.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self._storage
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear/delete a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session was deleted, False if it didn't exist
        """
        if session_id in self._storage:
            del self._storage[session_id]
            logger.info(f"Cleared session: {session_id}")
            return True
        return False
    
    def clear_all_sessions(self) -> int:
        """
        Clear all sessions.
        
        Returns:
            Number of sessions cleared
        """
        count = len(self._storage)
        self._storage.clear()
        logger.info(f"Cleared all {count} sessions")
        return count
    
    def get_session_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self._storage)
    
    def get_session_ids(self) -> list:
        """
        Get list of all session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self._storage.keys())


# Global session manager instance (singleton pattern)
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get or create the global session manager instance.
    
    Returns:
        SessionManager: Global session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        logger.info("Created global SessionManager instance")
    return _session_manager
