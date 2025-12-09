# Adding a New Job Type to ICC Agent

This guide explains how to add a new job type to the ICC Agent system following the established SOLID architecture.

## Overview

The system uses a modular, strategy-based architecture. Adding a new job requires:
1. Creating stage strategies
2. Adding a job prompt
3. Creating a stage handler
4. Adding wire builder (if needed)
5. Registering the new job

**Estimated Time:** 2-4 hours for a complete implementation

---

## Step 1: Define Stages

**Location:** `src/ai/router/context/stage_context.py`

Add your job's stages to the `Stage` enum:

```python
class Stage(Enum):
    # ... existing stages ...
    
    # Your New Job Flow
    ASK_YOUR_JOB_METHOD = "ask_your_job_method"
    NEED_YOUR_JOB_PARAMS = "need_your_job_params"
    CONFIRM_YOUR_JOB = "confirm_your_job"
    EXECUTE_YOUR_JOB = "execute_your_job"
```

Then register them in the appropriate category:

```python
@classmethod
def get_stages_by_category(cls) -> Dict[str, List['Stage']]:
    return {
        # ... existing categories ...
        "your_job": [
            cls.ASK_YOUR_JOB_METHOD,
            cls.NEED_YOUR_JOB_PARAMS,
            cls.CONFIRM_YOUR_JOB,
            cls.EXECUTE_YOUR_JOB,
        ],
    }
```

---

## Step 2: Create Stage Strategies

**Location:** `src/ai/router/stage_handlers/strategies/yourjob/`

Create a new directory and implement each stage as a strategy:

### 2.1 Create Directory Structure

```
src/ai/router/stage_handlers/strategies/yourjob/
├── __init__.py
├── ask_your_job_method.py
├── need_your_job_params.py
├── confirm_your_job.py
└── execute_your_job.py
```

### 2.2 Implement Each Strategy

**Example: `ask_your_job_method.py`**

```python
"""Strategy for ASK_YOUR_JOB_METHOD stage."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

logger = logging.getLogger(__name__)


class AskYourJobMethodStrategy(StageStrategy):
    """Handle method selection for your job."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute ASK_YOUR_JOB_METHOD stage."""
        user_lower = user_input.lower().strip()
        
        # Handle navigation commands
        nav_cmd = self._check_navigation_commands(user_input)
        if nav_cmd == "back":
            memory.current_tool = None
            return self._create_result(
                memory,
                "Going back. Choose a job type:\n- 'readsql'\n- 'comparesql'\n- 'yourjob'",
                Stage.ASK_JOB_TYPE
            )
        elif nav_cmd == "reset":
            memory.reset()
            memory.stage = Stage.ASK_JOB_TYPE
            return self._create_result(
                memory,
                "Reset! Choose a job type:\n- 'readsql'\n- 'comparesql'\n- 'yourjob'",
                Stage.ASK_JOB_TYPE
            )
        
        # Handle user choice
        if "option1" in user_lower:
            return self._create_result(
                memory,
                "Great! Please provide parameter X:",
                Stage.NEED_YOUR_JOB_PARAMS
            )
        elif "option2" in user_lower:
            return self._create_result(
                memory,
                "Okay! Please provide parameter Y:",
                Stage.NEED_YOUR_JOB_PARAMS
            )
        else:
            return self._create_result(
                memory,
                "Please choose:\n- 'option1' - Description\n- 'option2' - Description"
            )
```

### 2.3 Create `__init__.py`

```python
"""Stage strategies for your job."""

from src.ai.router.stage_handlers.strategies.yourjob.ask_your_job_method import AskYourJobMethodStrategy
from src.ai.router.stage_handlers.strategies.yourjob.need_your_job_params import NeedYourJobParamsStrategy
from src.ai.router.stage_handlers.strategies.yourjob.confirm_your_job import ConfirmYourJobStrategy
from src.ai.router.stage_handlers.strategies.yourjob.execute_your_job import ExecuteYourJobStrategy

__all__ = [
    "AskYourJobMethodStrategy",
    "NeedYourJobParamsStrategy",
    "ConfirmYourJobStrategy",
    "ExecuteYourJobStrategy",
]
```

