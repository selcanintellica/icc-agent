# ICC Agent - Technical Details

## Router Orchestrator Deep Dive

### Singleton Implementation (src/ai/router/router.py)

```python
# Module-level singleton instances
_default_sql_agent: Optional[ChatOllama] = None
_default_job_agent: Optional[ChatOllama] = None
_default_router_orchestrator: Optional[RouterOrchestrator] = None

def get_default_agents() -> Tuple[ChatOllama, ChatOllama]:
    """Create or reuse singleton agent instances"""
    global _default_sql_agent, _default_job_agent
    
    if _default_sql_agent is None:
        logger.info("🔧 Creating singleton SQL Agent")
        _default_sql_agent = create_sql_agent()
    
    if _default_job_agent is None:
        logger.info("🔧 Creating singleton Job Agent")
        _default_job_agent = create_job_agent()
    
    return _default_sql_agent, _default_job_agent

def get_default_router_orchestrator() -> RouterOrchestrator:
    """Get or create singleton router orchestrator"""
    global _default_router_orchestrator
    
    if _default_router_orchestrator is None:
        sql_agent, job_agent = get_default_agents()
        router_config = RouterConfig(...)
        _default_router_orchestrator = RouterOrchestrator(
            router_config,
            sql_agent=sql_agent,
            job_agent=job_agent
        )
    
    return _default_router_orchestrator
```

**Why This Matters**:
- Without singletons: New router → new LLM instances → Ollama reloads model (~5-10s)
- With singletons: Reuse LLM instances → model stays loaded → instant responses
- Check with `ollama ps`: Timer should reset but model stays loaded

### RouterOrchestrator Class

**Key Methods**:

1. **process_input()**
   ```python
   async def process_input(self, memory: Memory, user_input: str) -> RouterResponse:
       # Check for special prefixes (dropdown selections)
       if user_input.startswith("__CONNECTION_SELECTED__:"):
           connection_id = user_input.split(":", 1)[1]
           memory.gathered_params["connection"] = connection_id
           # Continue processing without LLM call
       
       # Delegate to current stage handler
       stage = memory.current_stage
       handler = self._get_handler(stage)
       return await handler.handle(memory, user_input)
   ```

2. **_get_handler()**
   - Maps stage to handler instance
   - Handlers created once at router initialization
   - Same handler instances reused across requests

**Handler Registration** (by job type):
```python
registry = HandlerRegistry()

# Register handlers by job type (not by individual stages)
registry.register("readsql", ReadSQLHandler(sql_agent=..., job_agent=...))
registry.register("comparesql", CompareSQLHandler(sql_agent=..., job_agent=...))
registry.register("writedata", WriteDataHandler(job_agent=...))
registry.register("sendemail", SendEmailHandler(job_agent=...))

# Each handler manages multiple stages via MANAGED_STAGES
# Router calls registry.get_handler(stage) which finds handler.can_handle(stage)
```

## Stage Handlers

**Handler Dependencies:**
- **ReadSQLHandler**: Uses both SQL agent (query generation) and job agent (parameters)
- **CompareSQLHandler**: Uses both SQL agent (two queries) and job agent (parameters)
- **WriteDataHandler**: Uses only job agent (no SQL generation needed)
- **SendEmailHandler**: Uses only job agent (auto-generates query from table info, no SQL agent)

### ReadSQL Handler (src/ai/router/stage_handlers/readsql_handler.py)

**Managed Stages**: `ASK_SQL_METHOD`, `NEED_NATURAL_LANGUAGE`, `NEED_USER_SQL`, `CONFIRM_GENERATED_SQL`, `CONFIRM_USER_SQL`, `EXECUTE_SQL`, `SHOW_RESULTS`, `NEED_WRITE_OR_EMAIL`

**Typical Flow**:
```
ask_sql_method → need_natural_language → confirm_generated_sql → execute_sql → show_results
```

**Example Logic** (simplified pseudocode):

1. **Handling natural language input**:
   ```python
   async def handle(self, memory: Memory, user_input: str):
       # Call SQL agent to generate SQL
       sql_query = await call_sql_agent(
           memory=memory,
           user_input=user_input,
           model=self.sql_agent
       )
       
       # Store SQL in memory
       memory.job_context["sql_query"] = sql_query
       
       # Transition to confirmation stage
       memory.stage = Stage.CONFIRM_GENERATED_SQL
       
       return StageHandlerResult(
           new_stage=Stage.CONFIRM_GENERATED_SQL,
           message=f"Here's the SQL:\n{sql_query}\n\nLooks good?"
       )
   ```

