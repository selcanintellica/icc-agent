"""
Rule creation flow handler.

Handles all stages related to creating rules from jobs created during a chat session.
"""

import logging
import json
from typing import Dict, Any, List, Optional

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.utils.folder_api_client import (
    fetch_folders,
    format_folders_for_display,
    get_folder_by_selection
)
from src.models.rule import RuleBuilder, RulePayload
from src.repositories.rule_repository import save_rule
from src.errors import (
    ICCBaseError,
    DuplicateJobNameError,
    NetworkTimeoutError,
    APIUnavailableError,
    ErrorHandler,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class RuleHandler(BaseStageHandler):
    """
    Handler for Rule creation workflow.
    
    Manages the flow:
    1. ASK_CREATE_RULE: Ask if user wants to create a rule
    2. ASK_RULE_FOLDER: Show folder list and let user select
    3. ASK_RULE_NAME: Ask for rule name
    4. EXECUTE_RULE_CREATION: Build and save the rule
    """
    
    MANAGED_STAGES = {
        Stage.ASK_CREATE_RULE,
        Stage.ASK_RULE_FOLDER,
        Stage.ASK_RULE_NAME,
        Stage.EXECUTE_RULE_CREATION,
    }
    
    def __init__(self):
        """Initialize Rule handler."""
        # Store fetched folders for the session
        self._cached_folders: List[Dict[str, str]] = []
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the Rule creation workflow based on current stage."""
        logger.info(f"RuleHandler: Processing stage {memory.stage.value}")
        
        try:
            if memory.stage == Stage.ASK_CREATE_RULE:
                return await self._handle_ask_create_rule(memory, user_input)
            elif memory.stage == Stage.ASK_RULE_FOLDER:
                return await self._handle_ask_rule_folder(memory, user_input)
            elif memory.stage == Stage.ASK_RULE_NAME:
                return await self._handle_ask_rule_name(memory, user_input)
            elif memory.stage == Stage.EXECUTE_RULE_CREATION:
                return await self._handle_execute_rule_creation(memory, user_input)
            else:
                logger.warning(f"RuleHandler received unexpected stage: {memory.stage.value}")
                return self._create_result(
                    memory,
                    "Unexpected state. Say 'new query' to start fresh.",
                    Stage.DONE
                )
                
        except ICCBaseError as e:
            logger.error(f"ICC error in Rule handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in Rule handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while creating the rule. Please try again."
            )
    
    async def _handle_ask_create_rule(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle ASK_CREATE_RULE stage.
        
        User has already been shown the jobs list and asked if they want to create a rule.
        This handler processes their yes/no response.
        """
        user_lower = user_input.lower().strip()
        
        logger.info(f"ASK_CREATE_RULE: user_input='{user_input}'")
        
        # Check for positive response
        if any(word in user_lower for word in ["yes", "y", "ok", "sure", "create", "rule", "yeah"]):
            logger.info("User wants to create a rule")
            return await self._fetch_and_show_folders(memory)
        
        # Check for negative response
        if any(word in user_lower for word in ["no", "n", "nope", "skip", "done", "finish", "nah"]):
            logger.info("User declined rule creation")
            return self._create_result(
                memory,
                "All done! Say 'new query' or 'start' to begin a fresh job.",
                Stage.DONE
            )
        
        # Unclear response - ask again
        jobs = memory.get_created_jobs()
        job_count = len(jobs) if jobs else 0
        
        return self._create_result(
            memory,
            f"Would you like to create a Rule from your {job_count} jobs? Please respond 'yes' or 'no':"
        )
    
    async def _fetch_and_show_folders(self, memory: Memory) -> StageHandlerResult:
        """Fetch folders from API and show selection list."""
        logger.info("Fetching folders for rule creation")
        
        try:
            # Get authentication
            from src.utils.auth import authenticate
            
            auth_result = await authenticate()
            if auth_result:
                userpass, token = auth_result
                auth_headers = {
                    "Authorization": f"Basic {userpass}",
                    "TokenKey": token
                }
            else:
                auth_headers = None
                logger.warning("No authentication available for folder fetch")
            
            # Fetch folders
            folders = await fetch_folders(auth_headers=auth_headers)
            
            if not folders:
                logger.warning("No folders available")
                return self._create_result(
                    memory,
                    "Unable to fetch folders. Please try again or say 'skip' to finish without creating a rule.",
                    is_error=True
                )
            
            # Cache folders for selection
            self._cached_folders = folders
            
            # Store in memory for persistence
            memory.gathered_params["available_folders"] = folders
            
            # Format and display
            folder_display = format_folders_for_display(folders)
            
            response = (
                f"{folder_display}\n\n"
                f"Enter the number or name of the folder where you want to save the rule:"
            )
            
            return self._create_result(memory, response, Stage.ASK_RULE_FOLDER)
            
        except Exception as e:
            logger.error(f"Error fetching folders: {e}", exc_info=True)
            return self._create_result(
                memory,
                f"Error fetching folders: {str(e)}\n\nPlease try again or say 'skip' to finish.",
                is_error=True
            )
    
    async def _handle_ask_rule_folder(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle ASK_RULE_FOLDER stage.
        
        User selects a folder from the list.
        """
        user_lower = user_input.lower().strip()
        
        # Check for skip/cancel
        if user_lower in ["skip", "cancel", "back", "no"]:
            return self._create_result(
                memory,
                "Rule creation cancelled. Say 'new query' or 'start' to begin fresh.",
                Stage.DONE
            )
        
        # Get folders from cache or memory
        folders = self._cached_folders or memory.gathered_params.get("available_folders", [])
        
        if not folders:
            # Need to re-fetch
            return await self._fetch_and_show_folders(memory)
        
        # Try to match user selection
        selected_folder = get_folder_by_selection(folders, user_input)
        
        if not selected_folder:
            return self._create_result(
                memory,
                f"Could not find folder '{user_input}'. Please enter a valid number or folder name:"
            )
        
        # Store selected folder
        memory.gathered_params["rule_folder_id"] = selected_folder["id"]
        memory.gathered_params["rule_folder_name"] = selected_folder["name"]
        
        logger.info(f"User selected folder: {selected_folder['name']} (ID: {selected_folder['id']})")
        
        response = f"Selected folder: {selected_folder['name']}\n\nWhat would you like to name this rule?"
        
        return self._create_result(memory, response, Stage.ASK_RULE_NAME)
    
    async def _handle_ask_rule_name(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle ASK_RULE_NAME stage.
        
        User provides the rule name.
        """
        user_lower = user_input.lower().strip()
        
        # Check for skip/cancel
        if user_lower in ["skip", "cancel", "back"]:
            return self._create_result(
                memory,
                "Rule creation cancelled. Say 'new query' or 'start' to begin fresh.",
                Stage.DONE
            )
        
        rule_name = user_input.strip()
        
        if not rule_name:
            return self._create_result(
                memory,
                "Please provide a name for the rule:"
            )
        
        # Validate name (basic validation)
        if len(rule_name) < 2:
            return self._create_result(
                memory,
                "Rule name is too short. Please provide a longer name:"
            )
        
        if len(rule_name) > 100:
            return self._create_result(
                memory,
                "Rule name is too long. Please provide a shorter name (max 100 characters):"
            )
        
        # Store rule name
        memory.gathered_params["rule_name"] = rule_name
        
        logger.info(f"User provided rule name: {rule_name}")
        
        # Proceed to execute
        return await self._execute_rule_creation(memory)
    
    async def _handle_execute_rule_creation(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Handle EXECUTE_RULE_CREATION stage.
        
        Build and save the rule.
        """
        # This stage is usually reached via transition, not direct user input
        # But handle user input for retry scenarios
        
        if user_input.lower().strip() in ["retry", "yes", "ok"]:
            return await self._execute_rule_creation(memory)
        
        if user_input.lower().strip() in ["cancel", "no", "skip"]:
            return self._create_result(
                memory,
                "Rule creation cancelled. Say 'new query' or 'start' to begin fresh.",
                Stage.DONE
            )
        
        # Try to execute
        return await self._execute_rule_creation(memory)
    
    async def _execute_rule_creation(self, memory: Memory) -> StageHandlerResult:
        """Execute the rule creation."""
        logger.info("Executing rule creation...")
        
        jobs = memory.get_created_jobs()
        folder_id = memory.gathered_params.get("rule_folder_id")
        folder_name = memory.gathered_params.get("rule_folder_name")
        rule_name = memory.gathered_params.get("rule_name")
        
        # Validate all required data
        if not jobs or len(jobs) < 2:
            return self._create_result(
                memory,
                "Not enough jobs to create a rule. At least 2 jobs are required.",
                Stage.DONE,
                is_error=True
            )
        
        if not folder_id:
            return await self._fetch_and_show_folders(memory)
        
        if not rule_name:
            return self._create_result(
                memory,
                "What would you like to name this rule?",
                Stage.ASK_RULE_NAME
            )
        
        try:
            # Get authentication
            from src.utils.auth import authenticate
            
            auth_result = await authenticate()
            if auth_result:
                userpass, token = auth_result
                auth_headers = {
                    "Authorization": f"Basic {userpass}",
                    "TokenKey": token
                }
            else:
                auth_headers = None
                logger.warning("No authentication available for rule save")
            
            # Build rule payload
            logger.info(f"Building rule payload: name={rule_name}, folder={folder_id}, jobs={len(jobs)}")
            logger.info(f"Jobs being used: {jobs}")
            
            payload = RuleBuilder.build(
                jobs=jobs,
                folder_id=folder_id,
                rule_name=rule_name
            )
            
            # Log the full detail for debugging
            logger.info(f"Rule payload detail (FULL): {payload.detail}")
            logger.info(f"Rule payload as API: {payload.to_api_payload()}")
            
            # Save rule
            result = await save_rule(payload, auth_headers=auth_headers)
            
            if result.get("message") == "Success":
                rule_id = result.get("rule_id")
                flow_description = RuleBuilder.format_flow_description(jobs)
                
                logger.info(f"Rule '{rule_name}' created successfully (ID: {rule_id})")
                
                # Clear rule-related params
                memory.gathered_params.pop("rule_folder_id", None)
                memory.gathered_params.pop("rule_folder_name", None)
                memory.gathered_params.pop("rule_name", None)
                memory.gathered_params.pop("available_folders", None)
                
                response = (
                    f"Rule '{rule_name}' created successfully!\n\n"
                    f"Flow: {flow_description}\n"
                    f"Saved to folder: {folder_name}\n"
                    f"Rule ID: {rule_id}\n\n"
                    f"Say 'new query' or 'start' to begin fresh."
                )
                
                return self._create_result(memory, response, Stage.DONE)
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Rule creation failed: {error_msg}")
                return self._create_result(
                    memory,
                    f"Error creating rule: {error_msg}\n\nSay 'retry' to try again or 'cancel' to skip.",
                    is_error=True
                )
                
        except DuplicateJobNameError as e:
            logger.warning(f"Duplicate rule name '{rule_name}': {e}")
            memory.gathered_params["rule_name"] = ""
            return self._create_result(
                memory,
                f"A rule named '{rule_name}' already exists. Please provide a different name:",
                Stage.ASK_RULE_NAME,
                is_error=True,
                error_code=e.code
            )
        
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout creating rule: {e}")
            return self._create_result(
                memory,
                f"{e.user_message}\n\nSay 'retry' to try again or 'cancel' to skip.",
                is_error=True,
                error_code=e.code
            )
        
        except APIUnavailableError as e:
            logger.error(f"API unavailable: {e}")
            return self._create_result(
                memory,
                f"{e.user_message}\n\nSay 'retry' to try again or 'cancel' to skip.",
                is_error=True,
                error_code=e.code
            )
        
        except ICCBaseError as e:
            logger.error(f"ICC error creating rule: {e}")
            return self._create_result(
                memory,
                f"{e.user_message}\n\nSay 'retry' to try again or 'cancel' to skip.",
                is_error=True,
                error_code=e.code
            )
        
        except Exception as e:
            logger.error(f"Error creating rule: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"Error creating rule: {str(e)}\n\nSay 'retry' to try again or 'cancel' to skip.",
                is_error=True
            )
    
    def _format_jobs_for_display(self, jobs: List[Dict[str, str]]) -> str:
        """Format jobs as a numbered list for display."""
        lines = []
        for i, job in enumerate(jobs, 1):
            job_type = job.get("type", "unknown").replace("_", " ").title()
            lines.append(f"  {i}. {job['name']} ({job_type})")
        return "\n".join(lines)