---

## Step 3: Create Job Prompt (Optional)

**Location:** `src/ai/router/prompts/job_prompts/your_job_prompt.py`

If your job uses LLM for parameter extraction:

```python
"""
Your Job parameter extraction prompt.
"""


class YourJobPrompt:
    """Prompt for your_job parameter extraction."""
    
    TEMPLATE = """Extract params for your_job.

CRITICAL RULES:
1. Match user's answer to the last question asked
2. IGNORE "ok", "okay", "yes", "no" UNLESS answering yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing

Required params:
- name: Job name
- parameter1: Description
- parameter2: Description

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self, **kwargs) -> str:
        """Get the your_job prompt."""
        return self.TEMPLATE
```

Then register in `src/ai/router/prompts/job_prompts/__init__.py`:

```python
from .your_job_prompt import YourJobPrompt

__all__ = [
    # ... existing ...
    "YourJobPrompt",
]
```

And add to `PromptManager`:

```python
# src/ai/router/prompts/prompt_manager.py
def __init__(self):
    self._prompts: Dict[str, PromptProvider] = {
        "write_data": WriteDataPrompt(),
        "read_sql": ReadSQLPrompt(),
        "send_email": SendEmailPrompt(),
        "your_job": YourJobPrompt(),  # ADD THIS
    }
```

---

## Step 4: Use LLM for Parameter Extraction (Optional)

If your job has complex parameters that need conversational gathering, use the Job Agent.

### 4.1 When to Use Job Agent

Use Job Agent when:
- ✅ Parameters need natural language understanding
- ✅ Multiple parameters with dependencies
- ✅ Need to ask follow-up questions
- ✅ Parameters require validation with user confirmation

Don't use when:
- ❌ Simple yes/no choices (use strategy directly)
- ❌ Fixed selection from dropdown (use strategy)
- ❌ Single parameter with no dependencies

### 4.2 Create Parameter Gathering Stage

**Example: `need_your_job_params.py`**

```python
"""Strategy for gathering parameters using Job Agent."""

import logging
from src.ai.router.stage_handlers.stage_strategy import StageStrategy, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.router.utils.connection_fetcher import ConnectionFetcher

logger = logging.getLogger(__name__)


class NeedYourJobParamsStrategy(StageStrategy):
    """Handle parameter gathering using Job Agent."""
    
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute parameter gathering with Job Agent."""
        try:
            # Call job agent for intelligent parameter extraction
            action = call_job_agent(memory, user_input, tool_name="your_job")
            
            # Handle different action types
            if action.get("action") == "FETCH_CONNECTIONS":
                # Fetch connections for dropdown
                return await self._fetch_connections(memory)
            
            if action.get("action") == "FETCH_SCHEMAS":
                # Fetch schemas for selected connection
                connection = action.get("connection")
                return await self._fetch_schemas(memory, connection)
            
            if action.get("action") == "ASK":
                # Job agent needs more information
                memory.last_question = action["question"]
                return self._create_result(memory, action["question"])
            
            if action.get("action") == "TOOL" and action.get("tool_name") == "your_job":
                # All parameters gathered - move to confirmation
                params = action.get("params", {})
                memory.gathered_params.update(params)
                
                # Build confirmation message
                confirmation = self._build_confirmation_message(params)
                return self._create_result(
                    memory,
                    confirmation,
                    Stage.CONFIRM_YOUR_JOB
                )
            
            # Fallback
            return self._create_result(
                memory,
                "Let's set up your job. What would you like to name it?"
            )
            
        except Exception as e:
            logger.error(f"Error in parameter gathering: {e}")
            return self._create_result(
                memory,
                f"Error: {str(e)}\nPlease try again.",
                is_error=True
            )
    
    async def _fetch_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch connections for dropdown."""
        try:
            result = await ConnectionFetcher.fetch_connections(memory)
            if not result["success"]:
                return self._create_result(
                    memory,
                    f"Error fetching connections: {result['message']}"
                )
            
            # Format for dropdown
            import json
            question = "Which connection would you like to use?"
            dropdown_data = {
                'connections': memory.connections,
                'param_name': 'connection',
                'question': question
            }
            response = f"CONNECTION_DROPDOWN:{json.dumps(dropdown_data)}"
            memory.last_question = question
            
            return self._create_result(memory, response)
            
        except Exception as e:
            logger.error(f"Error fetching connections: {e}")
            return self._create_result(
                memory,
                "Error fetching connections. Please try again."
            )
    
    async def _fetch_schemas(self, memory: Memory, connection: str) -> StageHandlerResult:
        """Fetch schemas for selected connection."""
        try:
            result = await ConnectionFetcher.fetch_schemas(connection, memory)
            if not result["success"]:
                return self._create_result(
                    memory,
                    f"Error fetching schemas: {result['message']}"
                )
            
            # Format for dropdown
            import json
            question = "Which schema would you like to use?"
            dropdown_data = {
                'schemas': memory.available_schemas,
                'param_name': 'schema',
                'question': question
            }
            response = f"SCHEMA_DROPDOWN:{json.dumps(dropdown_data)}"
            memory.last_question = question
            
            return self._create_result(memory, response)
            
        except Exception as e:
            logger.error(f"Error fetching schemas: {e}")
            return self._create_result(
                memory,
                "Error fetching schemas. Please try again."
            )
    
    def _build_confirmation_message(self, params: dict) -> str:
        """Build confirmation message showing all gathered parameters."""
        lines = ["I've gathered these parameters:"]
        for key, value in params.items():
            lines.append(f"- {key}: {value}")
        lines.append("\nIs this correct? (yes/no)")
        return "\n".join(lines)
```