2. **Handling SQL confirmation**:
   ```python
   async def handle(self, memory: Memory, user_input: str):
       # Check for approval
       if user_input.lower() in ["yes", "y", "correct", "ok", "okay"]:
           memory.stage = Stage.EXECUTE_SQL
           return StageHandlerResult(
               new_stage="execute_sql",
               message="Great! Executing SQL..."
           )
       else:
           # Regenerate or cancel
           # ...
   ```

3. **_handle_execute_sql()** - **Confirmation Word Filtering**
   ```python
   async def _handle_execute_sql(self, memory: Memory, user_input: str):
       # KEY FIX: Filter confirmation words when no params gathered yet
       if not memory.gathered_params and \
          user_input.lower().strip() in ["yes", "ok", "okay", "sure", "correct"]:
           logger.info(f"🔄 Ignoring confirmation message '{user_input}'")
           user_input = ""  # Clear input to prevent extraction
       
       # Call job agent to gather parameters
       action = call_job_agent(
           memory=memory,
           user_input=user_input,
           tool_name="read_sql"
       )
       
       if action.action_type == "TOOL":
           # Execute job
           result = execute_read_sql_job(memory.gathered_params)
           memory.current_stage = "show_results"
           return RouterResponse(
               new_stage="show_results",
               message=f"Query executed! Job ID: {result.job_id}"
           )
   ```

**Why Filtering Works**:
- User says "okay" right after "Executing SQL..." message
- At this point, `gathered_params` is empty (no job name yet)
- Filter catches "okay" and sets `user_input = ""`
- Job agent receives empty string, doesn't extract anything
- Next real input (job name) gets extracted correctly

### WriteData Handler (src/ai/router/stage_handlers/writedata_handler.py)

**Stage Flow**:
```
need_write_params → execute_write
```

**Key Features**:

1. **Dropdown Optimization**
   ```python
   async def _handle_need_write_params(self, memory: Memory, user_input: str):
       action = call_job_agent(memory, user_input, "write_data")
       
       if action.action_type == "FETCH_CONNECTIONS":
           # Return dropdown format
           connections = memory.available_connections
           return RouterResponse(
               new_stage="need_write_params",
               message=f"CONNECTION_DROPDOWN:{json.dumps(connections)}"
           )
       
       if action.action_type == "FETCH_SCHEMAS":
           connection = memory.gathered_params["write_count_connection"]
           schemas = fetch_schemas(connection)
           return RouterResponse(
               new_stage="need_write_params",
               message=f"SCHEMA_DROPDOWN:{json.dumps(schemas)}"
           )
   ```

2. **Parameter Naming Consistency**
   - All references use singular: `write_count_schema` (not `write_count_schemas`)
   - Checked in lines 121-123 for write_count support
   - Assigned in line 198 after schema selection
   - Validated in `parameter_validator.py` line 286

### SendEmail Handler (src/ai/router/stage_handlers/sendemail_handler.py)

**Purpose**: Send query results via email

**Key Features**:

1. **Auto-Query Generation** (NOT using SQL agent)
   ```python
   # Generate from output_table_info (result table)
   schema = memory.output_table_info.get("schema")
   table = memory.output_table_info.get("table")
   auto_query = f"SELECT * FROM {schema}.{table}"
   ```

2. **Requires WriteData First**
   ```python
   if not memory.output_table_info:
       return self._create_result(
           memory,
           "You need to write the data to a table first before sending an email."
       )
   ```

3. **Query Confirmation Flow**
   - Shows auto-generated query for user approval
   - User can say "yes" to use it or "no" to provide custom query
   - Executes send_email_job with confirmed query

**Stage Flow**:
```
confirm_email_query → need_email_query (optional) → execute_email_job
```

**Why No SQL Agent?**:
- Email always sends from a result table (created by WriteData)
- Simple `SELECT *` query is auto-generated from table metadata
- No need for natural language to SQL conversion

### CompareSQL Handler (src/ai/router/stage_handlers/comparesql_handler.py)

**Purpose**: Compare results of two SQL queries with column mapping

**Uses Both Agents**:
- SQL agent for generating queries from natural language
- Job agent for gathering comparison parameters

**Stage Flow** (17 stages total):
```
ask_first_sql_method → [generate or manual first SQL] → confirm_first_sql
  → ask_second_sql_method → [generate or manual second SQL] → confirm_second_sql
  → ask_auto_match → [optional: waiting_map_table]
  → ask_reporting_type → ask_compare_schema → ask_compare_table_name
  → ask_compare_job_name → execute_compare_sql
```

