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
    last_job_name: Optional[str] = None  # ReadSQL job name
    last_job_folder: Optional[str] = None  # ReadSQL job folder
    last_columns: Optional[List[str]] = None
    last_preview: Optional[Dict[str, Any]] = None
    gathered_params: Dict[str, Any] = field(default_factory=dict)
    current_tool: Optional[str] = None  # Track which tool we're gathering params for (write_data, send_email, etc)
    last_question: Optional[str] = None  # Track the last question asked to user for context
    execute_query_enabled: bool = False  # Track if ReadSQL executed with execute_query=true (auto-writes data)
    connection: str = "ORACLE_10"  # Connection name, set from UI
    schema: str = "SALES"  # Schema name, set from UI
    selected_tables: List[str] = field(default_factory=lambda: ["customers", "orders"])  # Tables selected from UI
    connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Dynamic connection list from API
    available_schemas: List[str] = field(default_factory=list)  # Cached schema list for selected connection
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """
        Get connection ID from stored connections with fuzzy matching.
        
        Handles cases like:
        - "ORACLE_10" matches "ORACLE_10"
        - "ORACLE_10 (Oracle)" matches "ORACLE_10"
        - "oracle10" matches "ORACLE_10"
        - "oracle_10" matches "ORACLE_10"
        
        Args:
            connection_name: Name of the connection (can include db_type in parentheses)
            
        Returns:
            Connection ID string or None if not found
        """
        if not connection_name:
            return None
        
        # First try exact match
        conn = self.connections.get(connection_name)
        if conn:
            return conn.get("id")
        
        # Remove anything in parentheses (e.g., "ORACLE_10 (Oracle)" -> "ORACLE_10")
        clean_name = connection_name.split("(")[0].strip()
        conn = self.connections.get(clean_name)
        if conn:
            return conn.get("id")
        
        # Try case-insensitive match with underscores removed
        # "oracle10" or "ORACLE10" -> matches "ORACLE_10"
        normalized_input = clean_name.lower().replace("_", "").replace("-", "")
        
        for stored_name, conn_info in self.connections.items():
            normalized_stored = stored_name.lower().replace("_", "").replace("-", "")
            if normalized_input == normalized_stored:
                return conn_info.get("id")
        
        return None
    
    def get_connection_list_for_llm(self) -> str:
        """
        Format connection list for LLM to present to user.
        
        Returns:
            Formatted string with available connections
        """
        if not self.connections:
            return "No connections available."
        
        conn_list = []
        for name, info in self.connections.items():
            db_type = info.get("db_type", "Unknown")
            conn_list.append(f"• {name} ({db_type})")
        
        return "\n".join(conn_list)
    
    def get_schema_list_for_llm(self) -> str:
        """
        Format schema list for LLM to present to user.
        
        Returns:
            Formatted string with available schemas
        """
        if not self.available_schemas:
            return "No schemas available."
        
        # Format schemas in columns for better readability
        schema_list = [f"• {schema}" for schema in self.available_schemas]
        return "\n".join(schema_list)
    
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
        self.last_job_name = None
        self.last_job_folder = None
        self.last_columns = None
        self.last_preview = None
        self.gathered_params = {}
        self.current_tool = None
        self.execute_query_enabled = False
        # Keep connection and connections as they're set externally
    
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
            "last_job_name": self.last_job_name,
            "last_job_folder": self.last_job_folder,
            "last_columns": self.last_columns,
            "last_preview": self.last_preview,
            "gathered_params": self.gathered_params,
            "current_tool": self.current_tool,
            "execute_query_enabled": self.execute_query_enabled,
            "connection": self.connection,
            "schema": self.schema,
            "selected_tables": self.selected_tables,
            "connections": self.connections
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
        memory.last_job_name = data.get("last_job_name")
        memory.last_job_folder = data.get("last_job_folder")
        memory.last_columns = data.get("last_columns")
        memory.last_preview = data.get("last_preview")
        memory.gathered_params = data.get("gathered_params", {})
        memory.current_tool = data.get("current_tool")
        memory.execute_query_enabled = data.get("execute_query_enabled", False)
        memory.connection = data.get("connection", "ORACLE_10")
        memory.schema = data.get("schema", "SALES")
        memory.selected_tables = data.get("selected_tables", ["customers", "orders"])
        memory.connections = data.get("connections", {})
        return memory