### 4.3 Job Agent Action Types

The Job Agent returns actions with these types:

1. **`ASK`** - Needs more information
   ```python
   {"action": "ASK", "question": "What is parameter X?"}
   ```

2. **`TOOL`** - All parameters gathered
   ```python
   {
       "action": "TOOL",
       "tool_name": "your_job",
       "params": {"name": "job1", "param1": "value1", ...}
   }
   ```

3. **`FETCH_CONNECTIONS`** - Needs connection dropdown
   ```python
   {"action": "FETCH_CONNECTIONS"}
   ```

4. **`FETCH_SCHEMAS`** - Needs schema dropdown
   ```python
   {"action": "FETCH_SCHEMAS", "connection": "connection_name"}
   ```

### 4.4 Memory Fields Used by Job Agent

The Job Agent automatically uses these memory fields:

- `memory.gathered_params` - Stores collected parameters
- `memory.last_question` - Last question asked to user
- `memory.connections` - Available connections
- `memory.available_schemas` - Available schemas
- `memory.connection` - Selected connection
- `memory.schema` - Selected schema

### 4.5 Testing Parameter Extraction

Test your Job Agent integration:

```python
# Test conversation flow
User: "Create job"
Agent: "What would you like to name this job?"
User: "my_job"
Agent: "Which connection?" [dropdown appears]
User: [selects connection]
Agent: "Which schema?" [dropdown appears]
User: [selects schema]
Agent: "What is parameter1?"
User: "value1"
Agent: "I've gathered these parameters:\n- name: my_job\n- connection: conn1\n..."
```

---

## Step 5: Create Stage Handler

**Location:** `src/ai/router/stage_handlers/yourjob_handler.py`

