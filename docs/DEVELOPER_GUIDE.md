# ICC Agent - Developer Guide

## Quick Start

### Prerequisites
- Python 3.11+
- Ollama installed with `qwen3:8b` and `qwen2.5-coder:7b` models
- Access to ICC backend API (connection API, job API)
- Database connections configured in `db_config.json`

### Installation

```powershell
# Clone repository
cd C:\Users\ICC_Agent

# Install dependencies
pip install -r requirements_app.txt
#or
uv sync

# Verify Ollama models
ollama list

# Should show:
# qwen3:8b
# qwen2.5-coder:7b
```

### Running the Application

```powershell
# Start Ollama (if not running)
ollama serve

# Run the web UI
uv run app.py

# Open browser to http://localhost:8050
```

### Configuration

**Environment Variables** (optional):
```bash
# Override default LLM models
MODEL_NAME=qwen3:8b              # Job agent model
SQL_MODEL_NAME=qwen2.5-coder:7b  # SQL agent model

# Enable prompt logging (saves all LLM prompts to files)
ENABLE_PROMPT_LOGGING=true
PROMPT_LOG_DIR=prompt_logs
```

**Prompt Logging** (for debugging and analysis):
When enabled, all prompts sent to LLMs are saved to individual files:
```
prompt_logs/
  session_20251203_143052/
    0001_job_agent.txt
    0002_sql_agent.txt
    0003_job_agent.txt
    all_prompts.jsonl
```

**db_config.json**:
```json
{
  "connections": [
    {
      "id": "4976629955435844",
      "name": "ORACLE_10",
      "type": "oracle",
      "schemas": [
        {
          "name": "SALES",
          "tables": ["customers", "orders", "order_items", "products"]
        },
        {
          "name": "HR",
          "tables": ["employees", "departments"]
        }
      ]
    }
  ]
}
```


## Architecture Patterns

### 1. Singleton Pattern for LLM Agents

**When to Use**: Any resource that should be created once and reused
**Why**: Prevents expensive reinitialization (LLM model loading)

**Implementation**:
```python
# Module-level singleton
_default_instance: Optional[MyClass] = None

def get_default_instance() -> MyClass:
    global _default_instance
    if _default_instance is None:
        logger.info("Creating singleton instance")
        _default_instance = MyClass()
    return _default_instance

# Usage in app
instance = get_default_instance()  # Creates on first call
instance2 = get_default_instance()  # Reuses same instance
```

### 2. Dropdown Bypass Pattern

**When to Use**: Any parameter with a fixed set of options
**Why**: Faster, more reliable than LLM extraction

**Implementation Steps**:

1. **Validator returns FETCH action**:
   ```python
   def validate_params(tool_name, params, memory):
       if "connection" not in params and memory.available_connections:
           return ValidationResult(action="FETCH_CONNECTIONS")
   ```

2. **Handler formats dropdown response**:
   ```python
   if action.action_type == "FETCH_CONNECTIONS":
       connections = memory.available_connections
       return RouterResponse(
           new_stage=current_stage,
           message=f"CONNECTION_DROPDOWN:{json.dumps(connections)}"
       )
   ```

3. **UI renders dropdown**:
   ```python
   if response.message.startswith("CONNECTION_DROPDOWN:"):
       data = json.loads(response.message.split(":", 1)[1])
       return render_dropdown(data, param_name="connection")
   ```

4. **UI sends selection with prefix**:
   ```python
   selection = f"__CONNECTION_SELECTED__:{selected_value}"
   router.process_input(memory, selection)
   ```

5. **Router assigns directly**:
   ```python
   if user_input.startswith("__CONNECTION_SELECTED__:"):
       value = user_input.split(":", 1)[1]
       memory.gathered_params["connection"] = value
       # Continue processing
   ```

### 3. Excluded Fields Pattern

**When to Use**: Complex parameters need special formatting
**Why**: Prevents duplicate variables in wire payloads

**Implementation**:

1. **Override in subclass**:
   ```python
   class MyBuilder(BaseBuilder):
       def get_excluded_fields(self) -> List[str]:
           return ["complex_field", "json_field"]
   ```

2. **Base builder skips excluded fields**:
   ```python
   def _build_base_variables(self, params, excluded_fields):
       for key, value in params.items():
           if key not in excluded_fields:
               self.add_simple_variable(key, value)
   ```

