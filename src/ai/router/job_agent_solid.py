"""
Job parameter agent - SOLID compliant refactored version.
Extracts parameters and asks clarifying questions using dependency injection.
"""
import json
import logging
from typing import Dict, Any, Optional
from src.ai.router.memory import Memory
from src.ai.router.llm_client import LLMClient, OllamaClient
from src.ai.router.prompt_builder import PromptBuilder
from src.ai.router.validators import VALIDATORS, ParameterValidator

logger = logging.getLogger(__name__)


class JobAgent:
    """
    Agent that gathers parameters and determines when to invoke tools.
    
    SOLID Principles Applied:
    - Single Responsibility: Only coordinates between LLM, prompts, and validators
    - Open/Closed: Add new tools by adding validators, no modification needed
    - Liskov Substitution: Any LLMClient implementation works
    - Interface Segregation: Clean interfaces for each component
    - Dependency Inversion: Depends on abstractions (LLMClient, ParameterValidator)
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        validators: Optional[Dict[str, ParameterValidator]] = None
    ):
        """
        Initialize JobAgent with dependencies.
        
        Args:
            llm_client: LLM client implementation (defaults to OllamaClient)
            prompt_builder: Prompt builder (defaults to PromptBuilder)
            validators: Dict of validators by tool name (defaults to VALIDATORS)
        """
        self.llm = llm_client or OllamaClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validators = validators or VALIDATORS
    
    def gather_params(
        self,
        memory: Memory,
        user_input: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Extract parameters from user input and determine next action.
        
        Args:
            memory: Conversation memory with context
            user_input: Latest user message
            tool_name: Which tool we're gathering params for
            
        Returns:
            Dict with action (ASK/TOOL/FETCH_SCHEMAS), question, params, etc.
        """
        logger.info(f"🔍 Job Agent: Gathering params for '{tool_name}'")
        logger.info(f"📋 Current params: {memory.gathered_params}")
        
        try:
            # 1. Build prompt using PromptBuilder
            messages = self.prompt_builder.build_prompt(tool_name, memory, user_input)
            
            # 2. Get LLM response
            content = self.llm.invoke(messages)
            logger.info(f"🤖 Job Agent raw response: {content[:300]}...")
            
            # Check for empty response
            if not content:
                logger.error("❌ LLM returned empty response, using fallback")
                return self._fallback_validation(memory, tool_name, user_input)
            
            # 3. Parse JSON response
            result = self._parse_llm_response(content)
            
            # 4. Normalize parameters
            self._normalize_params(result, memory)
            
            # 5. Handle yes/no answers before validation
            self._handle_yes_no_answers(user_input, memory, tool_name)
            
            # 6. If LLM returned a question, use it
            if result.get("action") == "ASK" and result.get("question"):
                logger.info(f"📝 Using LLM's question: {result['question']}")
                
                # Check if we just handled a yes/no - if so, re-validate
                if user_input and user_input.lower().strip() in ["yes", "y", "no", "n", "true", "false", "1", "0"]:
                    logger.info("📝 Just handled yes/no, checking for next required param")
                    return self._fallback_validation(memory, tool_name, user_input="")
                
                # Enhance connection questions with list
                if tool_name == "write_data" and "connection" in result["question"].lower():
                    connection_list = memory.get_connection_list_for_llm()
                    if connection_list and memory.connections:
                        result["question"] = f"Which connection should I use to write the data?\n\nAvailable connections:\n{connection_list}"
                
                return result
            
            # 7. If LLM says TOOL, validate with appropriate validator
            if result.get("action") == "TOOL":
                return self._validate_params(memory, tool_name, user_input)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Job Agent error: {str(e)}")
            return self._fallback_validation(memory, tool_name, user_input)
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        
        Args:
            content: Raw LLM response
            
        Returns:
            Parsed JSON dict
        """
        # Clean markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Extract JSON from response (handle thinking models that add text)
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
    
    def _normalize_params(self, result: Dict[str, Any], memory: Memory) -> None:
        """
        Normalize and update parameters in memory.
        
        Args:
            result: Parsed LLM response
            memory: Conversation memory
        """
        if "params" in result and result["params"]:
            params = result["params"]
            
            # Fix: LLM sometimes returns schemas as list instead of string
            if "schemas" in params and isinstance(params["schemas"], list):
                params["schemas"] = params["schemas"][0] if params["schemas"] else ""
                logger.info(f"📝 Normalized schemas from list to string: {params['schemas']}")
            
            # Only update with non-None values
            new_params = {k: v for k, v in params.items() if v is not None}
            memory.gathered_params.update(new_params)
            logger.info(f"📝 Updated gathered_params: {memory.gathered_params}")
    
    def _handle_yes_no_answers(self, user_input: str, memory: Memory, tool_name: str) -> None:
        """
        Handle direct yes/no answers from user.
        
        Args:
            user_input: User's message
            memory: Conversation memory
            tool_name: Current tool name
        """
        if not user_input or user_input.lower().strip() not in ["yes", "y", "no", "n", "true", "false", "1", "0"]:
            return
        
        user_lower = user_input.lower().strip()
        params = memory.gathered_params
        
        # For read_sql: execute_query (first) → write_count (second)
        if tool_name == "read_sql":
            if "execute_query" not in params:
                if user_lower in ["yes", "y", "true", "1"]:
                    params["execute_query"] = True
                    logger.info("📝 Set execute_query=True from direct user input")
                elif user_lower in ["no", "n", "false", "0"]:
                    params["execute_query"] = False
                    logger.info("📝 Set execute_query=False from direct user input")
            elif "write_count" not in params:
                if user_lower in ["yes", "y", "true", "1"]:
                    params["write_count"] = True
                    logger.info("📝 Set write_count=True from direct user input")
                elif user_lower in ["no", "n", "false", "0"]:
                    params["write_count"] = False
                    logger.info("📝 Set write_count=False from direct user input")
        
        # For write_data: only write_count uses yes/no
        elif tool_name == "write_data" and "write_count" not in params:
            if user_lower in ["yes", "y", "true", "1"]:
                params["write_count"] = True
                logger.info("📝 Set write_count=True from direct user input")
            elif user_lower in ["no", "n", "false", "0"]:
                params["write_count"] = False
                logger.info("📝 Set write_count=False from direct user input")
    
    def _validate_params(self, memory: Memory, tool_name: str, user_input: str) -> Dict[str, Any]:
        """
        Validate parameters using appropriate validator.
        
        Args:
            memory: Conversation memory
            tool_name: Current tool name
            user_input: User's input
            
        Returns:
            Action dict (ASK if missing params, TOOL if complete)
        """
        validator = self.validators.get(tool_name)
        if not validator:
            logger.warning(f"⚠️ No validator found for {tool_name}, returning TOOL")
            return {
                "action": "TOOL",
                "tool_name": tool_name,
                "params": memory.gathered_params
            }
        
        result = validator.validate(memory.gathered_params, memory)
        if result:  # Missing parameters
            return result
        
        # All params present
        return {
            "action": "TOOL",
            "tool_name": tool_name,
            "params": memory.gathered_params
        }
    
    def _fallback_validation(self, memory: Memory, tool_name: str, user_input: str = "") -> Dict[str, Any]:
        """
        Fallback validation if LLM fails.
        
        Args:
            memory: Conversation memory
            tool_name: Current tool name
            user_input: User's input
            
        Returns:
            Action dict
        """
        logger.info(f"🔧 Fallback validation for {tool_name}")
        return self._validate_params(memory, tool_name, user_input)


# Global instance
job_agent = JobAgent()


def call_job_agent(memory: Memory, user_input: str, tool_name: str = "read_sql") -> Dict[str, Any]:
    """
    Call the job parameter agent.
    
    Args:
        memory: Conversation memory
        user_input: User's message
        tool_name: Tool we're gathering params for
        
    Returns:
        Action dict with next steps
    """
    return job_agent.gather_params(memory, user_input, tool_name)
