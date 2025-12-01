"""
SendEmail flow handler.

Handles all stages related to emailing query results following SOLID principles.
"""

import logging
import json
from typing import Dict, Any
from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.toolkits.icc_toolkit import send_email_job
from src.models.natural_language import SendEmailLLMRequest, SendEmailVariables

logger = logging.getLogger(__name__)


class SendEmailHandler(BaseStageHandler):
    """
    Handler for SendEmail workflow.
    
    Following Single Responsibility Principle - only handles send_email-related operations.
    """
    
    # Define which stages this handler manages
    MANAGED_STAGES = {
        Stage.NEED_WRITE_OR_EMAIL,  # Can be triggered from this stage
        Stage.CONFIRM_EMAIL_QUERY,  # Confirming auto-generated query
        Stage.NEED_EMAIL_QUERY,  # User provides custom query
    }
    
    def __init__(self, job_agent=None):
        """
        Initialize SendEmail handler.
        
        Args:
            job_agent: Job agent for parameter gathering (optional)
        """
        self.job_agent = job_agent
    
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Note: SendEmail is typically accessed as a tool after ReadSQL,
        so it checks memory.current_tool in addition to stage.
        """
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the SendEmail workflow based on current stage."""
        logger.info(f"SendEmailHandler: Processing stage {memory.stage.value}")

        # Route to appropriate handler based on stage
        if memory.stage == Stage.CONFIRM_EMAIL_QUERY:
            return await self._handle_confirm_email_query(memory, user_input)
        elif memory.stage == Stage.NEED_EMAIL_QUERY:
            return await self._handle_need_email_query(memory, user_input)
        else:
            # Initial send_email request (from NEED_WRITE_OR_EMAIL)
            return await self._handle_initial_request(memory, user_input)

    async def _handle_initial_request(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle initial send_email request - gather params."""
        logger.info("SendEmailHandler: Processing initial send_email request")
        
        # Clear params only when switching from read_sql (has execute_query or write_count params)
        has_read_sql_params = "execute_query" in memory.gathered_params or "write_count" in memory.gathered_params
        if has_read_sql_params:
            logger.info("Switching from read_sql to send_email, clearing gathered_params")
            memory.gathered_params = {}
            memory.last_question = None
        
        memory.current_tool = "send_email"
        logger.info("Processing send_email request...")
        
        # Get action from job agent
        action = call_job_agent(memory, user_input, tool_name="send_email")
        
        # Handle different action types
        if action.get("action") == "ASK":
            memory.last_question = action["question"]
            return self._create_result(memory, action["question"])
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "send_email":
            return await self._prepare_email_query_confirmation(memory)
        
        return self._create_result(memory, "Please provide email parameters.")
    
    async def _prepare_email_query_confirmation(self, memory: Memory) -> StageHandlerResult:
        """Prepare email query and ask for user confirmation."""
        logger.info("All email params gathered, preparing for query verification...")

        params = memory.gathered_params

        # Check if we have output_table_info (data was written to a table)
        if not memory.output_table_info:
            # No result table - block email for ReadSQL without WriteData
            logger.warning("No output_table_info - cannot send email without writing data first")
            memory.gathered_params = {}
            memory.current_tool = None
            memory.last_question = None
            return self._create_result(
                memory,
                "You need to write the data to a table first before sending an email.\n\nPlease use 'write' to save the ReadSQL results to a table, then you can send an email.\n\nWhat would you like to do? (write / done)"
            )

        # Generate query from output_table_info (result table, not the original SQL)
        schema = memory.output_table_info.get("schema")
        table = memory.output_table_info.get("table")
        auto_query = f"SELECT * FROM {schema}.{table}"
        logger.info(f"Auto-generated email query from result table: {auto_query}")

        # Store params for later execution after confirmation
        memory.pending_email_params = {
            "name": params.get("name", "Email_Results"),
            "to": params.get("to"),
            "subject": params.get("subject", "Query Results"),
            "text": params.get("text", "Please find the query results attached."),
            "cc": params.get("cc", ""),
            "query": auto_query
        }

        # Transition to confirmation stage
        memory.email_query_confirmed = False

        return self._create_result(
            memory,
            f"I will use this SQL query to fetch data from the result table:\n```sql\n{auto_query}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_EMAIL_QUERY
        )

    async def _handle_confirm_email_query(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle user's confirmation response for the email query."""
        user_lower = user_input.lower()

        if "yes" in user_lower or "ok" in user_lower or "correct" in user_lower:
            logger.info("User confirmed email query, executing send_email_job...")
            memory.email_query_confirmed = True
            return await self._execute_confirmed_email_job(memory)

        elif "no" in user_lower or "change" in user_lower or "modify" in user_lower:
            logger.info("User wants to modify the email query")
            return self._create_result(
                memory,
                "Please provide the SQL query you want to use for the email:",
                Stage.NEED_EMAIL_QUERY
            )

        else:
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to use this query or 'no' to provide a different one."
            )

    async def _handle_need_email_query(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle user providing their own SQL query for email."""
        user_query = user_input.strip()

        # Basic SQL validation
        if not any(keyword in user_query.lower() for keyword in ["select", "insert", "update", "delete", "create", "drop"]):
            return self._create_result(
                memory,
                "That doesn't look like a SQL query. Please provide a valid SQL statement:"
            )

        logger.info(f"User provided custom email query: {user_query}")

        # Update the pending params with user's query
        if memory.pending_email_params:
            memory.pending_email_params["query"] = user_query

        # Execute the job with user's query
        return await self._execute_confirmed_email_job(memory)

    async def _execute_confirmed_email_job(self, memory: Memory) -> StageHandlerResult:
        """Execute send_email job after query has been confirmed."""
        logger.info("Executing send_email_job with confirmed query...")
        
        try:
            params = memory.pending_email_params
            if not params:
                return self._create_result(
                    memory,
                    "Error: No email parameters found. Please try again.",
                    Stage.NEED_WRITE_OR_EMAIL
                )
            
            # Get connection ID
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                return self._create_result(
                    memory,
                    f"Error: Unknown connection '{memory.connection}'."
                )
            
            logger.info(f"Using connection: {memory.connection} (ID: {connection_id})")

            request = SendEmailLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": params.get("name", "Email_Results"),
                    "description": ""
                },
                variables=[SendEmailVariables(
                    query=params.get("query"),  # Use confirmed query
                    connection=connection_id,
                    to=params.get("to"),
                    subject=params.get("subject", "Query Results"),
                    text=params.get("text", "Please find the query results attached."),
                    attachment=True,
                    cc=params.get("cc", "")
                )]
            )
            
            result = await send_email_job(request)
            logger.info(f"send_email_job result: {json.dumps(result, indent=2, default=str)}")
            
            # Reset all email-related state
            memory.gathered_params = {}
            memory.current_tool = None
            memory.pending_email_params = None
            memory.email_query_confirmed = False
            memory.last_question = None
            
            return self._create_result(
                memory,
                f"Email job created! Results will be sent to {params.get('to')}!\nAnything else? (write / email / done)",
                Stage.NEED_WRITE_OR_EMAIL
            )
        
        except Exception as e:
            logger.error(f"Error in send_email: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"Error: {str(e)}\nPlease try again."
            )