3. **Subclass handles excluded fields**:
   ```python
   def build(self, params):
       payload = super().build(params)  # Base adds non-excluded
       
       # Handle excluded fields with special formatting
       if "json_field" in params:
           json_str = json.dumps(params["json_field"])
           payload.add_variable("json_def_id", json_str)
       
       return payload
   ```

### 4. Confirmation Word Filtering

**When to Use**: After system messages where user might acknowledge
**Why**: Prevents spurious parameter extraction

**Implementation**:
```python
async def handle_stage(self, memory, user_input):
    # Filter if no params gathered yet
    if not memory.gathered_params and \
       user_input.lower().strip() in CONFIRMATION_WORDS:
        logger.info(f"Ignoring confirmation: {user_input}")
        user_input = ""  # Clear input
    
    # Continue processing
    action = call_job_agent(memory, user_input, tool_name)
```

**Confirmation Words List**:
```python
CONFIRMATION_WORDS = ["yes", "y", "ok", "okay", "sure", "correct", "right"]
```

## Adding a New Job Type

### Step 1: Decide Agent Dependencies

**Choose which agents your handler needs:**

- **Need SQL generation?** → Include `sql_agent` parameter
  - Example: ReadSQL, CompareSQL
  - Handler will call `call_sql_agent()` to generate queries from natural language

- **Need parameter extraction?** → Include `job_agent` parameter  
  - Example: All handlers
  - Handler will call `call_job_agent()` to gather user input

- **Auto-generate query from data?** → No SQL agent needed
  - Example: SendEmail (builds query from output_table_info)

### Step 2: Create Stage Handler

```python
# src/ai/router/stage_handlers/my_job_handler.py
from .base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.context.stage_context import Stage

class MyJobHandler(BaseStageHandler):
    # Define which stages this handler manages
    MANAGED_STAGES = {
        Stage.NEED_MY_JOB_PARAMS,
        Stage.EXECUTE_MY_JOB,
    }
    
    def __init__(self, sql_agent=None, job_agent=None):
        # Only include agents you need
        self.sql_agent = sql_agent  # If generating SQL from natural language
        self.job_agent = job_agent  # If extracting parameters from user input
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        stage = memory.stage
        
        if stage == Stage.NEED_MY_JOB_PARAMS:
            return await self._handle_need_params(memory, user_input)
        elif stage == Stage.EXECUTE_MY_JOB:
            return await self._handle_execute(memory, user_input)
    
    async def _handle_need_params(self, memory, user_input):
        # Call job agent to gather parameters
        action = call_job_agent(memory, user_input, tool_name="my_job")
        
        # Check action type
        if action.action_type == "ASK":
            return self._create_result(
                memory,
                message=action.question,
                new_stage=Stage.NEED_MY_JOB_PARAMS
            )
        
        if action.action_type == "TOOL":
            memory.stage = Stage.EXECUTE_MY_JOB
            return await self._handle_execute(memory, "")
    
    async def _handle_execute(self, memory, user_input):
        # Execute job
        result = execute_my_job(memory.gathered_params)
        
        return self._create_result(
            memory,
            message=f"Job executed! ID: {result.job_id}",
            new_stage=Stage.DONE
        )
```

### Step 3: Define Parameters

```python
# src/ai/router/prompts/prompt_manager.py

TOOL_PARAMS = {
    "my_job": {
        "required": ["name", "param1", "param2"],
        "descriptions": {
            "name": "Job name",
            "param1": "Description of param1",
            "param2": "Description of param2"
        }
    }
}
```

### Step 4: Create Payload Builder

```python
# src/payload_builders/builders/my_job_builder.py
from .base_builder import BaseBuilder

class MyJobBuilder(BaseBuilder):
    def __init__(self):
        super().__init__(template_id="123456789")
    
    def build(self, params: dict) -> WirePayload:
        # Build base variables
        payload = super().build(params)
        
        # Add job-specific variables
        payload.add_variable("param1_def_id", params["param1"])
        payload.add_variable("param2_def_id", params["param2"])
        
        return payload
```

### Step 5: Create Toolkit Function

