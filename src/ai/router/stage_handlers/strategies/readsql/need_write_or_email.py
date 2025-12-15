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
        
        logger.debug(f"NEED_WRITE_OR_EMAIL: input='{user_input}'")
        logger.debug(f"current_tool={memory.current_tool}")
        logger.debug(f"gathered_params={memory.gathered_params}")
        logger.debug(f"last_question={memory.last_question}")
        
        # If actively gathering params for write or email, don't treat "no" as done
        actively_gathering = memory.current_tool in ["write_data", "send_email"] and memory.gathered_params
        
        if actively_gathering:
            logger.debug(f"Actively gathering params for {memory.current_tool}, not treating 'no' as done")
        else:
            # Check for direct "rule" request (user wants to create rule immediately)
            if "rule" in user_lower:
                logger.info("User wants to create a rule directly")
                memory.current_tool = None
                
                created_jobs = memory.get_created_jobs()
                if memory.has_multiple_jobs():
                    logger.info(f"User has {len(created_jobs)} jobs, proceeding to rule creation")
                    
                    # Build job list summary
                    job_list = "\n".join([f"  {i+1}. {j['name']} ({j['type']})" for i, j in enumerate(created_jobs)])
                    
                    response = (
                        f"You've created {len(created_jobs)} jobs in this session:\n"
                        f"{job_list}\n\n"
                        f"Would you like to create a Rule combining these jobs into a workflow? (yes/no)"
                    )
                    
                    return self._create_result(
                        memory,
                        response,
                        Stage.ASK_CREATE_RULE
                    )
                else:
                    return self._create_result(
                        memory,
                        "You need at least 2 jobs to create a rule. Currently you have only one job.\n\n"
                        "What would you like to do?\n- 'email' - Send results via email\n- 'done' - Finish"
                    )
            
            # Check for "done" intent
            done_patterns = ["done", "finish", "complete", "nothing"]
            if (user_lower in ["no", "nope", "nah"] or 
                any(pattern in user_lower for pattern in done_patterns)):
                logger.info("User said done")
                memory.current_tool = None
                
                # Check if user has created multiple jobs - offer rule creation
                created_jobs = memory.get_created_jobs()
                logger.info(f"RULE_CHECK: created_jobs count = {len(created_jobs)}, jobs = {created_jobs}")
                
                if memory.has_multiple_jobs():
                    logger.info(f"User has {len(created_jobs)} jobs, offering rule creation")
                    
                    # Build job list summary
                    job_list = "\n".join([f"  {i+1}. {j['name']} ({j['type']})" for i, j in enumerate(created_jobs)])
                    
                    response = (
                        f"You've created {len(created_jobs)} jobs in this session:\n"
                        f"{job_list}\n\n"
                        f"Would you like to create a Rule combining these jobs into a workflow? (yes/no)"
                    )
                    
                    return self._create_result(
                        memory,
                        response,
                        Stage.ASK_CREATE_RULE
                    )
                else:
                    # Only one or no jobs - go directly to done
                    return self._create_result(
                        memory,
                        "All done! Say 'new query' or 'start' to begin a fresh job.",
                        Stage.DONE
                    )
        
        if memory.execute_query_enabled and any(word in user_lower for word in ["write", "save"]):
            return self._create_result(
                memory,
                "Data was already written to the table by the ReadSQL job.\n\nWhat would you like to do next?\n- 'email' - Send results via email\n- 'done' - Finish"
            )
        
        wants_write = memory.current_tool == "write_data" or any(word in user_lower for word in ["write", "save"])
        wants_email = memory.current_tool == "send_email" or any(word in user_lower for word in ["email", "send", "mail"])
        
        logger.debug(f"Intent detection: wants_write={wants_write}, wants_email={wants_email}")
        
        if wants_write:
            memory.current_tool = "write_data"
            logger.debug("Delegating to WriteDataHandler")
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_WRITEDATA__",
                next_stage=memory.stage
            )
        elif wants_email:
            memory.current_tool = "send_email"
            logger.debug("Delegating to SendEmailHandler")
            return StageHandlerResult(
                memory=memory,
                response="__DELEGATE_TO_SENDEMAIL__",
                next_stage=memory.stage
            )
        
        # Build help message based on available options
        created_jobs = memory.get_created_jobs()
        has_multiple_jobs = len(created_jobs) >= 2 if created_jobs else False
        
        if has_multiple_jobs:
            return self._create_result(
                memory,
                "Please specify what you'd like to do:\n- 'write' - Save to a table\n- 'email' - Send via email\n- 'rule' - Create a rule from your jobs\n- 'done' - Finish"
            )
        else:
            return self._create_result(
                memory,
                "Please specify what you'd like to do:\n- 'write' - Save to a table\n- 'email' - Send via email\n- 'done' - Finish"
            )
