"""Strategy for NEED_WRITE_OR_EMAIL stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class NeedWriteOrEmailStrategy(StageStrategy):
    """Handle post-execution options (write/email/done)."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle user's choice for next action after SQL execution.
        
        User can:
        - Write results to a table
        - Send results via email
        - Finish the workflow
        """
        user_lower = user_input.lower().strip()
        
        logger.info(f"📋 NEED_WRITE_OR_EMAIL: input='{user_input}'")
        logger.info(f"📋 current_tool={memory.current_tool}")
        logger.info(f"📋 gathered_params={memory.gathered_params}")
        logger.info(f"📋 last_question={memory.last_question}")
        
        # If actively gathering params for write or email, don't treat "no" as done
        actively_gathering = memory.current_tool in ["write_data", "send_email"] and memory.gathered_params
        
        if actively_gathering:
            logger.info(f"🔄 Actively gathering params for {memory.current_tool}, not treating 'no' as done")
        else:
            # Check for "done" intent
            done_patterns = ["done", "finish", "complete", "nothing"]
            if (user_lower in ["no", "nope", "nah"] or 
                any(pattern in user_lower for pattern in done_patterns)):
                logger.info("✅ User said done, transitioning to DONE stage")
                memory.current_tool = None
                return self._create_result(
                    memory,
                    "All done! 🎉\n\nSay 'new query' or 'start' to begin a fresh job.",
                    Stage.DONE
                )
        
        if memory.execute_query_enabled and any(word in user_lower for word in ["write", "save"]):
            return self._create_result(
                memory,
                "Data was already written to the table by the ReadSQL job.\n\nWhat would you like to do next?\n- 'email' - Send results via email\n- 'done' - Finish"
            )
        
        wants_write = memory.current_tool == "write_data" or any(word in user_lower for word in ["write", "save"])
        wants_email = memory.current_tool == "send_email" or any(word in user_lower for word in ["email", "send", "mail"])
        
        logger.info(f"🔍 Intent detection: wants_write={wants_write}, wants_email={wants_email}")
        
        if wants_write:
            memory.current_tool = "write_data"
            logger.info("📝 Delegating to WriteDataHandler...")
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_WRITEDATA__",
                next_stage=memory.stage
            )
        elif wants_email:
            memory.current_tool = "send_email"
            logger.info("📧 Delegating to SendEmailHandler...")
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_SENDEMAIL__",
                next_stage=memory.stage
            )
        
        return self._create_result(
            memory,
            "Please specify what you'd like to do:\n- 'write' - Save to a table\n- 'email' - Send via email\n- 'done' - Finish"
        )
