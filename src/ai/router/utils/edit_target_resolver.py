"""
Edit Target Resolver - Maps natural language edit requests to stage transitions.

This module provides resolution of user edit commands like "edit sql", "change reporting"
to the appropriate stage transitions and parameter clearing actions.
"""

import logging
from typing import Dict, Any, Optional
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class EditTargetResolver:
    """
    Resolves natural language edit targets to stage transitions and parameter actions.

    Examples:
    - "edit sql" → Clear last_sql, transition to ASK_SQL_METHOD
    - "change first query" → Clear first_sql, transition to ASK_FIRST_SQL_METHOD
    - "fix mapping" → Clear column_mappings, transition to WAITING_MAP_TABLE
    - "edit job name" → Clear gathered_params["job_name"], stay in current stage
    """

    # Mapping of edit targets to resolution strategies
    EDIT_MAP = {
        # ReadSQL
        "sql": {
            "clear": ["last_sql"],
            "transition": Stage.ASK_SQL_METHOD,
            "message": "Cleared SQL query. Let's start over with the SQL."
        },
        "query": {
            "clear": ["last_sql"],
            "transition": Stage.ASK_SQL_METHOD,
            "message": "Cleared SQL query. Let's start over with the SQL."
        },
        "connection": {
            "clear": ["connection"],
            "transition": Stage.START,
            "message": "Cleared connection. Let's select a connection again."
        },

        # CompareSQL - SQL queries
        "first sql": {
            "clear": ["first_sql"],
            "transition": Stage.ASK_FIRST_SQL_METHOD,
            "message": "Cleared first SQL query. Let's start over with the first query."
        },
        "first query": {
            "clear": ["first_sql"],
            "transition": Stage.ASK_FIRST_SQL_METHOD,
            "message": "Cleared first SQL query. Let's start over with the first query."
        },
        "second sql": {
            "clear": ["second_sql"],
            "transition": Stage.ASK_SECOND_SQL_METHOD,
            "message": "Cleared second SQL query. Let's start over with the second query."
        },
        "second query": {
            "clear": ["second_sql"],
            "transition": Stage.ASK_SECOND_SQL_METHOD,
            "message": "Cleared second SQL query. Let's start over with the second query."
        },

        # CompareSQL - Column mapping
        "mapping": {
            "clear": ["column_mappings", "key_mappings", "gathered_params.first_table_keys",
                      "gathered_params.second_table_keys", "gathered_params.first_table_columns",
                      "gathered_params.second_table_columns"],
            "transition": Stage.WAITING_MAP_TABLE,
            "message": "Cleared column mappings. Let's set up the column mapping again."
        },
        "columns": {
            "clear": ["column_mappings", "key_mappings"],
            "transition": Stage.WAITING_MAP_TABLE,
            "message": "Cleared column mappings. Let's set up the column mapping again."
        },

        # CompareSQL - Reporting type
        "reporting": {
            "clear": ["gathered_params.reporting"],
            "transition": Stage.ASK_REPORTING_TYPE,
            "message": "Cleared reporting type. Select the reporting type again."
        },
        "reporting type": {
            "clear": ["gathered_params.reporting"],
            "transition": Stage.ASK_REPORTING_TYPE,
            "message": "Cleared reporting type. Select the reporting type again."
        },
        "report": {
            "clear": ["gathered_params.reporting"],
            "transition": Stage.ASK_REPORTING_TYPE,
            "message": "Cleared reporting type. Select the reporting type again."
        },

        # Job parameters (works for all jobs)
        "job name": {
            "clear": ["gathered_params.name", "gathered_params.job_name"],
            "transition": None,  # Stay in current stage, re-ask via job agent
            "message": "Cleared job name. What would you like to name this job?"
        },
        "name": {
            "clear": ["gathered_params.name", "gathered_params.job_name"],
            "transition": None,
            "message": "Cleared job name. What would you like to name this job?"
        },
        "schema": {
            "clear": ["gathered_params.schemas", "gathered_params.result_schema"],
            "transition": None,
            "message": "Cleared schema. What schema would you like to use?"
        },
        "table": {
            "clear": ["gathered_params.table_name", "gathered_params.table"],
            "transition": None,
            "message": "Cleared table name. What table would you like to use?"
        },
        "table name": {
            "clear": ["gathered_params.table_name", "gathered_params.table"],
            "transition": None,
            "message": "Cleared table name. What table would you like to use?"
        },

        # SendEmail parameters
        "to": {
            "clear": ["gathered_params.to"],
            "transition": None,
            "message": "Cleared 'To' email address. Please provide the recipient email address:"
        },
        "subject": {
            "clear": ["gathered_params.subject"],
            "transition": None,
            "message": "Cleared email subject. What should the email subject be?"
        },
        "body": {
            "clear": ["gathered_params.body"],
            "transition": None,
            "message": "Cleared email body. What should the email body say?"
        },
    }

    # Fuzzy matching alternatives
    FUZZY_MATCHES = {
        "sql": ["query", "sql query", "the query", "the sql"],
        "first sql": ["first query", "query 1", "sql 1", "first"],
        "second sql": ["second query", "query 2", "sql 2", "second"],
        "mapping": ["mappings", "column mapping", "columns", "the mapping"],
        "reporting": ["report type", "report", "reporting type"],
        "job name": ["name", "job", "the name"],
        "schema": ["the schema", "result schema"],
        "table": ["table name", "the table", "result table"],
        "to": ["to email", "recipient", "to address"],
        "subject": ["email subject", "the subject"],
        "body": ["email body", "message", "the body"],
    }

    @staticmethod
    def resolve(edit_target: str, memory: Memory) -> Optional[Dict[str, Any]]:
        """
        Resolve edit target to actions.

        Args:
            edit_target: What the user wants to edit (e.g., "sql", "first query")
            memory: Conversation memory

        Returns:
            Dict with resolution info or None if cannot resolve
        """
        edit_target_lower = edit_target.lower().strip()

        # Direct match
        if edit_target_lower in EditTargetResolver.EDIT_MAP:
            return EditTargetResolver._build_resolution(edit_target_lower, memory)

        # Fuzzy match
        for key, aliases in EditTargetResolver.FUZZY_MATCHES.items():
            if edit_target_lower in aliases or any(alias in edit_target_lower for alias in aliases):
                return EditTargetResolver._build_resolution(key, memory)

        # Partial match (user said "edit first" instead of "edit first sql")
        for key in EditTargetResolver.EDIT_MAP.keys():
            if key in edit_target_lower or edit_target_lower in key:
                return EditTargetResolver._build_resolution(key, memory)

        # Could not resolve
        logger.warning(f"Could not resolve edit target: {edit_target}")
        return None

    @staticmethod
    def _build_resolution(key: str, memory: Memory) -> Dict[str, Any]:
        """
        Build resolution dict from edit map entry.

        Args:
            key: Key in EDIT_MAP
            memory: Conversation memory

        Returns:
            Resolution dict
        """
        config = EditTargetResolver.EDIT_MAP[key]

        # Clear parameters
        for param_path in config["clear"]:
            EditTargetResolver._clear_parameter(memory, param_path)

        return {
            "message": config["message"],
            "transition_to": config.get("transition"),
            "clear_params": config["clear"]
        }

    @staticmethod
    def _clear_parameter(memory: Memory, param_path: str) -> None:
        """
        Clear a parameter from memory.

        Supports paths like:
        - "last_sql" → memory.last_sql = None
        - "gathered_params.name" → memory.gathered_params.pop("name")

        Args:
            memory: Conversation memory
            param_path: Path to parameter (dot notation for nested)
        """
        if "." in param_path:
            # Nested parameter (e.g., gathered_params.name)
            parts = param_path.split(".", 1)
            container_name = parts[0]
            param_name = parts[1]

            if container_name == "gathered_params":
                if param_name in memory.gathered_params:
                    old_value = memory.gathered_params.pop(param_name)
                    logger.debug(f"Cleared gathered_params.{param_name} = {old_value}")
        else:
            # Top-level parameter
            if hasattr(memory, param_path):
                setattr(memory, param_path, None)
                logger.debug(f"Cleared memory.{param_path}")

    @staticmethod
    def get_available_edit_targets(memory: Memory) -> list:
        """
        Get list of available edit targets based on current memory state.

        Args:
            memory: Conversation memory

        Returns:
            List of edit target names that are currently set
        """
        available = []

        if memory.connection:
            available.append("connection")

        if hasattr(memory, 'last_sql') and memory.last_sql:
            available.append("sql")

        if hasattr(memory, 'first_sql') and memory.first_sql:
            available.append("first sql")

        if hasattr(memory, 'second_sql') and memory.second_sql:
            available.append("second sql")

        if hasattr(memory, 'column_mappings') and memory.column_mappings:
            available.append("mapping")

        if "reporting" in memory.gathered_params:
            available.append("reporting")

        # Job parameters
        for param in ["name", "job_name", "schemas", "table_name", "table"]:
            if param in memory.gathered_params:
                available.append(param.replace("_", " "))

        return available
