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
from src.ai.router.global_command_handler import GlobalCommandHandler
from src.ai.router.utils.edit_target_resolver import EditTargetResolver
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
        Stage.CONFIRM_SEND_EMAIL_JOB,
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
            # Check for global commands first (back, reset, edit, review)
            global_cmd = GlobalCommandHandler.check_global_command(memory, user_input)

            if global_cmd == "reset":
                result = GlobalCommandHandler.handle_reset(memory)
                return self._create_result(
                    memory,
                    result["message"],
                    result.get("transition_to")
                )

            elif global_cmd == "back":
                result = GlobalCommandHandler.handle_back(memory)

                # If we need to re-gather parameters (during parameter gathering)
                if result.get("re_gather"):
                    logger.info("Re-gathering parameters after back command")
                    # Continue below to re-run job agent with empty input
                    user_input = ""
                # If we transitioned to a new stage, re-run handler with empty input to trigger that stage's prompt
                elif result.get("transition_to"):
                    memory.stage = result["transition_to"]
                    logger.info(f"Re-running handler after back to stage: {memory.stage.value}")
                    return await self.handle(memory, "")  # Re-run with empty input
                else:
                    # No transition - just show the message
                    return self._create_result(memory, result["message"])

            elif global_cmd == "review":
                result = GlobalCommandHandler.handle_review(memory)
                return self._create_result(memory, result["message"])

            elif global_cmd == "edit":
                # If we're in confirmation stage, don't intercept - let ConfirmJobStrategy handle it
                if memory.stage != Stage.CONFIRM_SEND_EMAIL_JOB:
                    edit_resolver = EditTargetResolver()
                    result = GlobalCommandHandler.handle_edit(memory, user_input, edit_resolver)

                    # If editing a parameter during parameter gathering (no stage transition)
                    if not result.get("transition_to") and memory.current_tool:
                        logger.info("Edited parameter during parameter gathering - continuing to re-gather")
                        # Clear last_question to trigger fresh parameter gathering
                        memory.last_question = None
                        # Continue below to re-run job agent with empty input
                        user_input = ""
                    else:
                        return self._create_result(
                            memory,
                            result["message"],
                            result.get("transition_to")
                        )

            if memory.stage == Stage.CONFIRM_SEND_EMAIL_JOB:
                # Handle confirmation stage with ConfirmJobStrategy
                from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
                confirm_strategy = ConfirmJobStrategy(
                    job_type="send_email",
                    execution_callback=lambda m: self._execute_send_email_job_final(m)
                )
                return await confirm_strategy.execute(memory, user_input)
            elif memory.stage == Stage.CONFIRM_EMAIL_QUERY:
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
        logger.debug("SendEmailHandler: Processing initial send_email request")
        logger.debug(f"Current gathered_params: {memory.gathered_params}")
        logger.debug(f"User input: '{user_input}'")
        
        # Clear params only when switching from read_sql
        has_read_sql_params = "execute_query" in memory.gathered_params or "write_count" in memory.gathered_params
        if has_read_sql_params:
            logger.info("Switching from read_sql to send_email, clearing gathered_params")
            memory.gathered_params = {}
            memory.last_question = None
        
        memory.current_tool = "send_email"
        logger.debug("Calling job_agent for send_email")
        
        # Get action from job agent
        action = call_job_agent(memory, user_input, tool_name="send_email")
        logger.debug(f"Job agent returned: action={action.get('action')}, tool_name={action.get('tool_name')}")
        logger.debug(f"Question: {action.get('question')}")
        logger.debug(f"Updated params: {action.get('params')}")
        
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
        logger.debug(f"CONFIRM_EMAIL_QUERY: user input = '{user_input}'")
        user_lower = user_input.lower()

        # Check if we're in a "name retry" scenario (name was cleared after duplicate error)
        name_is_empty = not memory.gathered_params.get("name") or not memory.pending_email_params.get("name") if memory.pending_email_params else not memory.gathered_params.get("name")
        
        if name_is_empty and user_input.strip():
            # User is providing a new job name after duplicate error
            new_name = user_input.strip()
            logger.debug(f"Name retry scenario - using '{new_name}' as new job name")
            memory.gathered_params["name"] = new_name
            if memory.pending_email_params:
                memory.pending_email_params["name"] = new_name
            # Re-execute the job with the new name
            return await self._execute_confirmed_email_job(memory)

        if any(word in user_lower for word in ["yes", "ok", "correct"]):
            logger.info("User confirmed email query, executing send_email_job")
            memory.email_query_confirmed = True
            return await self._execute_confirmed_email_job(memory)

        elif any(word in user_lower for word in ["no", "change", "modify", "different"]):
            logger.info("User wants to modify the email query")
            return self._create_result(
                memory,
                "Please provide the SQL query you want to use for the email:",
                Stage.NEED_EMAIL_QUERY
            )

        else:
            logger.debug("Unclear confirmation, asking again")
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
        logger.info("Email query confirmed, transitioning to job confirmation")
        logger.debug(f"Pending params: {memory.pending_email_params}")
        logger.debug(f"Gathered params: {memory.gathered_params}")

        # First time here - show confirmation summary
        if memory.stage != Stage.CONFIRM_SEND_EMAIL_JOB:
            params = memory.pending_email_params
            if not params:
                logger.error("No pending_email_params found")
                return self._create_result(
                    memory,
                    "Email parameters not found. Please start over and provide the email details.",
                    Stage.NEED_WRITE_OR_EMAIL,
                    is_error=True
                )

            # Copy pending_email_params to gathered_params for confirmation strategy
            memory.gathered_params.update(params)
            memory.stage = Stage.CONFIRM_SEND_EMAIL_JOB

            # Show confirmation
            from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
            confirm_strategy = ConfirmJobStrategy(
                job_type="send_email",
                execution_callback=lambda m: self._execute_send_email_job_final(m)
            )
            return await confirm_strategy.execute(memory, "")

        # If we get here, it means we're being called from confirmation - should not happen
        return await self._execute_send_email_job_final(memory)

    async def _execute_send_email_job_final(self, memory: Memory) -> StageHandlerResult:
        """Actually execute the send_email job after confirmation."""
        logger.info("Executing SEND_EMAIL_JOB (after confirmation)")

        try:
            params = memory.gathered_params  # Use gathered_params (copied from pending)
            if not params:
                logger.error("No gathered_params found")
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
            
            if result.get("message") == "Success":
                job_id = result.get("job_id")
                job_folder = memory.job_folder  # Use session-level folder from config
                
                # Track job for rule creation
                memory.add_created_job(
                    job_id=job_id,
                    job_name=job_name,
                    job_type="send_email",
                    job_folder=job_folder
                )
                logger.info(f"Added send_email job to created_jobs: {job_name} (ID: {job_id})")
                
                # Reset email-specific params but keep output_table_info for subsequent emails
                memory.gathered_params = {}
                memory.current_tool = None
                memory.pending_email_params = None
                memory.email_query_confirmed = False
                memory.last_question = None
                # DON'T clear: connection, schema, output_table_info (needed for next email)
                
                to_email = params.get('to')
                
                # Check if we have multiple jobs for rule creation option
                created_jobs = memory.get_created_jobs()
                has_multiple_jobs = len(created_jobs) >= 2 if created_jobs else False
                
                if has_multiple_jobs:
                    response = (
                        f"Email job '{job_name}' created successfully!\n\n"
                        f"Results will be sent to: {to_email}\n"
                        f"Subject: {params.get('subject', 'Query Results')}\n\n"
                        f"What would you like to do next?\n"
                        f"- 'email' - Send another email\n"
                        f"- 'rule' - Create a rule from your jobs\n"
                        f"- 'done' - Finish"
                    )
                else:
                    response = (
                        f"Email job '{job_name}' created successfully!\n\n"
                        f"Results will be sent to: {to_email}\n"
                        f"Subject: {params.get('subject', 'Query Results')}\n\n"
                        f"What would you like to do next?\n"
                        f"- 'email' - Send another email\n"
                        f"- 'done' - Finish"
                    )
                return self._create_result(memory, response, Stage.NEED_WRITE_OR_EMAIL)
            else:
                error_msg = result.get("error", "Unknown error")
                return self._create_result(
                    memory,
                    f"Error creating SendEmail job: {error_msg}",
                    is_error=True
                )
        
        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate job name '{job_name}': {e}")
            # Clear only the name - keep all other params for retry
            memory.gathered_params["name"] = ""
            memory.last_question = None  # Trigger fresh prompt for name
            return self._create_result(
                memory,
                f"A job named '{job_name}' already exists. Please provide a different name:",
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
