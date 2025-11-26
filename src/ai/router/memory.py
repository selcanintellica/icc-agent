"""
Memory and Stage management for the staged conversation router.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class Stage(Enum):
    """Conversation stages for the router."""
    START = "start"
    
    # New Initial Stage
    ASK_JOB_TYPE = "ask_job_type"
    
    # Read SQL Flow
    ASK_SQL_METHOD = "ask_sql_method"
    NEED_NATURAL_LANGUAGE = "need_natural_language"
    NEED_USER_SQL = "need_user_sql"
    CONFIRM_GENERATED_SQL = "confirm_generated_sql"
    CONFIRM_USER_SQL = "confirm_user_sql"
    EXECUTE_SQL = "execute_sql"
    
    # Compare SQL Flow
    ASK_FIRST_SQL_METHOD = "ask_first_sql_method"
    NEED_FIRST_NATURAL_LANGUAGE = "need_first_natural_language"
    NEED_FIRST_USER_SQL = "need_first_user_sql"
    CONFIRM_FIRST_GENERATED_SQL = "confirm_first_generated_sql"
    CONFIRM_FIRST_USER_SQL = "confirm_first_user_sql"
    
    ASK_SECOND_SQL_METHOD = "ask_second_sql_method"
    NEED_SECOND_NATURAL_LANGUAGE = "need_second_natural_language"
    NEED_SECOND_USER_SQL = "need_second_user_sql"
    CONFIRM_SECOND_GENERATED_SQL = "confirm_second_generated_sql"
    CONFIRM_SECOND_USER_SQL = "confirm_second_user_sql"
    
    ASK_AUTO_MATCH = "ask_auto_match"
    WAITING_MAP_TABLE = "waiting_map_table"
    ASK_REPORTING_TYPE = "ask_reporting_type"
    ASK_COMPARE_SCHEMA = "ask_compare_schema"
    ASK_COMPARE_TABLE_NAME = "ask_compare_table_name"
    ASK_COMPARE_JOB_NAME = "ask_compare_job_name"
    EXECUTE_COMPARE_SQL = "execute_compare_sql"

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
    job_type: str = "readsql"  # readsql or comparesql
    
    last_sql: Optional[str] = None
    first_sql: Optional[str] = None
    second_sql: Optional[str] = None
    
    # Compare SQL specific fields
    first_columns: Optional[List[str]] = None
    second_columns: Optional[List[str]] = None
    column_mappings: Optional[List[Dict[str, str]]] = None  # [{FirstMappedColumn, SecondMappedColumn}]
    key_mappings: Optional[List[Dict[str, str]]] = None  # [{FirstKey, SecondKey}]
    
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
        self.job_type = "readsql"
        self.last_sql = None
        self.first_sql = None
        self.second_sql = None
        self.first_columns = None
        self.second_columns = None
        self.column_mappings = None
        self.key_mappings = None
        self.last_job_id = None
        self.last_columns = None
        self.last_preview = None
        self.gathered_params = {}
        # Keep connection as it's set externally
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "job_type": self.job_type,
            "last_sql": self.last_sql,
            "first_sql": self.first_sql,
            "second_sql": self.second_sql,
            "first_columns": self.first_columns,
            "second_columns": self.second_columns,
            "column_mappings": self.column_mappings,
            "key_mappings": self.key_mappings,
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
        memory.job_type = data.get("job_type", "readsql")
        memory.last_sql = data.get("last_sql")
        memory.first_sql = data.get("first_sql")
        memory.second_sql = data.get("second_sql")
        memory.first_columns = data.get("first_columns")
        memory.second_columns = data.get("second_columns")
        memory.column_mappings = data.get("column_mappings")
        memory.key_mappings = data.get("key_mappings")
        memory.last_job_id = data.get("last_job_id")
        memory.last_columns = data.get("last_columns")
        memory.last_preview = data.get("last_preview")
        memory.gathered_params = data.get("gathered_params", {})
        memory.connection = data.get("connection", "ORACLE_10")
        memory.schema = data.get("schema", "SALES")
        memory.selected_tables = data.get("selected_tables", ["customers", "orders"])
        return memory