```python
# src/ai/toolkits/icc_toolkit.py

def execute_my_job(params: dict) -> dict:
    """Execute my_job with given parameters"""
    logger.info(f"Executing my_job with params: {params}")
    
    # Build payload
    builder = MyJobBuilder()
    payload = builder.build(params)
    
    # Call API
    repository = JobRepository()
    response = repository.create_job(payload)
    
    logger.info(f"✅ My job created: {response.job_id}")
    
    return {
        "message": "Success",
        "job_id": response.job_id,
        "params": params
    }
```

### Step 6: Register in Router

```python
# src/ai/router/router.py

class RouterOrchestrator:
    def __init__(self, config, sql_agent, job_agent):
        # ...
        # Register handler (router dispatches based on stage.can_handle)
        self.handler_registry.register_handler(MyJobHandler(sql_agent, job_agent))
```

### Step 7: Add Entry Point

```python
# src/ai/router/stage_handlers/router_handler.py

async def handle_router_stage(self, memory, user_input):
    # Add to intent detection
    if "my job" in user_input.lower():
        memory.stage = Stage.NEED_MY_JOB_PARAMS
        memory.current_job_type = "my_job"
        return self._create_result(
            memory,
            message="Let's create a my_job job!",
            new_stage=Stage.NEED_MY_JOB_PARAMS
        )
```

## Modifying Prompts

### Job Agent Prompts

**Location**: `src/ai/router/prompts/prompt_manager.py`

**Structure**:
```python
def build_job_prompt(tool_name, gathered_params, last_question, user_input):
    # System prompt
    system = f"""Extract params for {tool_name} job.

IGNORE: "ok", "okay", "yes", "no", "sure" - NOT parameter values!

Required params:
{format_required_params(tool_name)}

IMPORTANT: Only extract actual values from user input.

Output JSON: {{"action": "ASK"|"TOOL", "question": "...", "params": {{...}}}}
"""
    
    # User prompt
    user = f"""Last question: "{last_question}"
User answer: "{user_input}"
Current: {json.dumps(gathered_params)}
Missing: {get_missing_params(tool_name, gathered_params)}

Output JSON only:
"""
    
    return system, user
```

**Tips**:
- Keep prompts concise (fewer tokens = faster)
- Be explicit about what NOT to extract
- Use structured output format (JSON)
- Include examples for complex cases
- Avoid listing all available options (use dropdowns)

### SQL Agent Prompts

**Location**: `src/ai/router/sql_agent.py`

**Structure**:
```python
def build_sql_prompt(user_request, schema, table_info):
    prompt = f"""Generate SQL for: {user_request}

Schema: {schema}
Tables:
{format_table_info(table_info)}

Requirements:
- Use correct table/column names from schema
- Generate SELECT query only
- No INSERT/UPDATE/DELETE
- Use JOINs where appropriate

Output: SQL query only, no explanation.
"""
    return prompt
```

**Tips**:
- Provide schema context
- Limit table info (only selected tables)
- Be explicit about restrictions
- Request SQL only (no explanations)
- Set `num_predict` limit to prevent long outputs

## Testing

### Unit Tests

**Test Handler Logic**:
```python
# tests/test_handlers.py
import pytest
from src.ai.router.stage_handlers.readsql_handler import ReadSQLHandler

@pytest.mark.asyncio
async def test_confirmation_filtering():
    handler = ReadSQLHandler(sql_agent, job_agent)
    memory = create_test_memory()
    memory.stage = Stage.EXECUTE_SQL
    memory.gathered_params = {}
    
    response = await handler.handle(memory, "okay")
    
    # Should not extract "okay" as parameter
    assert "okay" not in memory.gathered_params.values()
    # Should still be in same stage
    assert response.new_stage == Stage.EXECUTE_SQL
```

**Test Parameter Validation**:
```python
def test_validator_fetch_connections():
    memory = Memory()
    memory.available_connections = [{"id": "123", "name": "ORACLE"}]
    params = {}
    
    result = validate_params("read_sql", params, memory)
    
    assert result.action == "FETCH_CONNECTIONS"
    assert result.missing_param == "connection"
```

**Test Payload Builders**:
```python
def test_excluded_fields():
    builder = WriteDataBuilder()
    params = {
        "name": "test",
        "columns": [{"columnName": "id"}],
        "data_set": {...}
    }
    
    payload = builder.build(params)
    
    # Check no duplicates
    var_names = [v.definition_id for v in payload.variables]
    assert len(var_names) == len(set(var_names))
```

