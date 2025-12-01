"""
Job Context.

Handles job execution state and results following Single Responsibility Principle.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class JobContext:
    """
    Manages job execution state and results.
    
    Following SRP - only responsible for job-related state.
    """
    
    # Job type
    job_type: str = "readsql"  # readsql or comparesql
    
    # SQL queries
    last_sql: Optional[str] = None
    first_sql: Optional[str] = None  # For CompareSQL
    second_sql: Optional[str] = None  # For CompareSQL
    
    # Job execution results
    last_job_id: Optional[str] = None
    last_job_name: Optional[str] = None  # ReadSQL job name
    last_job_folder: Optional[str] = None  # ReadSQL job folder
    last_columns: Optional[List[str]] = None
    last_preview: Optional[Dict[str, Any]] = None
    
    # CompareSQL specific fields
    first_columns: Optional[List[str]] = None
    second_columns: Optional[List[str]] = None
    column_mappings: Optional[List[Dict[str, str]]] = None  # [{FirstMappedColumn, SecondMappedColumn}]
    key_mappings: Optional[List[Dict[str, str]]] = None  # [{FirstKey, SecondKey}]
    
    # Parameter gathering
    gathered_params: Dict[str, Any] = field(default_factory=dict)
    current_tool: Optional[str] = None  # Track which tool we're gathering params for
    
    # Execution flags
    execute_query_enabled: bool = False  # Track if ReadSQL executed with execute_query=true
    
    # Output table info for send_email query generation
    # Stores schema and table where data was written (by execute_query, write_data, or compare_sql)
    output_table_info: Optional[Dict[str, str]] = None
    
    # SendEmail pending state (for query confirmation flow)
    pending_email_params: Optional[Dict[str, Any]] = None
    email_query_confirmed: bool = False
    
    # UI selections
    selected_tables: List[str] = field(default_factory=lambda: ["customers", "orders"])
    
    def reset(self) -> None:
        """Reset job context for new conversation."""
        self.job_type = "readsql"
        self.last_sql = None
        self.first_sql = None
        self.second_sql = None
        self.last_job_id = None
        self.last_job_name = None
        self.last_job_folder = None
        self.last_columns = None
        self.last_preview = None
        self.first_columns = None
        self.second_columns = None
        self.column_mappings = None
        self.key_mappings = None
        self.gathered_params = {}
        self.current_tool = None
        self.execute_query_enabled = False
        self.output_table_info = None
        self.pending_email_params = None
        self.email_query_confirmed = False
    
    def set_read_sql_result(
        self,
        job_id: str,
        columns: List[str],
        job_name: Optional[str] = None,
        job_folder: Optional[str] = None
    ) -> None:
        """
        Set results from ReadSQL job execution.
        
        Args:
            job_id: Job ID from execution
            columns: Column names from result
            job_name: Name of the job
            job_folder: Folder where job is stored
        """
        self.last_job_id = job_id
        self.last_columns = columns
        if job_name:
            self.last_job_name = job_name
        if job_folder:
            self.last_job_folder = job_folder
    
    def set_compare_sql_columns(
        self,
        first_columns: List[str],
        second_columns: List[str]
    ) -> None:
        """
        Set columns for CompareSQL job.
        
        Args:
            first_columns: Columns from first query
            second_columns: Columns from second query
        """
        self.first_columns = first_columns
        self.second_columns = second_columns
    
    def add_gathered_param(self, key: str, value: Any) -> None:
        """
        Add a gathered parameter.
        
        Args:
            key: Parameter key
            value: Parameter value
        """
        self.gathered_params[key] = value
    
    def get_gathered_param(self, key: str, default: Any = None) -> Any:
        """
        Get a gathered parameter.
        
        Args:
            key: Parameter key
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        return self.gathered_params.get(key, default)
    
    def clear_gathered_params(self) -> None:
        """Clear all gathered parameters."""
        self.gathered_params = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_type": self.job_type,
            "last_sql": self.last_sql,
            "first_sql": self.first_sql,
            "second_sql": self.second_sql,
            "last_job_id": self.last_job_id,
            "last_job_name": self.last_job_name,
            "last_job_folder": self.last_job_folder,
            "last_columns": self.last_columns,
            "last_preview": self.last_preview,
            "first_columns": self.first_columns,
            "second_columns": self.second_columns,
            "column_mappings": self.column_mappings,
            "key_mappings": self.key_mappings,
            "gathered_params": self.gathered_params,
            "current_tool": self.current_tool,
            "execute_query_enabled": self.execute_query_enabled,
            "selected_tables": self.selected_tables,
            "output_table_info": self.output_table_info,
            "pending_email_params": self.pending_email_params,
            "email_query_confirmed": self.email_query_confirmed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobContext":
        """Create JobContext from dictionary."""
        return cls(
            job_type=data.get("job_type", "readsql"),
            last_sql=data.get("last_sql"),
            first_sql=data.get("first_sql"),
            second_sql=data.get("second_sql"),
            last_job_id=data.get("last_job_id"),
            last_job_name=data.get("last_job_name"),
            last_job_folder=data.get("last_job_folder"),
            last_columns=data.get("last_columns"),
            last_preview=data.get("last_preview"),
            first_columns=data.get("first_columns"),
            second_columns=data.get("second_columns"),
            column_mappings=data.get("column_mappings"),
            key_mappings=data.get("key_mappings"),
            gathered_params=data.get("gathered_params", {}),
            current_tool=data.get("current_tool"),
            execute_query_enabled=data.get("execute_query_enabled", False),
            selected_tables=data.get("selected_tables", ["customers", "orders"]),
            output_table_info=data.get("output_table_info"),
            pending_email_params=data.get("pending_email_params"),
            email_query_confirmed=data.get("email_query_confirmed", False)
        )
