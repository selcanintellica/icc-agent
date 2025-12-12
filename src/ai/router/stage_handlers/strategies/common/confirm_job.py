"""
Confirmation Strategy - Shows job summary and gets user confirmation before execution.

This strategy is reusable across all job types (ReadSQL, WriteData, SendEmail, CompareSQL).
"""

import logging
from typing import Dict, Any
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.utils.edit_target_resolver import EditTargetResolver

logger = logging.getLogger(__name__)


class ConfirmJobStrategy(StageStrategy):
    """
    Show final job summary and get user confirmation before execution.

    Supports:
    - yes/confirm/looks good → Execute job
    - no/cancel → Ask what to edit
    - edit <param> → Edit specific parameter
    - back → Go to previous stage
    - reset → Start over
    """

    def __init__(self, job_type: str, execution_callback=None):
        """
        Initialize confirmation strategy.

        Args:
            job_type: Type of job (read_sql, write_data, send_email, compare_sql)
            execution_callback: Async function to call when confirmed
        """
        super().__init__()
        self.job_type = job_type
        self.execution_callback = execution_callback

    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle confirmation stage.

        Args:
            memory: Conversation memory
            user_input: User's input

        Returns:
            StageHandlerResult with next action
        """
        user_lower = user_input.lower().strip()

        # First time entering - show summary
        if not user_input or user_lower in ["yes", "ok", "okay", "sure", "correct"] and not hasattr(self, '_summary_shown'):
            summary = self._format_summary(memory)
            self._summary_shown = True
            return self._create_result(memory, summary)

        # Confirmation - proceed to execution
        if user_lower in ["yes", "confirm", "ok", "looks good", "proceed", "go ahead", "yes please"]:
            logger.info(f"User confirmed {self.job_type} job, proceeding to execution")

            # Execute the job
            if self.execution_callback:
                return await self.execution_callback(memory)
            else:
                # Fallback: transition to appropriate execution stage
                return self._transition_to_execution(memory)

        # Cancellation
        if user_lower in ["no", "cancel", "abort", "stop", "don't"]:
            logger.info(f"User cancelled {self.job_type} job")
            return self._create_result(
                memory,
                "❌ Job creation cancelled.\n\nWhat would you like to edit? (Type 'edit <parameter>' or 'reset' to start over)"
            )

        # Edit commands
        if any(user_lower.startswith(prefix) for prefix in ["edit ", "change ", "correct ", "fix ", "update "]):
            return self._handle_edit_command(memory, user_input)

        # Back command
        if user_lower in ["back", "go back", "previous"]:
            logger.info("User requested back from confirmation")
            if hasattr(memory.stage_context, 'go_back'):
                prev_stage = memory.stage_context.go_back()
                return self._create_result(
                    memory,
                    "⬅️ Going back to previous step...",
                    prev_stage
                )

        # Reset command
        if user_lower in ["reset", "start over", "restart"]:
            logger.info("User requested reset from confirmation")
            memory.reset()
            return self._create_result(
                memory,
                "🔄 Reset complete. What type of job would you like to create?",
                Stage.START
            )

        # Show summary again if unclear input
        summary = self._format_summary(memory)
        return self._create_result(
            memory,
            f"I didn't understand '{user_input}'.\n\n{summary}"
        )

    def _format_summary(self, memory: Memory) -> str:
        """
        Format job summary for review.

        Args:
            memory: Conversation memory

        Returns:
            Formatted summary string
        """
        if self.job_type == "read_sql":
            return self._format_read_sql_summary(memory)
        elif self.job_type == "write_data":
            return self._format_write_data_summary(memory)
        elif self.job_type == "send_email":
            return self._format_send_email_summary(memory)
        elif self.job_type == "compare_sql":
            return self._format_compare_sql_summary(memory)
        else:
            return self._format_generic_summary(memory)

    def _format_read_sql_summary(self, memory: Memory) -> str:
        """Format ReadSQL job summary."""
        summary = "📋 **ReadSQL Job Summary**\n\n"

        # SQL Query
        if memory.last_sql:
            sql_preview = memory.last_sql[:300] + "..." if len(memory.last_sql) > 300 else memory.last_sql
            summary += f"**SQL Query:**\n```sql\n{sql_preview}\n```\n\n"

        # Connection
        if memory.connection:
            summary += f"**Connection:** {memory.connection}\n"

        # Job parameters
        params = memory.gathered_params
        if params.get("name"):
            summary += f"**Job Name:** {params['name']}\n"

        if params.get("execute_query"):
            summary += f"**Save Results:** Yes\n"
            if params.get("result_schema"):
                summary += f"**Result Schema:** {params['result_schema']}\n"
            if params.get("table_name"):
                summary += f"**Result Table:** {params['table_name']}\n"
            if params.get("drop_before_create"):
                summary += f"**Drop Before Create:** {params['drop_before_create']}\n"
        else:
            summary += f"**Save Results:** No (preview only)\n"

        if params.get("write_count"):
            summary += f"**Track Row Count:** Yes\n"

        summary += "\n**Ready to create this job?**\n"
        summary += "- Type **'yes'** or **'confirm'** to proceed\n"
        summary += "- Type **'edit <parameter>'** to modify something (e.g., 'edit sql', 'edit job name')\n"
        summary += "- Type **'cancel'** to abort\n"

        return summary

    def _format_write_data_summary(self, memory: Memory) -> str:
        """Format WriteData job summary."""
        summary = "📋 **WriteData Job Summary**\n\n"

        params = memory.gathered_params

        if params.get("name"):
            summary += f"**Job Name:** {params['name']}\n"

        if memory.connection:
            summary += f"**Connection:** {memory.connection}\n"

        if params.get("schemas"):
            summary += f"**Schema:** {params['schemas']}\n"

        if params.get("table"):
            summary += f"**Table:** {params['table']}\n"

        if params.get("drop_or_truncate"):
            summary += f"**Action:** {params['drop_or_truncate']}\n"

        summary += "\n**Ready to create this job?**\n"
        summary += "- Type **'yes'** or **'confirm'** to proceed\n"
        summary += "- Type **'edit <parameter>'** to modify something\n"
        summary += "- Type **'cancel'** to abort\n"

        return summary

    def _format_send_email_summary(self, memory: Memory) -> str:
        """Format SendEmail job summary."""
        summary = "📋 **SendEmail Job Summary**\n\n"

        params = memory.gathered_params

        if params.get("name"):
            summary += f"**Job Name:** {params['name']}\n"

        if params.get("to"):
            summary += f"**To:** {params['to']}\n"

        if params.get("cc"):
            summary += f"**CC:** {params['cc']}\n"

        if params.get("subject"):
            summary += f"**Subject:** {params['subject']}\n"

        if params.get("text"):
            text_preview = params['text'][:100] + "..." if len(params['text']) > 100 else params['text']
            summary += f"**Message:** {text_preview}\n"

        summary += "\n**Ready to send this email?**\n"
        summary += "- Type **'yes'** or **'confirm'** to proceed\n"
        summary += "- Type **'edit <parameter>'** to modify something\n"
        summary += "- Type **'cancel'** to abort\n"

        return summary

    def _format_compare_sql_summary(self, memory: Memory) -> str:
        """Format CompareSQL job summary."""
        summary = "📋 **CompareSQL Job Summary**\n\n"

        # First SQL
        if memory.first_sql:
            sql_preview = memory.first_sql[:200] + "..." if len(memory.first_sql) > 200 else memory.first_sql
            summary += f"**First SQL:**\n```sql\n{sql_preview}\n```\n\n"

        # Second SQL
        if memory.second_sql:
            sql_preview = memory.second_sql[:200] + "..." if len(memory.second_sql) > 200 else memory.second_sql
            summary += f"**Second SQL:**\n```sql\n{sql_preview}\n```\n\n"

        # Column Mapping
        params = memory.gathered_params
        if params.get("first_table_keys") and params.get("second_table_keys"):
            summary += f"**Key Mapping:**\n"
            summary += f"- First Keys: {params['first_table_keys']}\n"
            summary += f"- Second Keys: {params['second_table_keys']}\n\n"

        if params.get("first_table_columns") and params.get("second_table_columns"):
            summary += f"**Column Mapping:**\n"
            summary += f"- First Columns: {params['first_table_columns'][:100]}{'...' if len(params['first_table_columns']) > 100 else ''}\n"
            summary += f"- Second Columns: {params['second_table_columns'][:100]}{'...' if len(params['second_table_columns']) > 100 else ''}\n\n"

        # Reporting type
        if params.get("reporting"):
            summary += f"**Reporting Type:** {params['reporting']}\n"

        # Result location
        if params.get("schemas") and params.get("table_name"):
            summary += f"**Result Location:** {params['schemas']}.{params['table_name']}\n"

        # Job name
        if params.get("job_name"):
            summary += f"**Job Name:** {params['job_name']}\n"

        summary += "\n**Ready to create this comparison job?**\n"
        summary += "- Type **'yes'** or **'confirm'** to proceed\n"
        summary += "- Type **'edit <parameter>'** to modify something (e.g., 'edit first sql', 'edit reporting')\n"
        summary += "- Type **'cancel'** to abort\n"

        return summary

    def _format_generic_summary(self, memory: Memory) -> str:
        """Format generic job summary."""
        summary = f"📋 **{self.job_type.replace('_', ' ').title()} Job Summary**\n\n"

        if memory.gathered_params:
            summary += "**Parameters:**\n"
            for key, value in memory.gathered_params.items():
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                summary += f"- {key}: {value}\n"

        summary += "\n**Ready to proceed?**\n"
        summary += "- Type **'yes'** to confirm\n"
        summary += "- Type **'edit <parameter>'** to modify\n"
        summary += "- Type **'cancel'** to abort\n"

        return summary

    def _handle_edit_command(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle edit command from confirmation.

        Args:
            memory: Conversation memory
            user_input: User's edit command

        Returns:
            StageHandlerResult with edit action
        """
        logger.info(f"User requested edit from confirmation: {user_input}")

        # Use edit target resolver
        edit_resolver = EditTargetResolver()
        resolution = edit_resolver.resolve(user_input.lower().replace("edit ", "").replace("change ", ""), memory)

        if resolution and resolution.get("transition_to"):
            # Clear parameters and transition
            logger.info(f"Resolved edit to stage: {resolution['transition_to'].value}")
            return self._create_result(
                memory,
                resolution["message"],
                resolution["transition_to"]
            )
        elif resolution:
            # Parameters cleared but stay in same stage (e.g., job name)
            # Re-show summary with cleared param
            summary = self._format_summary(memory)
            return self._create_result(
                memory,
                f"✏️ {resolution['message']}\n\n{summary}"
            )
        else:
            # Could not resolve
            available = edit_resolver.get_available_edit_targets(memory)
            message = f"I couldn't identify what you want to edit from '{user_input}'.\n\n"
            if available:
                message += "Available items to edit:\n"
                for item in available[:10]:
                    message += f"- {item}\n"
                message += "\nTry: 'edit <item>' (e.g., 'edit sql', 'edit job name')"
            else:
                message += "No parameters to edit."

            return self._create_result(memory, message)

    def _transition_to_execution(self, memory: Memory) -> StageHandlerResult:
        """
        Transition to appropriate execution stage based on job type.

        Args:
            memory: Conversation memory

        Returns:
            StageHandlerResult with execution stage
        """
        if self.job_type == "read_sql":
            return self._create_result(
                memory,
                "Creating ReadSQL job...",
                Stage.EXECUTE_SQL
            )
        elif self.job_type == "compare_sql":
            # For CompareSQL, we need to actually execute here
            # since EXECUTE_COMPARE_SQL is deprecated
            return self._create_result(
                memory,
                "Creating CompareSQL job...",
                Stage.GATHER_COMPARE_PARAMS  # Will handle execution
            )
        elif self.job_type == "write_data":
            return self._create_result(
                memory,
                "Creating WriteData job...",
                Stage.START  # WriteData needs proper execution stage
            )
        elif self.job_type == "send_email":
            return self._create_result(
                memory,
                "Sending email...",
                Stage.START  # SendEmail needs proper execution stage
            )
        else:
            return self._create_result(
                memory,
                "Proceeding with job creation...",
                Stage.START
            )
