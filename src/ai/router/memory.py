"""
Memory and Stage management for the staged conversation router.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class Stage(Enum):
    """Conversation stages for the router."""
    START = "start"
    ASK_SQL_METHOD = "ask_sql_method"          # NEW: Ask if user provides SQL or wants it generated
    NEED_NATURAL_LANGUAGE = "need_natural_language"  # NEW: Waiting for NL query to generate SQL
    NEED_USER_SQL = "need_user_sql"            # NEW: Waiting for user to provide SQL directly
    CONFIRM_GENERATED_SQL = "confirm_generated_sql"  # NEW: Show generated SQL, ask for confirmation
    CONFIRM_USER_SQL = "confirm_user_sql"      # NEW: Show user's SQL, ask for confirmation
    EXECUTE_SQL = "execute_sql"                # Ready to execute (replaces HAVE_SQL)
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
    connection: str = "ORACLE_10"  # Connection name, set from UI
    schema: str = "SALES"  # Schema name, set from UI
    selected_tables: List[str] = field(default_factory=lambda: ["customers", "orders"])  # Tables selected from UI
    
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
            "connection": self.connection,
            "schema": self.schema,
            "selected_tables": self.selected_tables
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
        memory.connection = data.get("connection", "ORACLE_10")
        memory.schema = data.get("schema", "SALES")
        memory.selected_tables = data.get("selected_tables", ["customers", "orders"])
        return memory
