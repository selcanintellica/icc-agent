"""
Refactored Job Agent with Dependency Injection and Error Handling.

This module provides job parameter gathering following SOLID principles with:
- Structured error handling
- Retry logic for LLM calls
- User-friendly error messages
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from src.ai.router.memory import Memory
from src.ai.router.prompts import PromptManager
from src.ai.router.validators import ParameterValidator, YesNoExtractor
from src.utils.retry import retry, RetryPresets, RetryExhaustedError
from src.errors import (
    LLMError,
    LLMTimeoutError,
    LLMParsingError,
    LLMUnavailableError,
    InvalidJSONError,
    ValidationError,
    MissingParameterError,
    ErrorCode,
    ErrorHandler,
)
from src.utils.prompt_logger import get_prompt_logger, is_prompt_logging_enabled

logger = logging.getLogger(__name__)


class JobAgentConfig:
    """Configuration for JobAgent following SRP."""
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434",
        num_predict: int = 4096,
        timeout: float = 30.0
    ):
        self.model_name = model_name or os.getenv("MODEL_NAME", "qwen3:8b")
        self.temperature = temperature
        self.base_url = base_url
        self.num_predict = num_predict
        self.timeout = timeout


class JobAgent:
    """
    Agent that gathers parameters for job execution with error handling.
    
    Refactored following SOLID principles with:
    - Dependency injection
    - Retry logic for LLM calls
    - Structured error handling
    """
    
    def __init__(
        self,
        config: Optional[JobAgentConfig] = None,
        prompt_manager: Optional[PromptManager] = None,
        validator: Optional[ParameterValidator] = None
    ):
        """
        Initialize JobAgent with dependency injection.
        
        Args:
            config: Configuration for the agent
            prompt_manager: Manager for prompts
            validator: Validator for parameters
        """
        self.config = config or JobAgentConfig()
        self.prompt_manager = prompt_manager or PromptManager()
        self.validator = validator or ParameterValidator()
        
        self.llm = ChatOllama(
            model=self.config.model_name,
            temperature=self.config.temperature,
            base_url=self.config.base_url,
            num_predict=self.config.num_predict,
            timeout=self.config.timeout,
            keep_alive="3600s",
            model_kwargs={
                "think": False,
                "stream": True
            }
        )
    
    def gather_params(
        self,
        memory: Memory,
        user_input: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Extract parameters from user input and determine next action.
        
        Handles three types of input:
        1. Yes/No answers (instant extraction)
        2. Conversational input (questions, clarifications, off-topic)
        3. Parameter values (LLM extraction)
        
        Args:
            memory: Conversation memory with context
            user_input: Latest user message
            tool_name: Which tool we're gathering params for
            
        Returns:
            Dict with action (ASK/TOOL/FETCH_SCHEMAS/CHAT), question, params, etc.
        """
        logger.info(f"Job Agent: Gathering params for '{tool_name}'")
        logger.info(f"Current params: {memory.gathered_params}")

        try:
            # Check for edit/back commands - allow user to correct parameters
            edit_result = self._check_edit_commands(memory, user_input, tool_name)
            if edit_result:
                return edit_result
            
            # Check if schema was directly selected via dropdown (bypass LLM)
            if user_input.startswith("__SCHEMA_SELECTED__:"):
                schema_name = user_input.replace("__SCHEMA_SELECTED__:", "").strip()
                logger.info(f"✅ Schema directly selected via dropdown: {schema_name} (already assigned)")
                # Schema already assigned in app.py, just validate to get next question
                return self._validate_params(memory, tool_name, user_input="")

            # Check if connection was directly selected via dropdown (bypass LLM)
            if user_input.startswith("__CONNECTION_SELECTED__:"):
                connection_name = user_input.replace("__CONNECTION_SELECTED__:", "").strip()
                logger.info(f"✅ Connection directly selected via dropdown: {connection_name} (already assigned)")
                # Connection already assigned in app.py, just validate to get next question
                return self._validate_params(memory, tool_name, user_input="")

            # Check for direct yes/no answers first (fastest)
            if YesNoExtractor.extract_boolean(user_input, memory, tool_name):
                # Re-run validation to get next question
                return self._validate_params(memory, tool_name, user_input="")

            # Skip LLM only for simple commands when params are empty
            user_input_lower = user_input.lower().strip()
            simple_commands = {"write", "email", "send", "done", "finish", "complete", "both"}

            if not memory.gathered_params and user_input_lower in simple_commands:
                logger.info(f"📝 Skipping LLM extraction for command: '{user_input}'")
                return self._validate_params(memory, tool_name, user_input="")

            result = self._extract_with_llm(memory, user_input, tool_name)
            
            # Normalize schemas if it's a list
            if "params" in result and result["params"]:
                params = result["params"]
                if "schemas" in params and isinstance(params["schemas"], list):
                    params["schemas"] = params["schemas"][0] if params["schemas"] else ""
                    logger.info(f"Normalized schemas from list to string: {params['schemas']}")
                
                # Update memory with non-None values
                # Pydantic will handle validation of empty strings vs missing values
                new_params = {k: v for k, v in params.items() if v is not None}
                memory.gathered_params.update(new_params)
                logger.info(f"✅ Updated gathered_params: {memory.gathered_params}")
            
            logger.info(f"🤖 Job Agent action: {result.get('action')}, tool: {result.get('tool_name')}")
            logger.info(f"🤖 Extracted params: {result.get('params')}")
            
            # If this was conversational input with ASK action and a question, return it directly
            # Don't override with validation
            if result.get('action') == 'ASK' and result.get('question') and self._is_conversational_input(user_input):
                logger.info("💬 Returning conversational response directly (skipping validation override)")
                return result
            
            # After extracting params, validate to get the correct next question
            logger.info(f"🔍 Validating params for {tool_name}...")
            validation_result = self._validate_params(memory, tool_name, user_input)
            logger.info(f"🔍 Validation result: action={validation_result.get('action')}, question={validation_result.get('question', 'N/A')[:50]}...")
            return validation_result

        except LLMError as e:
            logger.error(f"LLM error in job agent: {e}")
            # Return validation result with error context
            result = self._validate_params(memory, tool_name, user_input)
            if "error" not in result:
                result["error"] = e.user_message
            return result

        except Exception as e:
            logger.error(f"Job Agent unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
            # Convert to ICC error and continue with validation
            icc_error = ErrorHandler.handle(e, {"tool_name": tool_name})
            result = self._validate_params(memory, tool_name, user_input)
            if "error" not in result:
                result["error"] = icc_error.user_message
            return result
    
    def _check_edit_commands(self, memory: Memory, user_input: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if user wants to go back and edit a previous parameter.
        
        Supports:
        - "back" / "go back" - remove last parameter and re-ask
        - "edit <param>" / "change <param>" - edit specific parameter
        - "reset" / "start over" - clear all parameters
        
        Args:
            memory: Conversation memory
            user_input: User's input
            tool_name: Current tool name
            
        Returns:
            Dict with action=ASK if edit command detected, None otherwise
        """
        input_lower = user_input.lower().strip()
        
        # Reset/start over - clear all parameters
        if input_lower in ["reset", "start over", "restart", "clear all"]:
            if not memory.gathered_params:
                return {
                    "action": "ASK",
                    "question": "No parameters have been set yet. Let's start fresh!",
                    "params": {},
                    "tool_name": tool_name
                }
            
            logger.info(f"🔄 User requested reset, clearing all parameters: {list(memory.gathered_params.keys())}")
            param_names = list(memory.gathered_params.keys())
            memory.gathered_params.clear()
            
            # Get first question again
            validation = self._validate_params(memory, tool_name, user_input="")
            validation["question"] = f"✅ Cleared parameters: {', '.join(param_names)}\n\n{validation.get('question', 'Let\'s start over.')}"
            return validation
        
        # Go back - remove last parameter
        if input_lower in ["back", "go back", "undo", "previous"]:
            if not memory.gathered_params:
                return {
                    "action": "ASK",
                    "question": "No parameters to go back to. Let's continue from here.",
                    "params": {},
                    "tool_name": tool_name
                }
            
            # Remove the last added parameter
            last_param = list(memory.gathered_params.keys())[-1]
            old_value = memory.gathered_params.pop(last_param)
            logger.info(f"⬅️ User went back, removed: {last_param}={old_value}")
            
            # Get the question for that parameter again
            validation = self._validate_params(memory, tool_name, user_input="")
            validation["question"] = f"✅ Removed: {last_param} = '{old_value}'\n\n{validation.get('question', 'What would you like for this parameter?')}"
            return validation
        
        # Edit specific parameter - use LLM to understand which parameter user wants to edit
        edit_patterns = ["edit ", "change ", "correct ", "fix ", "update "]
        for pattern in edit_patterns:
            if input_lower.startswith(pattern):
                # Use LLM to identify which parameter user wants to edit
                matched_param = self._identify_parameter_with_llm(user_input, memory.gathered_params)
                
                if matched_param:
                    old_value = memory.gathered_params.pop(matched_param)
                    logger.info(f"✏️ User editing parameter: {matched_param}={old_value} (from input: '{user_input}')")
                    
                    # Get the question for that parameter
                    validation = self._validate_params(memory, tool_name, user_input="")
                    validation["question"] = f"✅ Cleared: {matched_param} = '{old_value}'\n\n{validation.get('question', f'Please provide a new value for {matched_param}:')}"
                    return validation
                else:
                    available_params = ', '.join(memory.gathered_params.keys()) if memory.gathered_params else 'none'
                    return {
                        "action": "ASK",
                        "question": f"I couldn't identify which parameter you want to edit from '{user_input}'.\n\nAvailable parameters: {available_params}\n\nPlease be more specific, like:\n{chr(10).join(['- edit ' + p for p in list(memory.gathered_params.keys())[:3]]) if memory.gathered_params else '- No parameters set yet'}",
                        "params": {},
                        "tool_name": tool_name
                    }
        
        return None
    
    def _identify_parameter_with_llm(self, user_input: str, params: Dict[str, Any]) -> Optional[str]:
        """
        Use LLM to identify which parameter the user wants to edit.
        
        This handles natural language understanding:
        - "edit the job's name" → job_name
        - "change connection" → connection
        - "fix the folder" → folder
        - "update execute query" → execute_query
        - "edit name" → job_name (context-aware)
        
        Args:
            user_input: User's full input (e.g., "edit job name")
            params: Dictionary of currently gathered parameters
            
        Returns:
            Matched parameter name or None if can't determine
        """
        if not params:
            return None
        
        # Build prompt for LLM
        param_list = '\n'.join([f"- {key}: {value}" for key, value in params.items()])
        
        prompt = f"""You are helping identify which parameter a user wants to edit.

Current parameters:
{param_list}

User input: "{user_input}"

Identify which parameter the user wants to edit. Respond with ONLY the exact parameter name from the list above, or "NONE" if you cannot determine it.

Examples:
User: "edit job name" → job_name
User: "change the connection" → connection
User: "fix folder" → folder
User: "edit name" → job_name
User: "update execute" → execute_query
User: "change something random" → NONE

Response (parameter name only):"""

        try:
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            
            identified_param = response.content.strip()
            logger.info(f"🤖 LLM identified parameter: '{identified_param}' from input: '{user_input}'")
            
            # Validate LLM response
            if identified_param == "NONE" or not identified_param:
                logger.warning(f"LLM could not identify parameter from: {user_input}")
                return None
            
            # Check if identified param exists in actual params (case-insensitive)
            for param_key in params.keys():
                if param_key.lower() == identified_param.lower():
                    return param_key
            
            # LLM returned something not in params
            logger.warning(f"LLM returned '{identified_param}' but it's not in params: {list(params.keys())}")
            return None
            
        except Exception as e:
            logger.error(f"Error using LLM to identify parameter: {e}")
            # Fallback to simple fuzzy matching
            return self._simple_param_match(user_input, params)
    
    def _simple_param_match(self, user_input: str, params: Dict[str, Any]) -> Optional[str]:
        """
        Simple fallback matching if LLM fails.
        
        Args:
            user_input: User's input
            params: Dictionary of gathered parameters
            
        Returns:
            Matched parameter name or None
        """
        user_lower = user_input.lower().strip()
        
        # Remove edit keywords
        for keyword in ["edit ", "change ", "correct ", "fix ", "update "]:
            user_lower = user_lower.replace(keyword, "")
        
        user_lower = user_lower.strip().replace(" ", "_")
        
        # Try exact match
        if user_lower in params:
            return user_lower
        
        # Try contains
        for param in params.keys():
            if user_lower in param.lower() or param.lower() in user_lower:
                return param
        
        return None
    
    def _is_conversational_input(self, user_input: str) -> bool:
        """
        Detect if user input is conversational (question/clarification) vs parameter answer.
        
        Args:
            user_input: User's input
            
        Returns:
            True if conversational, False if likely parameter answer
        """
        input_lower = user_input.lower().strip()
        
        # Question indicators
        question_patterns = [
            "what", "why", "how", "when", "where", "who",
            "can you", "could you", "would you", "will you",
            "tell me", "explain", "show me", "help",
            "i don't understand", "i'm confused", "not sure",
            "i don't know", "i do not know", "don't know", "do not know",
            "no idea", "not certain", "unsure", "unclear",
            "what does", "what is", "what are",
            "?"
        ]
        
        # Off-topic indicators
        off_topic_patterns = [
            "weather", "news", "joke", "story",
            "changed my mind", "wait", "hold on", "stop",
            "forget", "cancel", "never mind"
        ]
        
        for pattern in question_patterns + off_topic_patterns:
            if pattern in input_lower:
                return True
        
        return False
    
    def _handle_conversation(
        self,
        memory: Memory,
        user_input: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Handle conversational input (questions, clarifications, off-topic).
        
        Args:
            memory: Conversation memory
            user_input: User's conversational input
            tool_name: Current tool name
            
        Returns:
            Dict with action=ASK and conversational response
        """
        logger.info(f"Detected conversational input: {user_input}")
        
        # Build context for conversational response
        context = f"""
You are helping the user configure a '{tool_name}' job.

Current progress:
{json.dumps(memory.gathered_params, indent=2)}

Last question asked: {memory.last_question or "(none yet)"}

The user said: "{user_input}"

Respond naturally to their question or comment, then remind them what we're working on and what information you still need.

Be conversational and helpful. After your response, restate the last question or ask the next needed parameter.

Output format:
{{
    "action": "ASK",
    "question": "Your conversational response here...",
    "params": {{}}
}}
"""
        
        try:
            result = self._invoke_llm_with_retry(context, is_conversation=True)
            logger.info(f"Conversational response: {result.get('question', '')[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"Conversation handling failed: {e}")
            # Fallback: acknowledge and continue
            return {
                "action": "ASK",
                "question": f"I understand. Let's continue with the {tool_name} configuration. {memory.last_question or 'What would you like to do next?'}",
                "params": {}
            }
    
    def _extract_with_llm(
        self,
        memory: Memory,
        user_input: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Use LLM to extract parameters from user input.
        
        Args:
            memory: Conversation memory
            user_input: User's input
            tool_name: Tool name
            
        Returns:
            Dict with extracted action and parameters
        """
        # Check if input is conversational (question/clarification)
        if self._is_conversational_input(user_input):
            return self._handle_conversation(memory, user_input, tool_name)

        # Get appropriate prompt for the tool
        if tool_name == "write_data":
            missing = self._get_missing_params_write_data(memory.gathered_params)
            
            # Only include connection list in system prompt if:
            # 1. We need connection AND it's not in last_question already
            # Check if write_count is enabled to add conditional hints
            write_count = memory.gathered_params.get("write_count", False)
            
            # Don't include connection list - we use dropdowns now
            system_prompt = self.prompt_manager.get_prompt("write_data", connections="", write_count=write_count)
            
            last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
            prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
            
        elif tool_name == "read_sql":
            missing = self._get_missing_params_read_sql(memory.gathered_params)

            # Check if execute_query or write_count is enabled to add conditional hints
            execute_query = memory.gathered_params.get("execute_query", False)
            write_count = memory.gathered_params.get("write_count", False)

            system_prompt = self.prompt_manager.get_prompt("read_sql", execute_query=execute_query, write_count=write_count)
            
            last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
            prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
            
        elif tool_name == "send_email":
            missing = self._get_missing_params_send_email(memory.gathered_params)
            system_prompt = self.prompt_manager.get_prompt("send_email")
            
            last_q = f'Last question: "{memory.last_question}"\n' if memory.last_question else ""
            prompt_text = f"""{last_q}User answer: "{user_input}"
Current: {json.dumps(memory.gathered_params)}
Missing: {', '.join(missing) if missing else 'none'}

Output JSON only:"""
            
        else:
            # Fallback to parameter extraction prompt
            system_prompt = self.prompt_manager.get_prompt("parameter_extraction")
            prompt_text = f"""Tool: {tool_name}
Current params: {json.dumps(memory.gathered_params)}
User said: "{user_input}"

IMPORTANT: Output ONLY the JSON response.

Extract parameters or ask for missing ones."""
        
        logger.info(f"Calling LLM with model: {self.config.model_name}")
        logger.debug(f"System prompt:\n{system_prompt}")
        logger.debug(f"User prompt:\n{prompt_text}")
        
        full_prompt = f"{system_prompt}\n\n{prompt_text}"
        return self._invoke_llm_with_retry(full_prompt)

    @retry(config=RetryPresets.LLM_CALL)
    def _invoke_llm_with_retry(
        self,
        prompt: str,
        is_conversation: bool = False
    ) -> Dict[str, Any]:
        """Invoke LLM with automatic retry on failure."""
        try:
            system_content = "You are a helpful assistant helping configure database jobs. Be friendly and concise." if is_conversation else "You are a parameter extraction assistant. Output JSON only."
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=prompt)
            ]
            
            # Log prompt if enabled
            if is_prompt_logging_enabled():
                get_prompt_logger().log_full_conversation(
                    agent_type="job_agent",
                    messages=messages,
                    metadata={
                        "model": self.config.model_name,
                        "temperature": self.config.temperature,
                        "is_conversation": is_conversation
                    }
                )

            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Log response if enabled
            if is_prompt_logging_enabled():
                get_prompt_logger().log_full_conversation(
                    agent_type="job_agent",
                    messages=messages,
                    response=content,
                    metadata={
                        "model": self.config.model_name,
                        "temperature": self.config.temperature,
                        "is_conversation": is_conversation
                    }
                )
            
            logger.info(f"Job Agent raw response: {content[:300]}...")
            
            if not content:
                raise LLMParsingError(
                    message="LLM returned empty response",
                    user_message="The AI returned an empty response. Please try again."
                )

            return self._parse_llm_response(content)

        except TimeoutError as e:
            raise LLMTimeoutError(
                message=f"Job agent LLM timeout: {e}",
                user_message="The AI is taking too long. Please try again.",
                timeout_seconds=self.config.timeout,
                cause=e
            )
        except ConnectionError as e:
            raise LLMUnavailableError(
                message=f"Could not connect to LLM: {e}",
                user_message="The AI assistant is currently unavailable. Please try again later.",
                model_name=self.config.model_name,
                cause=e
            )
        except (LLMError, InvalidJSONError):
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                raise LLMTimeoutError(
                    message=f"LLM timeout: {e}",
                    user_message="The AI is taking too long. Please try again.",
                    cause=e
                )
            if "connection" in error_str or "connect" in error_str:
                raise LLMUnavailableError(
                    message=f"LLM connection error: {e}",
                    user_message="Unable to connect to the AI service. Please try again.",
                    cause=e
                )
            raise LLMError(
                error_code=ErrorCode.LLM_INVALID_RESPONSE,
                message=f"Unexpected LLM error: {e}",
                user_message="The AI encountered an error. Please try again.",
                cause=e
            )

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        try:
            # Clean markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Extract JSON from thinking model output
            if "{" in content:
                start_idx = content.find("{")
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(content)):
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                content = content[start_idx:end_idx]
            
            # Handle truncated JSON
            content = content.strip()
            if content and not content.endswith("}"):
                open_braces = content.count("{") - content.count("}")
                open_brackets = content.count("[") - content.count("]")
                if content.count('"') % 2 != 0:
                    content += '"'
                content += "]" * open_brackets
                content += "}" * open_braces
                logger.warning("Attempted to fix truncated JSON")
            
            result = json.loads(content)
            
            # Normalize: if LLM returns "message" instead of "question", fix it
            if "message" in result and "question" not in result:
                result["question"] = result["message"]
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Job Agent: Could not parse JSON: {e}")
            logger.error(f"Raw content: {content[:200]}")
            raise InvalidJSONError(
                message=f"Could not parse LLM response as JSON: {e}",
                user_message="The AI response was unclear. Please try again.",
                raw_content=content[:200],
                cause=e
            )
    
    def _validate_params(
        self,
        memory: Memory,
        tool_name: str,
        user_input: str = ""
    ) -> Dict[str, Any]:
        """
        Validate parameters using Pydantic models.
        
        Args:
            memory: Conversation memory
            tool_name: Tool name
            user_input: User input (optional)
            
        Returns:
            Dict with validation result
        """
        params = memory.gathered_params
        logger.info(f"Validating params for {tool_name}, current params: {params}")
        
        if tool_name == "read_sql":
            result = self.validator.validate_read_sql_params(params, memory)
            if result:
                return result
            return {
                "action": "TOOL",
                "tool_name": "read_sql",
                "params": params
            }
        
        elif tool_name == "write_data":
            result = self.validator.validate_write_data_params(params, memory)
            if result:
                return result
            return {
                "action": "TOOL",
                "tool_name": "write_data",
                "params": params
            }
        
        elif tool_name == "send_email":
            result = self.validator.validate_send_email_params(params)
            if result:
                return result
            return {
                "action": "TOOL",
                "tool_name": "send_email",
                "params": params
            }
        
        elif tool_name == "compare_sql":
            result = self.validator.validate_compare_sql_params(params)
            if result:
                return result
            return {
                "action": "TOOL",
                "tool_name": "compare_sql",
                "params": params
            }
        
        return {
            "action": "ASK",
            "question": "I need more information. What would you like to do?"
        }
    
    def _get_missing_params_write_data(self, params: Dict[str, Any]) -> list:
        """Get list of missing write_data parameters."""
        missing = []
        if not params.get("name"): missing.append("name")
        if not params.get("table"): missing.append("table")
        if not params.get("schemas"): missing.append("schemas")
        if not params.get("connection"): missing.append("connection")
        if not params.get("drop_or_truncate"): missing.append("drop_or_truncate")
        return missing
    
    def _get_missing_params_read_sql(self, params: Dict[str, Any]) -> list:
        """Get list of missing read_sql parameters."""
        missing = []
        if not params.get("name"): missing.append("name")
        if "execute_query" not in params: missing.append("execute_query")
        if "write_count" not in params: missing.append("write_count")
        return missing
    
    def _get_missing_params_send_email(self, params: Dict[str, Any]) -> list:
        """Get list of missing send_email parameters."""
        missing = []
        if not params.get("name"): missing.append("name")
        if not params.get("to"): missing.append("to")
        if not params.get("subject"): missing.append("subject")
        return missing


# Factory function for creating JobAgent instances
def create_job_agent(
    config: Optional[JobAgentConfig] = None,
    prompt_manager: Optional[PromptManager] = None,
    validator: Optional[ParameterValidator] = None
) -> JobAgent:
    """
    Factory function to create a JobAgent instance.
    
    Args:
        config: Optional configuration
        prompt_manager: Optional prompt manager
        validator: Optional parameter validator
        
    Returns:
        JobAgent: Configured job agent instance
    """
    return JobAgent(config=config, prompt_manager=prompt_manager, validator=validator)


# Create default instance for backward compatibility
_default_job_agent = create_job_agent()


def call_job_agent(memory: Memory, user_input: str, tool_name: str = "read_sql") -> Dict[str, Any]:
    """
    Call the job parameter agent (backward compatibility function).
    
    Args:
        memory: Conversation memory
        user_input: User's message
        tool_name: Tool we're gathering params for
        
    Returns:
        Action dict with next steps
    """
    return _default_job_agent.gather_params(memory, user_input, tool_name)
