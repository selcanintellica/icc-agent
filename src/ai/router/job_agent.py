"""
Refactored Job Agent with Dependency Injection.

This module provides job parameter gathering following SOLID principles:
- Single Responsibility: Only responsible for parameter gathering coordination
- Open/Closed: Easy to extend with new tools
- Liskov Substitution: Can be replaced with mock for testing
- Interface Segregation: Clean interfaces
- Dependency Inversion: Depends on abstractions (PromptManager, ParameterValidator)
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from src.ai.router.memory import Memory
from src.ai.router.prompts import PromptManager
from src.ai.router.validators import ParameterValidator, YesNoExtractor

logger = logging.getLogger(__name__)


class JobAgentConfig:
    """Configuration for JobAgent following SRP."""
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434",
        num_predict: int = 4096
    ):
        self.model_name = model_name or os.getenv("MODEL_NAME", "qwen3:8b")
        self.temperature = temperature
        self.base_url = base_url
        self.num_predict = num_predict


class JobAgent:
    """
    Agent that gathers parameters for job execution.
    
    Refactored following SOLID principles with dependency injection.
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
            timeout=30.0,  # 30 second timeout
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
        logger.info(f"🔍 Job Agent: Gathering params for '{tool_name}'")
        logger.info(f"📋 Current params: {memory.gathered_params}")
        
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
        
        # Try to use LLM to extract parameters
        try:
            result = self._extract_with_llm(memory, user_input, tool_name)
            
            # Normalize schemas if it's a list
            if "params" in result and result["params"]:
                params = result["params"]
                if "schemas" in params and isinstance(params["schemas"], list):
                    params["schemas"] = params["schemas"][0] if params["schemas"] else ""
                    logger.info(f"📝 Normalized schemas from list to string: {params['schemas']}")
                
                # Update memory with non-None values
                new_params = {k: v for k, v in params.items() if v is not None}
                memory.gathered_params.update(new_params)
                logger.info(f"📝 Updated gathered_params: {memory.gathered_params}")
            
            logger.info(f"✅ Job Agent action: {result.get('action')}, params: {result.get('params')}")
            
            # After extracting params, ALWAYS validate to get the correct next question
            # The validator knows the correct order (name -> connection -> schemas -> table)
            # Don't trust LLM's question suggestions
            return self._validate_params(memory, tool_name, user_input)
        
        except Exception as e:
            logger.error(f"❌ Job Agent error: {str(e)}")
            return self._validate_params(memory, tool_name, user_input)
    
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
        logger.info(f"💬 Detected conversational input: {user_input}")
        
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
            messages = [
                SystemMessage(content="You are a helpful assistant helping configure database jobs. Be friendly and conversational."),
                HumanMessage(content=context)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            logger.info(f"💬 Conversational response: {result.get('question', '')[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Conversation handling failed: {str(e)}")
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
            # 2. This avoids duplication when validator includes it in the question
            needs_connection = "connection" in missing and "connection" not in memory.gathered_params
            connection_already_in_question = memory.last_question and "Available connections:" in memory.last_question
            
            connection_list = ""
            if needs_connection and memory.connections and not connection_already_in_question:
                connection_list = memory.get_connection_list_for_llm()
            
            # Check if write_count is enabled to add conditional hints
            write_count = memory.gathered_params.get("write_count", False)
            
            system_prompt = self.prompt_manager.get_prompt("write_data", connections=connection_list, write_count=write_count)
            
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
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt_text)
        ]
        
        logger.info(f"🔄 Calling LLM with model: {self.config.model_name}")
        logger.info(f"📝 Prompt length: {len(prompt_text)} chars")
        logger.info(f"📄 System prompt:\n{system_prompt}")
        logger.info(f"📄 User prompt:\n{prompt_text}")
        
        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            logger.info(f"🤖 Job Agent raw response: {content[:300]}...")
            
            if not content:
                logger.error("❌ LLM returned empty response, using fallback")
                return self._validate_params(memory, tool_name, user_input)
        except Exception as llm_error:
            logger.error(f"❌ LLM invocation failed: {str(llm_error)}")
            logger.error(f"❌ Falling back to validation")
            return self._validate_params(memory, tool_name, user_input)
        
        # Parse JSON response
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
                logger.info(f"📝 Extracted JSON from {start_idx} to {end_idx}")
            
            # Handle truncated JSON
            content = content.strip()
            if content and not content.endswith("}"):
                open_braces = content.count("{") - content.count("}")
                open_brackets = content.count("[") - content.count("]")
                if content.count('"') % 2 != 0:
                    content += '"'
                content += "]" * open_brackets
                content += "}" * open_braces
                logger.warning(f"⚠️ Attempted to fix truncated JSON")
            
            result = json.loads(content)
            
            # Normalize: if LLM returns "message" instead of "question", fix it
            if "message" in result and "question" not in result:
                result["question"] = result["message"]
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Job Agent: Could not parse JSON: {e}")
            logger.error(f"Raw content: {content}")
            return self._validate_params(memory, tool_name, user_input)
    
    def _validate_params(
        self,
        memory: Memory,
        tool_name: str,
        user_input: str = ""
    ) -> Dict[str, Any]:
        """
        Validate parameters using ParameterValidator.
        
        Args:
            memory: Conversation memory
            tool_name: Tool name
            user_input: User input (optional)
            
        Returns:
            Dict with validation result
        """
        params = memory.gathered_params
        logger.info(f"🔧 Validating params for {tool_name}, current params: {params}")
        
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
