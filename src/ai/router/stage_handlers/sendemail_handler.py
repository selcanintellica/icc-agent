"""
SendEmail flow handler with comprehensive error handling.

Handles all stages related to emailing query results.
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
from src.errors import (
    ICCBaseError,
    UnknownConnectionError,
    DuplicateJobNameError,
    JobCreationFailedError,
    NetworkTimeoutError,
    MissingDatasetError,
    InvalidEmailError,
    ValidationError,
    ErrorHandler,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class SendEmailHandler(BaseStageHandler):
    """
    Handler for SendEmail workflow with comprehensive error handling.
    
    Following Single Responsibility Principle - only handles send_email operations.
    """
    
    MANAGED_STAGES = {
        Stage.CONFIRM_EMAIL_QUERY,
        Stage.NEED_EMAIL_QUERY,
    }
    
    # Note: NEED_WRITE_OR_EMAIL routing is handled by HandlerRegistry based on memory.current_tool
    
    def __init__(self, job_agent=None):
        """Initialize SendEmail handler."""
        self.job_agent = job_agent
    
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Note: NEED_WRITE_OR_EMAIL is routed by HandlerRegistry based on memory.current_tool
        """
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the SendEmail workflow based on current stage."""
        logger.info(f"SendEmailHandler: Processing stage {memory.stage.value}")
        logger.info(f"SendEmailHandler: current_tool={memory.current_tool}")

        try:
            if memory.stage == Stage.CONFIRM_EMAIL_QUERY:
                return await self._handle_confirm_email_query(memory, user_input)
            elif memory.stage == Stage.NEED_EMAIL_QUERY:
                return await self._handle_need_email_query(memory, user_input)
            elif memory.stage == Stage.NEED_WRITE_OR_EMAIL:
                # This should only happen when routed here by HandlerRegistry
                logger.info("SendEmailHandler handling NEED_WRITE_OR_EMAIL (routed by current_tool)")
                return await self._handle_initial_request(memory, user_input)
            else:
                logger.warning(f"SendEmailHandler received unexpected stage: {memory.stage.value}")
                return await self._handle_initial_request(memory, user_input)
                
        except ICCBaseError as e:
            logger.error(f"ICC error in SendEmail handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in SendEmail handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while setting up the email. Please try again."
            )

    async def _handle_initial_request(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle initial send_email request - gather params."""
        logger.info("SendEmailHandler: Processing initial send_email request")
        logger.info(f"📧 Current gathered_params: {memory.gathered_params}")
        logger.info(f"📧 User input: '{user_input}'")
        
        # Clear params only when switching from read_sql
        has_read_sql_params = "execute_query" in memory.gathered_params or "write_count" in memory.gathered_params
        if has_read_sql_params:
            logger.info("Switching from read_sql to send_email, clearing gathered_params")
            memory.gathered_params = {}
            memory.last_question = None
        
        memory.current_tool = "send_email"
        logger.info("📧 Calling job_agent for send_email...")
        
        # Get action from job agent
        action = call_job_agent(memory, user_input, tool_name="send_email")
        logger.info(f"📧 Job agent returned: action={action.get('action')}, tool_name={action.get('tool_name')}")
        logger.info(f"📧 Question: {action.get('question')}")
        logger.info(f"📧 Updated params: {action.get('params')}")
        
        # Handle different action types
        if action.get("action") == "ASK":
            memory.last_question = action["question"]
            return self._create_result(memory, action["question"])
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "send_email":
            return await self._prepare_email_query_confirmation(memory)
        
        return self._create_result(memory, "Please provide the email parameters. What should I name this email job?")
    
    async def _prepare_email_query_confirmation(self, memory: Memory) -> StageHandlerResult:
        """Prepare email query and ask for user confirmation."""
        logger.info("All email params gathered, preparing for query verification...")

        params = memory.gathered_params

        # Validate email address
        to_email = params.get("to", "")
        if not self._is_valid_email(to_email):
            return self._create_result(
                memory,
                f"The email address '{to_email}' doesn't appear to be valid. Please provide a valid email address:",
                is_error=True,
                error_code=ErrorCode.VAL_INVALID_EMAIL.code
            )

        # Check if we have output_table_info (data was written to a table)
        if not memory.output_table_info:
            logger.warning("No output_table_info - cannot send email without writing data first")
            memory.gathered_params = {}
            memory.current_tool = None
            memory.last_question = None
            return self._create_result(
                memory,
                "You need to write the data to a table first before sending an email.\n\n"
                "Please use 'write' to save the ReadSQL results to a table, then you can send an email.\n\n"
                "What would you like to do?\n- 'write' - Save data to a table\n- 'done' - Finish",
                is_error=True,
                error_code=ErrorCode.JOB_MISSING_DATASET.code
            )

        # Generate query from output_table_info
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

        memory.email_query_confirmed = False

        return self._create_result(
            memory,
            f"I will use this SQL query to fetch data for the email:\n```sql\n{auto_query}\n```\nIs this correct? (yes/no)",
            Stage.CONFIRM_EMAIL_QUERY
        )

    async def _handle_confirm_email_query(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle user's confirmation response for the email query."""
        logger.info(f"📧 CONFIRM_EMAIL_QUERY: user input = '{user_input}'")
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["yes", "ok", "correct"]):
            logger.info("✅ User confirmed email query, executing send_email_job...")
            memory.email_query_confirmed = True
            return await self._execute_confirmed_email_job(memory)

        elif any(word in user_lower for word in ["no", "change", "modify", "different"]):
            logger.info("🔄 User wants to modify the email query")
            return self._create_result(
                memory,
                "Please provide the SQL query you want to use for the email:",
                Stage.NEED_EMAIL_QUERY
            )

        else:
            logger.info("❓ Unclear confirmation, asking again")
            return self._create_result(
                memory,
                "Please confirm: Say 'yes' to use this query or 'no' to provide a different one."
            )

    async def _handle_need_email_query(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle user providing their own SQL query for email."""
        user_query = user_input.strip()

        if not user_query:
            return self._create_result(
                memory,
                "Please provide your SQL query:"
            )

        # Basic SQL validation
        sql_lower = user_query.lower()
        valid_keywords = ["select", "insert", "update", "delete", "create", "drop", "alter", "with"]
        
        if not any(sql_lower.startswith(kw) or f" {kw} " in sql_lower for kw in valid_keywords):
            return self._create_result(
                memory,
                "That doesn't look like a valid SQL query. Please provide a SQL statement:"
            )

        logger.info(f"User provided custom email query: {user_query}")

        # Update the pending params with user's query
        if memory.pending_email_params:
            memory.pending_email_params["query"] = user_query

        return await self._execute_confirmed_email_job(memory)

    async def _execute_confirmed_email_job(self, memory: Memory) -> StageHandlerResult:
        """Execute send_email job after query has been confirmed."""
        logger.info("📧 ========== EXECUTING SEND_EMAIL_JOB ==========")
        logger.info(f"📧 Pending params: {memory.pending_email_params}")
        logger.info(f"📧 Gathered params: {memory.gathered_params}")
        
        try:
            params = memory.pending_email_params
            if not params:
                logger.error("❌ No pending_email_params found!")
                return self._create_result(
                    memory,
                    "Email parameters not found. Please start over and provide the email details.",
                    Stage.NEED_WRITE_OR_EMAIL,
                    is_error=True
                )
            
            job_name = params.get("name", "Email_Results")
            
            # Get connection ID
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            
            if not connection_id:
                raise UnknownConnectionError(
                    connection_name=memory.connection,
                    user_message=f"The connection '{memory.connection}' was not found. Please select a valid connection."
                )
            
            logger.info(f"Using connection: {memory.connection} (ID: {connection_id})")

            request = SendEmailLLMRequest(
                rights={"owner": "184431757886694"},
                props={
                    "active": "true",
                    "name": job_name,
                    "description": ""
                },
                variables=[SendEmailVariables(
                    query=params.get("query"),
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
            
            # Reset email-specific params but keep output_table_info for subsequent emails
            memory.gathered_params = {}
            memory.current_tool = None
            memory.pending_email_params = None
            memory.email_query_confirmed = False
            memory.last_question = None
            # DON'T clear: connection, schema, output_table_info (needed for next email)
            
            to_email = params.get('to')
            response = (
                f"✅ Email job '{job_name}' created successfully!\n\n"
                f"Results will be sent to: {to_email}\n"
                f"Subject: {params.get('subject', 'Query Results')}\n\n"
                f"Would you like to continue? (Type 'yes')\n- 'email' - Send another email\n- 'done' - Finish"
            )
            return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
        
        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name: {e}")
            memory.gathered_params["name"] = ""  # Clear name to ask again
            return self._create_result(
                memory,
                e.user_message + "\n\nWhat would you like to name this email job instead?",
                is_error=True,
                error_code=e.code
            )
        
        except UnknownConnectionError as e:
            logger.error(f"Unknown connection: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout: {e}")
            return self._create_result(
                memory,
                e.user_message + "\n\nPlease try again.",
                is_error=True,
                error_code=e.code
            )
        
        except ICCBaseError as e:
            logger.error(f"ICC error in send_email: {e}")
            return self._create_result(
                memory,
                e.user_message,
                is_error=True,
                error_code=e.code
            )
        
        except Exception as e:
            logger.error(f"Error in send_email: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                self._format_job_error("SendEmail", e, params.get("name")),
                is_error=True
            )
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        if not email:
            return False
        
        # Simple check for @ and .
        if "@" not in email or "." not in email:
            return False
        
        # Check format
        parts = email.split("@")
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if "." not in domain:
            return False
        
        return True