### Integration Tests

**Test Full Flow**:
```python
@pytest.mark.asyncio
async def test_readsql_flow():
    router = get_default_router_orchestrator()
    memory = Memory()
    
    # Request data
    r1 = await router.process_input(memory, "get customers")
    assert r1.new_stage == Stage.CONFIRM_GENERATED_SQL
    
    # Confirm SQL
    r2 = await router.process_input(memory, "yes")
    assert r2.new_stage == Stage.EXECUTE_SQL
    
    # Provide job name
    r3 = await router.process_input(memory, "customer_query")
    assert r3.new_stage == Stage.SHOW_RESULTS
    assert memory.job_context["job_id"]
```

### Manual Testing

**Test Dropdown Flow**:
```
User: "write data to database"
→ System: Shows connection dropdown
User: Selects "ORACLE_10"
→ System: Shows schema dropdown
User: Selects "SALES"
→ System: "What table?"
User: "customers"
→ System: Execute job
```

**Test Confirmation Filtering**:
```
User: "read from customers"
→ System: "Here's the SQL... Looks good?"
User: "yes"
→ System: "Great! Executing..."
User: "okay"
→ System: "What should I name this job?" (doesn't extract "okay")
User: "customer_data"
→ System: "Job created!"
```

## Debugging

### Enable Detailed Logging

```python
# app.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check LLM Status

```powershell
# Check loaded models
ollama ps

# Expected output (singleton working):
# NAME                ID              SIZE    PROCESSOR    UNTIL
# qwen3:8b          abc123...       5.5 GB  100% GPU     59 minutes from now
# qwen2.5-coder:7b  def456...       4.7 GB  100% GPU     59 minutes from now

# Check model info
ollama show qwen3:8b
ollama show qwen2.5-coder:7b
```

### Debug Router State

```python
# Add to router
logger.info(f"📍 Current stage: {memory.stage.value}")
logger.info(f"📋 Gathered params: {memory.gathered_params}")
logger.info(f"💬 User input: {user_input}")
```

### Debug Prompt Logging

```python
# Enable prompt logging in .env
ENABLE_PROMPT_LOGGING=true
PROMPT_LOG_DIR=prompt_logs

# Check logged prompts
# Each session creates a directory: prompt_logs/session_20251203_143052/
# Individual files: 0001_job_agent.txt, 0002_sql_agent.txt, etc.
# Combined log: all_prompts.jsonl
```

**Prompt File Format:**
```
=== PROMPT ===
Agent: job_agent
Timestamp: 2025-12-03 14:30:52

--- SYSTEM ---
Extract params for read_sql job...

--- USER ---
Last question: "What job name?"
User answer: "customer_data"
...

--- RESPONSE ---
{"action": "TOOL", "params": {"name": "customer_data"}}

--- METADATA ---
{"stage": "execute_sql", "tool": "read_sql"}
```

### Debug Dropdown Selection

```python
# Add to app.py callback
logger.info(f"🔘 Dropdown callback triggered")
logger.info(f"   n_clicks: {n_clicks}")
logger.info(f"   selected_values: {selected_values}")
logger.info(f"   triggered_id: {callback_context.triggered[0]['prop_id']}")
```

## Common Issues

### Issue: LLM Reloading on Every Request

**Symptoms**:
- `ollama ps` shows model timer resetting to 59 minutes
- Slow response times (5-10s)

**Diagnosis**:
```python
# Check if singleton is working
logger.info(f"🔧 Router instance ID: {id(router)}")
logger.info(f"🔧 Job agent instance ID: {id(job_agent)}")
# Should show same IDs across requests
```

**Solution**:
- Ensure `get_default_router_orchestrator()` used
- Check singleton globals not being reset
- Verify `keep_alive="3600s"` configured

### Issue: Confirmation Word Extracted as Parameter

**Symptoms**:
- User says "okay", system extracts it as job name

**Diagnosis**:
```python
# Check gathered_params state
logger.info(f"📋 Gathered params before filtering: {memory.gathered_params}")
# Should be empty when filtering should trigger
```

**Solution**:
- Add confirmation word filter to handler
- Check filter applied before job_agent call
- Ensure condition: `not memory.gathered_params`

### Issue: Dropdown Not Appearing

**Symptoms**:
- System asks for connection in text instead of dropdown

**Diagnosis**:
```python
# Check validator action
logger.info(f"🔧 Validator action: {result.action}")
# Should be FETCH_CONNECTIONS, not ASK
```

**Solution**:
- Check `memory.available_connections` populated
- Verify validator returns FETCH action
- Ensure handler formats response correctly
- Check UI parses dropdown format

### Issue: JSON Serialization Error

**Symptoms**:
- `Object of type ColumnSchema is not JSON serializable`

**Diagnosis**:
```python
# Check for duplicate variables
var_names = [v.definition_id for v in payload.variables]
logger.info(f"Variables: {var_names}")
# Look for duplicates
```

**Solution**:
- Implement `get_excluded_fields()` in builder
- Return fields that need special handling
- Ensure base builder skips excluded fields

## Performance Optimization

### Reduce Prompt Size

**Before**:
```python
prompt = f"""Available connections:
{format_all_connections(100+ connections)}  # 1000+ chars

Select connection:
"""
```

**After**:
```python
# Use dropdown instead
return ValidationResult(action="FETCH_CONNECTIONS")
```

**Result**: ~1000 char reduction, faster response

### Limit LLM Output

```python
ChatOllama(
    model="qwen2.5-coder:7b",  # For SQL agent
    # OR
    model="qwen3:8b",           # For job agent
)
```

### Cache Expensive Operations

```python
# Cache schemas per connection
if connection_id not in memory.available_schemas:
    schemas = fetch_schemas(connection_id)  # API call
    memory.available_schemas[connection_id] = schemas
