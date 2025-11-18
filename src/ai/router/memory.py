"""
Memory and Stage management for the staged conversation router.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class Stage(Enum):
    """Conversation stages for the router."""
    START = "start"
    NEED_QUERY = "need_query"
    HAVE_SQL = "have_sql"
    SHOW_RESULTS = "show_results"
    NEED_WRITE_OR_EMAIL = "need_write_or_email"
    DONE = "done"


@dataclass
class Memory:
    """
    Conversation memory that persists across turns.
    Stores state, last SQL, job results, and any gathered parameters.
    """
    stage: Stage = Stage.START
    last_sql: Optional[str] = None
    last_job_id: Optional[str] = None
    last_columns: Optional[List[str]] = None
    last_preview: Optional[Dict[str, Any]] = None
    gathered_params: Dict[str, Any] = field(default_factory=dict)
    connection: str = "oracle_10"  # Default connection, can be set from UI/config
    
    def reset(self):
        """Reset memory to start a new conversation."""
        self.stage = Stage.START
        self.last_sql = None
        self.last_job_id = None
        self.last_columns = None
        self.last_preview = None
        self.gathered_params = {}
        # Keep connection as it's set externally
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "last_sql": self.last_sql,
            "last_job_id": self.last_job_id,
            "last_columns": self.last_columns,
            "last_preview": self.last_preview,
            "gathered_params": self.gathered_params,
            "connection": self.connection
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create Memory from dictionary."""
        memory = cls()
        memory.stage = Stage(data.get("stage", "start"))
        memory.last_sql = data.get("last_sql")
        memory.last_job_id = data.get("last_job_id")
        memory.last_columns = data.get("last_columns")
        memory.last_preview = data.get("last_preview")
        memory.gathered_params = data.get("gathered_params", {})
        memory.connection = data.get("connection", "oracle_10")
        return memory