**Key Features**:
1. Supports both generated and manual SQL for each query
2. Auto-column matching or manual mapping
3. Flexible reporting types
4. Stores comparison results in specified table

## LLM Agents

### Job Agent (src/ai/router/job_agent.py)

**Purpose**: Extract structured parameters from user input

**Configuration**:
```python
ChatOllama(
    model="qwen3:8b",        # Configurable via MODEL_NAME env var
    temperature=0.1,
    keep_alive="3600s",
    num_predict=4096,
    timeout=30.0
)
```

**Prompt Structure**:
```
Extract params for {job_name} job.

IGNORE: "ok", "okay", "yes", "no", "sure" - NOT parameter values!

Required params:
1. name: Job name
2. connection: Database connection (UI shows dropdown)
3. ...

IMPORTANT: Only extract actual values from user input.

Output JSON: {"action": "ASK"|"TOOL", "question": "...", "params": {...}}
```

**Key Logic**:
```python
def call_job_agent(memory: Memory, user_input: str, tool_name: str) -> AgentAction:
    # Check if user_input is a command (no extraction needed)
    if user_input.lower() in ["write", "email", "both", "done"]:
        logger.info(f"📝 Skipping LLM extraction for command: '{user_input}'")
        # Process command directly
    
    # Build prompt with current context
    prompt = build_job_prompt(
        tool_name=tool_name,
        gathered_params=memory.gathered_params,
        last_question=memory.last_question,
        user_input=user_input
    )
    
    # Call LLM
    response = job_agent.invoke(prompt)
    
    # Parse JSON response
    action = parse_agent_response(response)
    
    return action
```

### SQL Agent (src/ai/router/sql_agent.py)

**Purpose**: Generate SQL from natural language

**Configuration**:
```python
ChatOllama(
    model="qwen2.5-coder:7b",  # Specialized coding model, configurable via SQL_MODEL_NAME
    temperature=0.1,
    keep_alive="3600s",
    num_predict=2048           # Max SQL length
)
```

**Prompt Structure**:
```
Generate SQL for: {user_request}

Schema: {schema_name}
Available tables: {table_list}
Table columns:
- customers: customer_id, name, email, ...
- orders: order_id, customer_id, amount, ...

Requirements:
- Use correct table/column names from schema
- Generate SELECT query only
- No INSERT/UPDATE/DELETE

Output: SQL query only, no explanation.
```

**Key Logic**:
```python
async def call_sql_agent(memory: Memory, user_input: str, model: ChatOllama) -> str:
    # Get schema context
    connection = memory.selected_connection
    schema = memory.selected_schema
    tables = memory.selected_tables
    
    # Fetch table metadata
    table_info = get_table_columns(connection, schema, tables)
    
    # Build prompt
    prompt = build_sql_prompt(
        user_request=user_input,
        schema=schema,
        table_info=table_info
    )
    
    # Generate SQL
    response = model.invoke(prompt)
    sql_query = extract_sql(response)
    
    return sql_query
```

## Parameter Validation

### ParameterValidator (src/ai/router/validators/parameter_validator.py)

**Purpose**: Check required parameters and determine next action

**Key Method**:
```python
def validate_params(
    tool_name: str,
    gathered_params: dict,
    memory: Memory
) -> ValidationResult:
    # Get required params for this job type
    required = get_required_params(tool_name)
    
    # Check each required parameter
    for param in required:
        if param not in gathered_params:
            # Check if dropdown available
            if param == "connection" and memory.available_connections:
                return ValidationResult(
                    action="FETCH_CONNECTIONS",
                    missing_param="connection"
                )
            
            if param == "schemas":
                # Use singular param name
                schema_param = f"{get_param_prefix(tool_name)}_schema"
                connection = gathered_params.get(f"{get_param_prefix(tool_name)}_connection")
                
                if connection and schema_param not in gathered_params:
                    # Check if schemas cached
                    if connection in memory.available_schemas:
                        return ValidationResult(
                            action="FETCH_SCHEMAS",
                            missing_param=schema_param
                        )
            
            # No dropdown available, ask user
            return ValidationResult(
                action="ASK",
                missing_param=param,
                question=f"What {param} should I use?"
            )
    
    # All params present
    return ValidationResult(action="TOOL")
```

**Dropdown Logic**:
1. Check if parameter missing
2. Check if dropdown data available in memory
3. Return FETCH action instead of ASK
4. Handler returns special format: `CONNECTION_DROPDOWN:{json}`
5. UI renders dropdown
6. User selection sent with prefix: `__CONNECTION_SELECTED__:value`
7. Router assigns directly to memory (bypasses LLM)