```python
"""
YourJob Handler with Strategy Pattern.

Handles all stages for your job type.
"""

import logging
from typing import Optional

from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.stage_handlers.stage_strategy import StageStrategyRegistry
from src.ai.router.stage_handlers.strategies.yourjob import (
    AskYourJobMethodStrategy,
    NeedYourJobParamsStrategy,
    ConfirmYourJobStrategy,
    ExecuteYourJobStrategy,
)
from src.errors import ICCBaseError

logger = logging.getLogger(__name__)


class YourJobHandler(BaseStageHandler):
    """
    Handler for your job stages using Strategy pattern.
    
    Following SOLID principles:
    - Single Responsibility: Only orchestrates your job stages
    - Open/Closed: Easy to add new stages via registry
    - Strategy Pattern: Each stage is a separate strategy
    """
    
    def __init__(self, job_agent=None):
        """
        Initialize YourJob handler.
        
        Args:
            job_agent: Job agent for parameter gathering (optional)
        """
        self.job_agent = job_agent
        self.strategy_registry = self._initialize_strategies()
    
    def _initialize_strategies(self) -> StageStrategyRegistry:
        """Initialize and register all strategies."""
        registry = StageStrategyRegistry()
        
        # Register each stage strategy
        registry.register(Stage.ASK_YOUR_JOB_METHOD, AskYourJobMethodStrategy())
        registry.register(Stage.NEED_YOUR_JOB_PARAMS, NeedYourJobParamsStrategy())
        registry.register(Stage.CONFIRM_YOUR_JOB, ConfirmYourJobStrategy())
        registry.register(Stage.EXECUTE_YOUR_JOB, ExecuteYourJobStrategy())
        
        return registry
    
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Args:
            stage: The stage to check
            
        Returns:
            bool: True if this handler can process the stage
        """
        return self.strategy_registry.has_strategy(stage)
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process the stage using appropriate strategy.
        
        Args:
            memory: Current conversation memory
            user_input: User's input message
            
        Returns:
            StageHandlerResult: Result with updated memory and response
        """
        try:
            # Get strategy for current stage
            strategy = self.strategy_registry.get_strategy(memory.stage)
            
            if strategy is None:
                logger.error(f"No strategy found for stage {memory.stage.value}")
                return self._create_result(
                    memory,
                    f"Unhandled stage in YourJob flow: {memory.stage.value}",
                    is_error=True
                )
            
            # Delegate to strategy with automatic help detection
            return await strategy.handle_with_help(memory, user_input)

        except ICCBaseError as e:
            logger.error(f"ICC error in YourJob handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in YourJob handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while processing your request. Please try again."
            )
```

---

## Step 6: Register Handler in Router

**Location:** `src/ai/router/router.py`

### 5.1 Import the Handler

```python
from .stage_handlers.yourjob_handler import YourJobHandler
```

### 5.2 Register in `_create_default_registry()`

```python
def _create_default_registry(self) -> HandlerRegistry:
    """Create default handler registry."""
    registry = HandlerRegistry()
    
    # ... existing handlers ...
    
    registry.register_handler(
        "yourjob",
        YourJobHandler(
            job_agent=self.config.job_agent  # if needed
        )
    )
    
    return registry
```

### 5.3 Add to Job Type Selection

**Location:** `src/ai/router/router.py` in `_handle_job_type_selection()`

```python
async def _handle_job_type_selection(self, memory: Memory, user_utterance: str):
    """Handle job type selection at ASK_JOB_TYPE stage."""
    user_lower = user_utterance.lower().strip()
    
    if "readsql" in user_lower:
        # ... existing ...
    elif "comparesql" in user_lower:
        # ... existing ...
    elif "yourjob" in user_lower:  # ADD THIS
        logger.info("User selected: yourjob")
        memory.current_tool = "your_job"
        memory.stage = Stage.ASK_YOUR_JOB_METHOD
        return memory, "How would you like to proceed with your job?\n- 'option1' - Description\n- 'option2' - Description"
    else:
        return memory, "Please choose:\n- 'readsql'\n- 'comparesql'\n- 'yourjob'"
```

---

## Step 7: Create Wire Builder (If Needed)

**Location:** `src/payload_builders/builders/yourjob_builder.py`

Only needed if your job calls the backend API:

```python
"""
YourJob Wire Builder.

Handles building wire payloads for YourJob jobs.
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel

from src.models.wire import WireVariable
from src.models.definition_map import TEMPLATES
from .base_builder import WirePayloadBuilder

logger = logging.getLogger(__name__)


class YourJobWireBuilder(WirePayloadBuilder):
    """Builder for YourJob wire payloads."""
    
    def __init__(self):
        """Initialize YourJob wire builder."""
        template_meta = TEMPLATES["YOURJOB"]
        super().__init__(
            template_id=template_meta["template_id"],
            definitions_map=template_meta["definitions"]
        )
    
    def get_template_key(self) -> str:
        """Get template key."""
        return "YOURJOB"
    
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build YourJob-specific variables.
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Additional arguments
            
        Returns:
            List[WireVariable]: YourJob-specific variables
        """
        # Add job-specific logic here
        return []
```

