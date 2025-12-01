"""
Refactored Memory using composition following SOLID principles.

This module provides a Memory class that composes:
- ConnectionManager: Handles connection-related operations
- JobContext: Manages job execution state
- StageContext: Handles conversation stage flow

Following SOLID principles:
- Single Responsibility: Each component has one responsibility
- Open/Closed: Easy to extend with new components
- Dependency Inversion: Memory depends on abstractions
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .context import ConnectionManager, JobContext, StageContext
from .context.stage_context import Stage


@dataclass
class Memory:
    """
    Refactored conversation memory using composition.
    
    Composes three focused components:
    - connection_manager: Handles connections and schemas
    - job_context: Manages job state and results
    - stage_context: Tracks conversation flow
    
    Following SOLID principles - Memory is now a facade that delegates
    to specialized components instead of handling everything itself.
    """
    
    connection_manager: ConnectionManager
    job_context: JobContext
    stage_context: StageContext
    
    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
        job_context: Optional[JobContext] = None,
        stage_context: Optional[StageContext] = None
    ):
        """
        Initialize memory with composed components.
        
        Args:
            connection_manager: Connection management (creates default if None)
            job_context: Job context (creates default if None)
            stage_context: Stage context (creates default if None)
        """
        self.connection_manager = connection_manager or ConnectionManager()
        self.job_context = job_context or JobContext()
        self.stage_context = stage_context or StageContext()
    
    # Convenience properties for backward compatibility
    
    @property
    def stage(self) -> Stage:
        """Get current stage."""
        return self.stage_context.stage
    
    @stage.setter
    def stage(self, value: Stage) -> None:
        """Set current stage."""
        self.stage_context.stage = value
    
    @property
    def job_type(self) -> str:
        """Get job type."""
        return self.job_context.job_type
    
    @job_type.setter
    def job_type(self, value: str) -> None:
        """Set job type."""
        self.job_context.job_type = value
    
    @property
    def last_sql(self) -> Optional[str]:
        """Get last SQL."""
        return self.job_context.last_sql
    
    @last_sql.setter
    def last_sql(self, value: Optional[str]) -> None:
        """Set last SQL."""
        self.job_context.last_sql = value
    
    @property
    def first_sql(self) -> Optional[str]:
        """Get first SQL."""
        return self.job_context.first_sql
    
    @first_sql.setter
    def first_sql(self, value: Optional[str]) -> None:
        """Set first SQL."""
        self.job_context.first_sql = value
    
    @property
    def second_sql(self) -> Optional[str]:
        """Get second SQL."""
        return self.job_context.second_sql
    
    @second_sql.setter
    def second_sql(self, value: Optional[str]) -> None:
        """Set second SQL."""
        self.job_context.second_sql = value
    
    @property
    def first_columns(self) -> Optional[List[str]]:
        """Get first columns."""
        return self.job_context.first_columns
    
    @first_columns.setter
    def first_columns(self, value: Optional[List[str]]) -> None:
        """Set first columns."""
        self.job_context.first_columns = value
    
    @property
    def second_columns(self) -> Optional[List[str]]:
        """Get second columns."""
        return self.job_context.second_columns
    
    @second_columns.setter
    def second_columns(self, value: Optional[List[str]]) -> None:
        """Set second columns."""
        self.job_context.second_columns = value
    
    @property
    def column_mappings(self) -> Optional[List[Dict[str, str]]]:
        """Get column mappings."""
        return self.job_context.column_mappings
    
    @column_mappings.setter
    def column_mappings(self, value: Optional[List[Dict[str, str]]]) -> None:
        """Set column mappings."""
        self.job_context.column_mappings = value
    
    @property
    def key_mappings(self) -> Optional[List[Dict[str, str]]]:
        """Get key mappings."""
        return self.job_context.key_mappings
    
    @key_mappings.setter
    def key_mappings(self, value: Optional[List[Dict[str, str]]]) -> None:
        """Set key mappings."""
        self.job_context.key_mappings = value
    
    @property
    def last_job_id(self) -> Optional[str]:
        """Get last job ID."""
        return self.job_context.last_job_id
    
    @last_job_id.setter
    def last_job_id(self, value: Optional[str]) -> None:
        """Set last job ID."""
        self.job_context.last_job_id = value
    
    @property
    def last_job_name(self) -> Optional[str]:
        """Get last job name."""
        return self.job_context.last_job_name
    
    @last_job_name.setter
    def last_job_name(self, value: Optional[str]) -> None:
        """Set last job name."""
        self.job_context.last_job_name = value
    
    @property
    def last_job_folder(self) -> Optional[str]:
        """Get last job folder."""
        return self.job_context.last_job_folder
    
    @last_job_folder.setter
    def last_job_folder(self, value: Optional[str]) -> None:
        """Set last job folder."""
        self.job_context.last_job_folder = value
    
    @property
    def last_columns(self) -> Optional[List[str]]:
        """Get last columns."""
        return self.job_context.last_columns
    
    @last_columns.setter
    def last_columns(self, value: Optional[List[str]]) -> None:
        """Set last columns."""
        self.job_context.last_columns = value
    
    @property
    def last_preview(self) -> Optional[Dict[str, Any]]:
        """Get last preview."""
        return self.job_context.last_preview
    
    @last_preview.setter
    def last_preview(self, value: Optional[Dict[str, Any]]) -> None:
        """Set last preview."""
        self.job_context.last_preview = value
    
    @property
    def gathered_params(self) -> Dict[str, Any]:
        """Get gathered params."""
        return self.job_context.gathered_params
    
    @gathered_params.setter
    def gathered_params(self, value: Dict[str, Any]) -> None:
        """Set gathered params."""
        self.job_context.gathered_params = value
    
    @property
    def current_tool(self) -> Optional[str]:
        """Get current tool."""
        return self.job_context.current_tool
    
    @current_tool.setter
    def current_tool(self, value: Optional[str]) -> None:
        """Set current tool."""
        self.job_context.current_tool = value
    
    @property
    def last_question(self) -> Optional[str]:
        """Get last question."""
        return self.stage_context.last_question
    
    @last_question.setter
    def last_question(self, value: Optional[str]) -> None:
        """Set last question."""
        self.stage_context.last_question = value
    
    @property
    def execute_query_enabled(self) -> bool:
        """Get execute query flag."""
        return self.job_context.execute_query_enabled
    
    @execute_query_enabled.setter
    def execute_query_enabled(self, value: bool) -> None:
        """Set execute query flag."""
        self.job_context.execute_query_enabled = value
    
    @property
    def output_table_info(self) -> Optional[Dict[str, str]]:
        """Get output table info (schema and table where data was written)."""
        return self.job_context.output_table_info
    
    @output_table_info.setter
    def output_table_info(self, value: Optional[Dict[str, str]]) -> None:
        """Set output table info."""
        self.job_context.output_table_info = value
    
    @property
    def pending_email_params(self) -> Optional[Dict[str, Any]]:
        """Get pending email params (for query confirmation flow)."""
        return self.job_context.pending_email_params
    
    @pending_email_params.setter
    def pending_email_params(self, value: Optional[Dict[str, Any]]) -> None:
        """Set pending email params."""
        self.job_context.pending_email_params = value
    
    @property
    def email_query_confirmed(self) -> bool:
        """Get email query confirmed flag."""
        return self.job_context.email_query_confirmed
    
    @email_query_confirmed.setter
    def email_query_confirmed(self, value: bool) -> None:
        """Set email query confirmed flag."""
        self.job_context.email_query_confirmed = value
    
    @property
    def connection(self) -> str:
        """Get connection."""
        return self.connection_manager.connection
    
    @connection.setter
    def connection(self, value: str) -> None:
        """Set connection."""
        self.connection_manager.connection = value
    
    @property
    def schema(self) -> str:
        """Get schema."""
        return self.connection_manager.schema
    
    @schema.setter
    def schema(self, value: str) -> None:
        """Set schema."""
        self.connection_manager.schema = value
    
    @property
    def selected_tables(self) -> List[str]:
        """Get selected tables."""
        return self.job_context.selected_tables
    
    @selected_tables.setter
    def selected_tables(self, value: List[str]) -> None:
        """Set selected tables."""
        self.job_context.selected_tables = value
    
    @property
    def connections(self) -> Dict[str, Dict[str, Any]]:
        """Get connections."""
        return self.connection_manager.connections
    
    @connections.setter
    def connections(self, value: Dict[str, Dict[str, Any]]) -> None:
        """Set connections."""
        self.connection_manager.connections = value
    
    @property
    def available_schemas(self) -> List[str]:
        """Get available schemas."""
        return self.connection_manager.available_schemas
    
    @available_schemas.setter
    def available_schemas(self, value: List[str]) -> None:
        """Set available schemas."""
        self.connection_manager.available_schemas = value
    
    # Delegated methods
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """Get connection ID (delegates to ConnectionManager)."""
        return self.connection_manager.get_connection_id(connection_name)
    
    def get_connection_list_for_llm(self) -> str:
        """Get connection list for LLM (delegates to ConnectionManager)."""
        return self.connection_manager.get_connection_list_for_llm()
    
    def get_schema_list_for_llm(self) -> str:
        """Get schema list for LLM (delegates to ConnectionManager)."""
        return self.connection_manager.get_schema_list_for_llm()
    
    def reset(self) -> None:
        """Reset all contexts."""
        self.stage_context.reset()
        self.job_context.reset()
        # Keep connection_manager as is (set externally)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization."""
        return {
            **self.stage_context.to_dict(),
            **self.job_context.to_dict(),
            **self.connection_manager.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create Memory from dictionary."""
        return cls(
            stage_context=StageContext.from_dict(data),
            job_context=JobContext.from_dict(data),
            connection_manager=ConnectionManager.from_dict(data)
        )


# Factory function for backward compatibility
def create_memory(
    connection: str = "ORACLE_10",
    schema: str = "SALES"
) -> Memory:
    """
    Create a Memory instance with default configuration.
    
    Args:
        connection: Default connection name
        schema: Default schema name
        
    Returns:
        Memory: Configured memory instance
    """
    return Memory(
        connection_manager=ConnectionManager(
            default_connection=connection,
            default_schema=schema
        ),
        job_context=JobContext(),
        stage_context=StageContext()
    )