else:
    schemas = memory.available_schemas[connection_id]  # Instant
```

### Use Singleton Pattern

```python
# Instead of:
def create_router():
    return RouterOrchestrator(...)  # New instance every time

# Use:
def get_default_router():
    global _default_router
    if _default_router is None:
        _default_router = RouterOrchestrator(...)
    return _default_router  # Reuse instance
```

## Best Practices

### 1. Always Use Singletons for LLM Agents
- Module-level globals
- Check for None before creating
- Log when creating new instances

### 2. Prefer Dropdowns Over LLM Extraction
- Faster (no LLM call)
- More reliable (no extraction errors)
- Better UX (visual selection)

### 3. Filter Confirmation Words
- After any system confirmation message
- Check `gathered_params` is empty
- Clear `user_input` if match found

### 4. Use Excluded Fields for Complex Types
- Override `get_excluded_fields()`
- Handle excluded fields in subclass
- Prevents duplicate variables

### 5. Keep Prompts Concise
- Only essential information
- Use examples sparingly
- Avoid listing large datasets
- Use structured output (JSON)

### 6. Log Extensively in Development
- Log stage transitions
- Log parameter gathering
- Log LLM calls and responses
- Log dropdown interactions

### 7. Test Edge Cases
- Empty input
- Confirmation words
- Duplicate dropdown buttons
- Missing parameters
- Invalid selections

## Deployment

### Production Checklist

- [ ] All tests passing
- [ ] Logging configured (not DEBUG)
- [ ] Error handling in place
- [ ] keep_alive configured
- [ ] Singleton pattern verified
- [ ] Dropdowns tested for all job types
- [ ] API endpoints accessible
- [ ] Database connections configured
- [ ] Ollama models available
- [ ] Performance benchmarks met

### Environment Variables

```bash
# .env
OLLAMA_HOST=http://localhost:11434
ICC_API_BASE=https://172.16.22.13:8084
DB_CONFIG_PATH=db_config.json
LOG_LEVEL=INFO
```

### Monitoring

```python
# Add metrics
from prometheus_client import Counter, Histogram

request_count = Counter('router_requests_total', 'Total requests')
response_time = Histogram('router_response_seconds', 'Response time')

@response_time.time()
async def process_input(memory, user_input):
    request_count.inc()
    # ... processing
```

## Resources

### Documentation
- Architecture: `docs/ARCHITECTURE.md`
- Technical Details: `docs/TECHNICAL_DETAILS.md`
- This Guide: `docs/DEVELOPER_GUIDE.md`

### External References
- Ollama: https://ollama.ai
- LangChain: https://python.langchain.com
- Dash: https://dash.plotly.com

### Support
- Check logs in application output
- Use `ollama ps` to verify model status
- Test individual components with unit tests
- Review conversation history in memory
