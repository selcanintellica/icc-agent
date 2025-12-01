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
        """Process the SendEmail workflow."""
        logger.info(f"📨 SendEmailHandler: Processing send_email request")
        
        # Clear params only when switching from read_sql (has execute_query or write_count params)
        has_read_sql_params = "execute_query" in memory.gathered_params or "write_count" in memory.gathered_params
        if has_read_sql_params:
            logger.info("🔄 Switching from read_sql to send_email, clearing gathered_params")
            memory.gathered_params = {}
            memory.last_question = None
        
        memory.current_tool = "send_email"
        logger.info("📧 Processing send_email request...")
        
        # Get action from job agent
        action = call_job_agent(memory, user_input, tool_name="send_email")
        
        # Handle different action types
        if action.get("action") == "ASK":
            memory.last_question = action["question"]
            return self._create_result(memory, action["question"])
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "send_email":
            return await self._execute_send_email_job(memory)
        
        return self._create_result(memory, "Please provide email parameters.")
    
    async def _execute_send_email_job(self, memory: Memory) -> StageHandlerResult:
        """Execute send_email job to email query results."""
        logger.info("⚡ Executing send_email_job...")
        
        try:
            params = memory.gathered_params
            
            # Get connection ID
            from src.utils.connections import get_connection_id
            connection_id = get_connection_id(memory.connection)
            if not connection_id:
                return self._create_result(
                    memory,
                    f"❌ Error: Unknown connection '{memory.connection}'."
                )
            
            # Create request and execute job
            request = SendEmailLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": params.get("name", "Email_Results"), "description": ""},
                variables=[SendEmailVariables(
                    query=memory.last_sql,
                    connection=connection_id,
                    to=params.get("to"),
                    subject=params.get("subject", "Query Results"),
                    text=params.get("text", "Please find the query results attached."),
                    attachment=True,
                    cc=params.get("cc", "")
                )]
            )
            
            result = await send_email_job(request)
            logger.info(f"📊 send_email_job result: {json.dumps(result, indent=2, default=str)}")
            
            # Clean up memory
            memory.gathered_params = {}
            memory.current_tool = None
            memory.last_question = None
            
            return self._create_result(
                memory,
                f"✅ Email sent to {params.get('to')}!\nAnything else? (write / done)"
            )
        
        except Exception as e:
            logger.error(f"❌ Error in send_email: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"❌ Error: {str(e)}\nPlease try again."
            )
