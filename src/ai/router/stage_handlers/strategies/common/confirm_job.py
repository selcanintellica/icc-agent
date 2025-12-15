"""
Strategy for job confirmation before execution.

This strategy shows a summary of all job parameters (including optional ones with defaults)
and allows users to confirm, cancel, or edit any parameter before job creation.
"""

import logging
import json
import re
from typing import Dict, Any, Optional, Callable
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.utils.connection_fetcher import ConnectionFetcher

logger = logging.getLogger(__name__)


class ConfirmJobStrategy(StageStrategy):
    """
    Handle job confirmation with optional parameter editing.

    Supports all job types: read_sql, write_data, send_email, compare_sql

    Features:
    - Shows complete job summary with all parameters
    - Displays optional parameters with default values
    - Allows editing any parameter including optional ones
    - Handles sub-flows (e.g., write_count needs connection/schema/table)
    - Auto-returns to confirmation after edits
    """

    def __init__(self, job_type: str, execution_callback: Optional[Callable] = None):
        """
        Initialize confirmation strategy.

        Args:
            job_type: Type of job (read_sql, write_data, send_email, compare_sql)
            execution_callback: Optional callback to execute the job
        """
        super().__init__()
        self.job_type = job_type
        self.execution_callback = execution_callback

    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle confirmation stage.

        User can:
        - Confirm: yes/confirm/ok → Execute job
        - Cancel: no/cancel → Abort
        - Edit: edit <param> → Edit specific parameter
        """
        # Check if we're in a sub-flow (editing write_count or cc)
        if hasattr(memory, 'confirmation_substate') and memory.confirmation_substate:
            return await self._handle_subflow(memory, user_input)

        user_lower = user_input.lower().strip()

        # Show initial summary if empty input (from back command)
        if not user_lower:
            return await self._show_summary(memory)

        # Handle confirmation
        if any(word in user_lower for word in ["yes", "confirm", "ok", "looks good", "correct"]):
            logger.info(f"User confirmed {self.job_type} job")
            if self.execution_callback:
                return await self.execution_callback(memory)
            else:
                return self._create_result(
                    memory,
                    "Job confirmed but no execution callback configured.",
                    is_error=True
                )

        # Handle cancellation
        if any(word in user_lower for word in ["no", "cancel", "abort"]):
            logger.info(f"User cancelled {self.job_type} job")
            memory.gathered_params = {}
            return self._create_result(
                memory,
                "Job creation cancelled. What would you like to do next?"
            )

        # Handle edit commands
        if any(user_lower.startswith(prefix) for prefix in ["edit ", "change ", "modify "]):
            return await self._handle_edit(memory, user_input)

        # Invalid input - re-show summary with hint
        return await self._show_summary(memory, hint="Please say 'yes' to confirm, 'edit <parameter>' to modify, or 'cancel' to abort.")

    async def _show_summary(self, memory: Memory, hint: Optional[str] = None) -> StageHandlerResult:
        """
        Show formatted job summary with all parameters.

        Args:
            memory: Current memory
            hint: Optional hint to show at the end
        """
        params = memory.gathered_params

        summary = f"📋 **{self._get_job_display_name()} Job Summary**\n\n"

        if self.job_type == "read_sql":
            summary += self._format_read_sql_summary(memory, params)
        elif self.job_type == "write_data":
            summary += self._format_write_data_summary(memory, params)
        elif self.job_type == "send_email":
            summary += self._format_send_email_summary(memory, params)
        elif self.job_type == "compare_sql":
            summary += self._format_compare_sql_summary(memory, params)

        summary += "\n**Ready to create this job?**\n"
        summary += "- Type **'yes'** or **'confirm'** to proceed\n"
        summary += "- Type **'edit <parameter>'** to modify something\n"
        summary += "  Examples: 'edit write count', 'edit cc', 'edit job name'\n"
        summary += "- Type **'cancel'** to abort\n"

        if hint:
            summary += f"\n💡 {hint}"

        return self._create_result(memory, summary)

    def _format_read_sql_summary(self, memory: Memory, params: Dict[str, Any]) -> str:
        """Format ReadSQL job summary."""
        sql = memory.last_sql or "Not set"
        sql_preview = sql[:200] + "..." if len(sql) > 200 else sql

        summary = f"**SQL Query:**\n```sql\n{sql_preview}\n```\n\n"
        summary += "**Execution Settings:**\n"
        summary += f"- Connection: {memory.connection or params.get('connection', 'Not set')}\n"
        summary += f"- Execute Query: {params.get('execute_query', True)}\n"

        if params.get('schemas'):
            summary += f"- Result Schema: {params.get('schemas')}\n"
        if params.get('table_name'):
            summary += f"- Result Table: {params.get('table_name')}\n"
        if params.get('name'):
            summary += f"- Job Name: {params.get('name')}\n"

        summary += "\n**Optional Settings:**\n"
        summary += self._format_write_count_params(params)

        return summary

    def _format_write_data_summary(self, memory: Memory, params: Dict[str, Any]) -> str:
        """Format WriteData job summary."""
        summary = "**Data Source:**\n"
        summary += f"- Job ID: {memory.last_job_id or 'Not set'}\n"

        if memory.output_table_info:
            summary += f"- Source Table: {memory.output_table_info.get('schema')}.{memory.output_table_info.get('table')}\n"

        summary += "\n**Destination:**\n"
        summary += f"- Connection: {params.get('connection', 'Not set')}\n"
        summary += f"- Schema: {params.get('schemas', 'Not set')}\n"
        summary += f"- Table: {params.get('table', 'Not set')}\n"
        summary += f"- Drop/Truncate: {params.get('drop_or_truncate', 'drop')}\n"

        if params.get('name'):
            summary += f"- Job Name: {params.get('name')}\n"

        summary += "\n**Optional Settings:**\n"
        summary += self._format_write_count_params(params)

        return summary

    def _format_send_email_summary(self, memory: Memory, params: Dict[str, Any]) -> str:
        """Format SendEmail job summary."""
        summary = "**Email Settings:**\n"
        summary += f"- To: {params.get('to', 'Not set')}\n"

        cc = params.get('cc', '')
        if cc:
            summary += f"- CC: {cc} ✓ (modified)\n"
        else:
            summary += "- CC: (none) ✓ (default)\n"

        summary += f"- Subject: {params.get('subject', 'Not set')}\n"

        body = params.get('body', '')
        body_preview = body[:100] + "..." if len(body) > 100 else body
        summary += f"- Body: {body_preview}\n"

        summary += "\n**Data Source:**\n"
        summary += f"- Job ID: {memory.last_job_id or 'Not set'}\n"

        if memory.output_table_info:
            summary += f"- Table: {memory.output_table_info.get('schema')}.{memory.output_table_info.get('table')}\n"

        return summary

    def _format_compare_sql_summary(self, memory: Memory, params: Dict[str, Any]) -> str:
        """Format CompareSQL job summary."""
        first_sql = memory.first_sql or "Not set"
        second_sql = memory.second_sql or "Not set"

        first_preview = first_sql[:150] + "..." if len(first_sql) > 150 else first_sql
        second_preview = second_sql[:150] + "..." if len(second_sql) > 150 else second_sql

        summary = f"**First SQL:**\n```sql\n{first_preview}\n```\n\n"
        summary += f"**Second SQL:**\n```sql\n{second_preview}\n```\n\n"

        if params.get('first_table_keys') and params.get('second_table_keys'):
            summary += "**Key Mapping:**\n"
            summary += f"- First Keys: {params.get('first_table_keys')}\n"
            summary += f"- Second Keys: {params.get('second_table_keys')}\n\n"

        if params.get('first_table_columns') and params.get('second_table_columns'):
            summary += "**Column Mapping:**\n"
            summary += f"- First Columns: {params.get('first_table_columns')}\n"
            summary += f"- Second Columns: {params.get('second_table_columns')}\n\n"

        summary += "**Comparison Settings:**\n"
        summary += f"- Reporting Type: {params.get('reporting', 'Not set')}\n"
        summary += f"- Result Schema: {params.get('schemas', 'Not set')}\n"
        summary += f"- Result Table: {params.get('table_name', 'Not set')}\n"

        if params.get('job_name'):
            summary += f"- Job Name: {params.get('job_name')}\n"

        return summary

    def _format_write_count_params(self, params: Dict[str, Any]) -> str:
        """Format write_count optional parameters."""
        write_count = params.get('write_count', False)

        if not write_count:
            return "- Write Count: false ✓ (default)\n"
        else:
            lines = "- Write Count: true ✓ (modified)\n"
            if params.get('write_count_connection'):
                lines += f"  - Connection: {params.get('write_count_connection')}\n"
            if params.get('write_count_schema'):
                lines += f"  - Schema: {params.get('write_count_schema')}\n"
            if params.get('write_count_table'):
                lines += f"  - Table: {params.get('write_count_table')}\n"
            return lines

    def _get_job_display_name(self) -> str:
        """Get display name for job type."""
        names = {
            "read_sql": "ReadSQL",
            "write_data": "WriteData",
            "send_email": "SendEmail",
            "compare_sql": "CompareSQL"
        }
        return names.get(self.job_type, self.job_type)

    async def _handle_edit(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle edit commands for any parameter.

        Args:
            memory: Current memory
            user_input: Edit command (e.g., "edit write count")
        """
        # Extract parameter name
        edit_lower = user_input.lower().strip()
        for prefix in ["edit ", "change ", "modify "]:
            if edit_lower.startswith(prefix):
                param_name = edit_lower[len(prefix):].strip()
                break
        else:
            param_name = edit_lower

        logger.info(f"User wants to edit: {param_name}")

        # Handle write_count editing
        if param_name in ["write count", "write_count", "writecount", "row count"]:
            if self.job_type not in ["read_sql", "write_data"]:
                return await self._show_summary(memory, hint=f"Write count is not available for {self._get_job_display_name()} jobs.")

            memory.confirmation_substate = "editing_write_count"
            return self._create_result(
                memory,
                "Do you want to write row counts? (yes/no)"
            )

        # Handle CC editing
        if param_name in ["cc", "carbon copy"]:
            if self.job_type != "send_email":
                return await self._show_summary(memory, hint="CC is only available for SendEmail jobs.")

            memory.confirmation_substate = "editing_cc"
            return self._create_result(
                memory,
                "Please provide CC email addresses (comma-separated), or type 'none' to clear:"
            )

        # Handle other parameter edits via EditTargetResolver
        from src.ai.router.utils.edit_target_resolver import EditTargetResolver
        resolver = EditTargetResolver()
        resolution = resolver.resolve(param_name, memory)

        if resolution:
            return self._create_result(
                memory,
                resolution.get("message"),
                resolution.get("transition_to")
            )
        else:
            return await self._show_summary(
                memory,
                hint=f"I couldn't identify what you want to edit from '{param_name}'. Try: 'edit write count', 'edit cc', 'edit job name', etc."
            )

    async def _handle_subflow(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle sub-flows for editing optional parameters.

        Subflows:
        - editing_write_count → ask yes/no
        - selecting_wc_connection → show connection dropdown
        - selecting_wc_schema → show schema dropdown
        - entering_wc_table → ask for table name
        - editing_cc → ask for CC emails
        """
        substate = memory.confirmation_substate
        user_lower = user_input.lower().strip()

        if substate == "editing_write_count":
            if any(word in user_lower for word in ["yes", "true", "enable"]):
                # Enable write_count, fetch connections
                memory.gathered_params['write_count'] = True
                memory.confirmation_substate = "selecting_wc_connection"
                return await self._fetch_write_count_connections(memory)
            elif any(word in user_lower for word in ["no", "false", "disable"]):
                # Disable write_count, clear related params
                memory.gathered_params['write_count'] = False
                memory.gathered_params.pop('write_count_connection', None)
                memory.gathered_params.pop('write_count_schema', None)
                memory.gathered_params.pop('write_count_table', None)
                memory.confirmation_substate = None
                return await self._show_summary(memory)
            else:
                return self._create_result(
                    memory,
                    "Please answer 'yes' to enable row count writing, or 'no' to disable it."
                )

        elif substate == "selecting_wc_connection":
            # Handle connection selection
            if user_input.startswith("__CONNECTION_SELECTED__:"):
                connection_name = user_input.replace("__CONNECTION_SELECTED__:", "").strip()
                memory.gathered_params['write_count_connection'] = connection_name
                memory.confirmation_substate = "selecting_wc_schema"
                return await self._fetch_write_count_schemas(memory, connection_name)
            else:
                # Direct input of connection name
                memory.gathered_params['write_count_connection'] = user_input.strip()
                memory.confirmation_substate = "selecting_wc_schema"
                return await self._fetch_write_count_schemas(memory, user_input.strip())

        elif substate == "selecting_wc_schema":
            # Handle schema selection
            if user_input.startswith("__SCHEMA_SELECTED__:"):
                schema_name = user_input.replace("__SCHEMA_SELECTED__:", "").strip()
                memory.gathered_params['write_count_schema'] = schema_name
            else:
                memory.gathered_params['write_count_schema'] = user_input.strip()

            memory.confirmation_substate = "entering_wc_table"
            return self._create_result(
                memory,
                "What table name should I use for row counts?"
            )

        elif substate == "entering_wc_table":
            # Store table name and return to confirmation
            table_name = user_input.strip()
            if not table_name:
                return self._create_result(
                    memory,
                    "Table name cannot be empty. Please provide a table name:"
                )

            memory.gathered_params['write_count_table'] = table_name
            memory.confirmation_substate = None
            return await self._show_summary(memory)

        elif substate == "editing_cc":
            # Handle CC email editing
            if user_lower in ["none", "clear", "remove", ""]:
                memory.gathered_params['cc'] = ""
            else:
                # Validate email format
                emails = [e.strip() for e in user_input.split(',')]
                invalid_emails = [e for e in emails if not self._is_valid_email(e)]

                if invalid_emails:
                    return self._create_result(
                        memory,
                        f"Invalid email format: {', '.join(invalid_emails)}\n\nPlease provide valid email addresses (comma-separated):"
                    )

                memory.gathered_params['cc'] = user_input.strip()

            memory.confirmation_substate = None
            return await self._show_summary(memory)

        # Unknown substate
        logger.warning(f"Unknown confirmation substate: {substate}")
        memory.confirmation_substate = None
        return await self._show_summary(memory)

    async def _fetch_write_count_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch available connections for write_count."""
        try:
            # Only fetch from API if not already in memory
            if not memory.connections:
                result = await ConnectionFetcher.fetch_connections(memory)
                if not result["success"]:
                    return self._create_result(
                        memory,
                        f"Unable to fetch connections: {result['message']}\n\nPlease type the connection name directly:",
                        is_error=True
                    )

            # Show dropdown with available connections
            question_text = "Which connection should I use for row count writes?"
            connections_list = list(memory.connections.keys()) if memory.connections else []
            response = f"CONNECTION_DROPDOWN:{json.dumps({'connections': connections_list, 'param_name': 'write_count_connection', 'question': question_text})}"
            return self._create_result(memory, response)

        except Exception as e:
            logger.error(f"Error fetching connections for write_count: {e}", exc_info=True)
            return self._create_result(
                memory,
                f"Unable to fetch connections: {str(e)}\n\nPlease type the connection name directly:",
                is_error=True
            )

    async def _fetch_write_count_schemas(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch available schemas for write_count."""
        try:
            result = await ConnectionFetcher.fetch_schemas(connection_name, memory)

            if result["success"]:
                question_text = "Which schema should I use for row count writes?"
                response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': 'write_count_schema', 'question': question_text})}"
                return self._create_result(memory, response)
            else:
                return self._create_result(
                    memory,
                    f"Unable to fetch schemas: {result['message']}\n\nPlease type the schema name directly:",
                    is_error=True
                )
        except Exception as e:
            logger.error(f"Error fetching schemas for write_count: {e}", exc_info=True)
            return self._create_result(
                memory,
                f"Unable to fetch schemas: {str(e)}\n\nPlease type the schema name directly:",
                is_error=True
            )

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            bool: True if valid email format
        """
        if not email:
            return False

        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