---

## Step 8: Add Request Model (If Needed)

**Location:** `src/models/natural_language.py`

```python
class YourJobVariables(BaseModel):
    connection: str = Field(..., description="Database connection")
    parameter1: str = Field(..., description="Parameter 1 description")
    parameter2: str = Field(..., description="Parameter 2 description")
    # ... add all required parameters


class YourJobRequest(BaseModel):
    name: str = Field(..., description="Job name")
    variables: YourJobVariables
```

---

## Step 9: Update Help System

**Location:** `src/ai/router/utils/help_handler.py`

Add stage descriptions in `_get_stage_description()`:

```python
def _get_stage_description(self, stage_value: str) -> str:
    stage_descriptions = {
        # ... existing stages ...
        
        # Your Job stages
        "ask_your_job_method": "choosing your job method",
        "need_your_job_params": "providing parameters for your job",
        "confirm_your_job": "confirming your job configuration",
        "execute_your_job": "executing your job",
    }
    return stage_descriptions.get(stage_value, f"at stage: {stage_value}")
```

---

## Checklist

Use this checklist to ensure complete implementation:

- [ ] Added stages to `Stage` enum
- [ ] Registered stages in `get_stages_by_category()`
- [ ] Created strategy directory structure
- [ ] Implemented all stage strategies
- [ ] Created strategy `__init__.py`
- [ ] Created job prompt (if using LLM)
- [ ] Registered prompt in PromptManager (if applicable)
- [ ] Created stage handler
- [ ] Registered handler in router
- [ ] Added job type to selection logic
- [ ] Created wire builder (if needed)
- [ ] Added request model (if needed)
- [ ] Updated help descriptions
- [ ] Tested all stages
- [ ] Added error handling
- [ ] Added logging statements

---

## Example: Complete Minimal Job

Here's a minimal working example for a simple "ping" job:

**1. Add Stage:**
```python
ASK_PING_TARGET = "ask_ping_target"
```

**2. Create Strategy:**
```python
class AskPingTargetStrategy(StageStrategy):
    async def execute(self, memory: Memory, user_input: str):
        memory.gathered_params["target"] = user_input
        return self._create_result(
            memory,
            f"Pinging {user_input}... Done!",
            Stage.DONE
        )
```

**3. Create Handler:**
```python
class PingHandler(BaseStageHandler):
    def __init__(self):
        self.strategy_registry = StageStrategyRegistry()
        self.strategy_registry.register(Stage.ASK_PING_TARGET, AskPingTargetStrategy())
    
    def can_handle(self, stage: Stage) -> bool:
        return self.strategy_registry.has_strategy(stage)
    
    async def handle(self, memory: Memory, user_input: str):
        strategy = self.strategy_registry.get_strategy(memory.stage)
        return await strategy.handle_with_help(memory, user_input)
```

**4. Register:**
```python
registry.register_handler("ping", PingHandler())
```

---

## Testing Your New Job

1. **Start the app:** `uv run app.py`
2. **Select your job:** Type the job name
3. **Test each stage:** Walk through all stages
4. **Test help:** Type "help" at each stage
5. **Test navigation:** Try "back" and "reset"
6. **Test errors:** Provide invalid input

---

## Best Practices

1. **Follow naming conventions:** Use snake_case for stage names
2. **Keep strategies focused:** Each strategy handles ONE stage
3. **Add comprehensive logging:** Use appropriate log levels
4. **Handle errors gracefully:** Use try-catch and ErrorHandler
5. **Provide clear messages:** User-facing text should be helpful
6. **Support navigation:** Always handle back/reset commands
7. **Document your code:** Add docstrings to all classes/methods
8. **Write tests:** Add unit tests for critical logic

---

## Need Help?

- Review existing jobs: `ReadSQLHandler`, `CompareSQLHandler`
- Check SOLID compliance: See `docs/ARCHITECTURE.md`
- Understand patterns: See `docs/ARCHITECTURE_DECISIONS.md`

Happy coding! 🚀
