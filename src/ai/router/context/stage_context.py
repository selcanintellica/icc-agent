"""
Stage Context.

Handles conversation stage management following Single Responsibility Principle.
"""

from enum import Enum
from typing import Optional


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
    
    # SendEmail Flow
    CONFIRM_EMAIL_QUERY = "confirm_email_query"
    NEED_EMAIL_QUERY = "need_email_query"
    
    DONE = "done"


class StageContext:
    """
    Manages conversation stage and flow.
    
    Following SRP - only responsible for stage transitions and tracking.
    """
    
    def __init__(self, initial_stage: Stage = Stage.START):
        """
        Initialize stage context.
        
        Args:
            initial_stage: Starting stage
        """
        self._stage: Stage = initial_stage
        self._last_question: Optional[str] = None
    
    @property
    def stage(self) -> Stage:
        """Get current stage."""
        return self._stage
    
    @stage.setter
    def stage(self, value: Stage) -> None:
        """Set current stage."""
        self._stage = value
    
    @property
    def last_question(self) -> Optional[str]:
        """Get last question asked to user."""
        return self._last_question
    
    @last_question.setter
    def last_question(self, value: Optional[str]) -> None:
        """Set last question asked to user."""
        self._last_question = value
    
    def transition_to(self, new_stage: Stage, question: Optional[str] = None) -> None:
        """
        Transition to a new stage.
        
        Args:
            new_stage: Stage to transition to
            question: Optional question being asked (for context)
        """
        self._stage = new_stage
        if question:
            self._last_question = question
    
    def is_read_sql_flow(self) -> bool:
        """Check if currently in ReadSQL flow."""
        read_sql_stages = {
            Stage.ASK_SQL_METHOD,
            Stage.NEED_NATURAL_LANGUAGE,
            Stage.NEED_USER_SQL,
            Stage.CONFIRM_GENERATED_SQL,
            Stage.CONFIRM_USER_SQL,
            Stage.EXECUTE_SQL
        }
        return self._stage in read_sql_stages
    
    def is_compare_sql_flow(self) -> bool:
        """Check if currently in CompareSQL flow."""
        compare_sql_stages = {
            Stage.ASK_FIRST_SQL_METHOD,
            Stage.NEED_FIRST_NATURAL_LANGUAGE,
            Stage.NEED_FIRST_USER_SQL,
            Stage.CONFIRM_FIRST_GENERATED_SQL,
            Stage.CONFIRM_FIRST_USER_SQL,
            Stage.ASK_SECOND_SQL_METHOD,
            Stage.NEED_SECOND_NATURAL_LANGUAGE,
            Stage.NEED_SECOND_USER_SQL,
            Stage.CONFIRM_SECOND_GENERATED_SQL,
            Stage.CONFIRM_SECOND_USER_SQL,
            Stage.ASK_AUTO_MATCH,
            Stage.WAITING_MAP_TABLE,
            Stage.ASK_REPORTING_TYPE,
            Stage.ASK_COMPARE_SCHEMA,
            Stage.ASK_COMPARE_TABLE_NAME,
            Stage.ASK_COMPARE_JOB_NAME,
            Stage.EXECUTE_COMPARE_SQL
        }
        return self._stage in compare_sql_stages
    
    def is_post_execution(self) -> bool:
        """Check if in post-execution stages."""
        return self._stage in {Stage.SHOW_RESULTS, Stage.NEED_WRITE_OR_EMAIL}
    
    def is_done(self) -> bool:
        """Check if conversation is complete."""
        return self._stage == Stage.DONE
    
    def reset(self) -> None:
        """Reset to initial stage."""
        self._stage = Stage.START
        self._last_question = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "stage": self._stage.value,
            "last_question": self._last_question
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StageContext":
        """Create StageContext from dictionary."""
        context = cls(initial_stage=Stage(data.get("stage", "start")))
        context.last_question = data.get("last_question")
        return context