**Parameter Prefix Pattern**:
- ReadSQL: No prefix (e.g., `connection`, `schema`)
- WriteData with write_count: `write_count_connection`, `write_count_schema`
- Email: No prefix
- Consistent singular form throughout

## Payload Builders

### Excluded Fields Pattern

**Problem**: 
- Base builder iterates all gathered_params
- Adds each as wire variable
- Template-specific builders also add certain params with special formatting
- Result: Duplicate variables (e.g., `columns` added twice)

**Solution**:

1. **BaseBuilder.get_excluded_fields()**
   ```python
   class BaseBuilder(ABC):
       def get_excluded_fields(self) -> List[str]:
           """Override in subclasses to exclude fields from base processing"""
           return []
       
       def build(self, params: dict) -> WirePayload:
           excluded = self.get_excluded_fields()
           self._build_base_variables(params, excluded_fields=excluded)
           # ...
       
       def _build_base_variables(self, params: dict, excluded_fields: List[str]):
           for key, value in params.items():
               if key not in excluded_fields:
                   # Add to wire variables
   ```

2. **WriteDataBuilder Override**
   ```python
   class WriteDataBuilder(BaseBuilder):
       def get_excluded_fields(self) -> List[str]:
           return ["columns", "add_columns", "data_set"]
       
       def build(self, params: dict) -> WirePayload:
           # Base builder skips columns/data_set
           payload = super().build(params)
           
           # Add columns as JSON
           if "columns" in params:
               columns_json = json.dumps(params["columns"])
               payload.add_variable("columns_definition_id", columns_json)
           
           # Add data_set with metadata
           if "data_set" in params:
               data_set_var = WireVariable(
                   definition_id="data_set_definition_id",
                   value=params["data_set"],
                   metadata={"type": "ResultSet", "job_id": params["source_job_id"]}
               )
               payload.add_variable(data_set_var)
           
           return payload
   ```

**Result**:
- Base builder adds simple parameters
- Template-specific builder handles complex types
- No duplicates, clean JSON serialization

### QueryBuilder (ReadSQL)

```python
class QueryBuilder(BaseBuilder):
    def build(self, params: dict) -> WirePayload:
        payload = super().build(params)
        
        # Add SQL query
        payload.add_variable("query_definition_id", params["sql_query"])
        
        # Add connection
        payload.add_variable("connection_definition_id", params["connection"])
        
        # Add columns (from SQL result)
        if "columns" in params:
            columns_json = json.dumps([{"columnName": col} for col in params["columns"]])
            payload.add_variable("columns_definition_id", columns_json)
        
        return payload
```

## Memory Management

### Memory Class Structure

```python
@dataclass
class Memory:
    conversation_history: List[Message]
    available_connections: List[dict]
    available_schemas: Dict[str, List[str]]
    gathered_params: Dict[str, Any]
    current_stage: str
    job_context: Dict[str, Any]
    
    # Context properties
    @property
    def selected_connection(self) -> Optional[str]:
        return self.job_context.get("connection")
    
    @property
    def selected_schema(self) -> Optional[str]:
        return self.job_context.get("schema")
```

### Connection/Schema Caching

```python
# On startup (app.py)
config_loader = ConfigLoader("db_config.json")
connections = config_loader.get_all_connections()

# Store in memory
memory.available_connections = connections

# On first schema fetch for a connection
connection_id = "ORACLE_10"
if connection_id not in memory.available_schemas:
    schemas = fetch_schemas(connection_id)
    memory.available_schemas[connection_id] = schemas

# Subsequent fetches use cache
schemas = memory.available_schemas[connection_id]  # Instant
```

### Parameter Clearing

```python
# When switching job types
if memory.current_job_type != new_job_type:
    memory.gathered_params.clear()
    memory.job_context.clear()
    memory.current_job_type = new_job_type
```

## Web UI Integration

### Dropdown Rendering (app.py)

```python
@app.callback(
    Output('chat-display', 'children'),
    Input('send-button', 'n_clicks'),
    State('user-input', 'value')
)
def process_message(n_clicks, user_input):
    response = router.process_input(memory, user_input)
    
    # Check for dropdown format
    if response.message.startswith("CONNECTION_DROPDOWN:"):
        json_str = response.message.split(":", 1)[1]
        connections = json.loads(json_str)
        
        # Render dropdown
        dropdown = dcc.Dropdown(
            id={'type': 'connection-select', 'param': 'connection'},
            options=[{'label': c['name'], 'value': c['id']} for c in connections],
            placeholder="Select connection..."
        )
        
        return [..., dropdown, confirm_button]
```

### Dropdown Selection Handling

```python
@app.callback(
    Output('chat-display', 'children', allow_duplicate=True),
    Input({'type': 'connection-confirm', 'param': ALL}, 'n_clicks'),
    State({'type': 'connection-select', 'param': ALL}, 'value'),
    prevent_initial_call=True
)
def handle_connection_selection(n_clicks, selected_connections):
    # Find which button was clicked
    triggered_id = callback_context.triggered[0]['prop_id']
    button_idx = None
    
    for i, clicks in enumerate(n_clicks):
        if clicks is not None and clicks > 0:
            button_idx = i
            break
    
    if button_idx is None:
        return dash.no_update
    
    # Get selected value and param name
    connection_id = selected_connections[button_idx]
    param_name = callback_context.inputs_list[0][button_idx]['id']['param']
    
    # Format with special prefix
    selection_input = f"__CONNECTION_SELECTED__:{connection_id}"
    
    # Process through router
    response = router.process_input(memory, selection_input)
    
    return render_chat_display(memory)
```

**Special Prefix Handling in Router**:
```python
def process_input(self, memory: Memory, user_input: str) -> RouterResponse:
    # Check for dropdown selection
    if user_input.startswith("__CONNECTION_SELECTED__:"):
        param_value = user_input.split(":", 1)[1]
        param_name = determine_param_name(memory.current_stage)
        memory.gathered_params[param_name] = param_value
        # Continue processing without LLM
    
    # ... rest of processing
```

## Testing Strategies

### Unit Tests

1. **Handler Tests**
   ```python
   async def test_readsql_confirmation_filtering():
       handler = ReadSQLHandler(config, sql_agent, job_agent)
       memory = create_test_memory()
       memory.current_stage = "execute_sql"
       memory.gathered_params = {}  # Empty
       
       # User says "okay" after confirmation
       response = await handler.handle(memory, "okay")
       
       # Should not extract "okay" as job name
       assert "okay" not in memory.gathered_params.values()
   ```

2. **Validator Tests**
   ```python
   def test_parameter_validator_singular_form():
       params = {"write_count_connection": "ORACLE_10"}
       memory = create_test_memory()
       
       result = validate_params("write_data", params, memory)
       
       # Should look for singular form
       assert result.missing_param == "write_count_schema"
       assert result.action == "FETCH_SCHEMAS"
   ```

3. **Payload Builder Tests**
   ```python
   def test_writedata_excluded_fields():
       builder = WriteDataBuilder()
       params = {
           "name": "test_job",
           "columns": [{"columnName": "id"}, {"columnName": "name"}],
           "data_set": {...}
       }
       
       payload = builder.build(params)
       
       # Should have only one columns variable
       columns_vars = [v for v in payload.variables if "columns" in v.definition_id]
       assert len(columns_vars) == 1
   ```

### Integration Tests

```python
async def test_full_readsql_flow():
    # Initialize router with singleton agents
    router = get_default_router_orchestrator()
    memory = Memory()
    
    # Step 1: User requests data
    response = await router.process_input(memory, "get customers from USA")
    assert response.new_stage == Stage.CONFIRM_GENERATED_SQL
    assert "SELECT" in response.message
    
    # Step 2: User confirms
    response = await router.process_input(memory, "yes")
    assert response.new_stage == Stage.EXECUTE_SQL
    
    # Step 3: User says "okay" (should be filtered)
    response = await router.process_input(memory, "okay")
    assert response.new_stage == "execute_sql"  # Still waiting for job name
    
    # Step 4: User provides job name
    response = await router.process_input(memory, "usa_customers")
    assert response.new_stage == "show_results"
    assert "job_id" in memory.job_context
```

## Performance Monitoring

### LLM Status Check

```python
# Check Ollama model status
import subprocess

result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
print(result.stdout)

# Expected output when singleton working:
# NAME           ID              SIZE    PROCESSOR    UNTIL
# qwen3:8b      abc123...       5.5 GB  100% GPU     59 minutes from now
```

### Response Time Logging

```python
import time

@measure_time
async def process_input(self, memory: Memory, user_input: str):
    start = time.time()
    
    response = await self._handle_request(memory, user_input)
    
    elapsed = time.time() - start
    logger.info(f"⏱️ Request processed in {elapsed:.2f}s")
    
    return response
```

### Expected Timings
- **With Singleton + keep_alive**: 0.5-2s per request
- **Without Singleton**: 5-10s per request (model reload)
- **Dropdown Selection**: <0.1s (no LLM call)
