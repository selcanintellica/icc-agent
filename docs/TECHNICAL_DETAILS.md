# ICC Agent - Technical Details

## Backend Service Layer

### Service Architecture (src/services/)

The backend uses a service layer pattern to decouple API routes from core business logic:

```python
# Service initialization at startup (backend/main.py)
@app.on_event("startup")
async def startup_event():
    # Initialize singleton services
    router_service = get_router_service()      # Manages router invocation
    session_manager = get_session_manager()    # Manages user sessions
    connection_service = get_connection_service()  # Provides metadata
    
    logger.info("✓ All services initialized")
```

### RouterService (src/services/router_service.py)

**Purpose**: Orchestrates router invocation with memory management

**Key Method**:
```python
async def invoke_router(
    self,
    user_input: str,
    memory: Memory,
    connection: Optional[str] = None,
    schema: Optional[str] = None,
    selected_tables: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Invoke router with optional connection info pre-population.
    
    Returns:
        Dict with response, memory, success flag, and optional error info
    """
    try:
        # Populate memory with connection info if provided
        if connection and schema and selected_tables:
            memory.connection_manager.default_connection = connection
            memory.connection_manager.default_schema = schema
            memory.connection_manager.selected_tables = selected_tables
        
        # Invoke router
        memory, response_text = await handle_turn(memory, user_input)
        
        return {
            "response": response_text,
            "memory": memory,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error invoking router: {e}", exc_info=True)
        error_info = UIFormatter.format_error_for_ui(e)
        return {
            "error": str(e),
            "error_info": error_info,
            "success": False
        }
```

### SessionManager (src/services/session_manager.py)

**Purpose**: Manages user sessions and associated memory states

**Key Methods**:
```python
class SessionManager:
    def __init__(self, storage: Optional[Dict[str, Memory]] = None):
        """Initialize with optional storage backend (defaults to in-memory dict)"""
        self._storage = storage if storage is not None else {}
    
    def get_or_create_session(self, session_id: str) -> Memory:
        """Get existing session or create new one with fresh Memory"""
        if session_id not in self._storage:
            logger.info(f"Creating new session: {session_id}")
            self._storage[session_id] = create_memory()
        return self._storage[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and free memory"""
        if session_id in self._storage:
            del self._storage[session_id]
            return True
        return False
```

**Storage Backend**: Currently in-memory dict, can be swapped for Redis, database, etc.

### ConnectionService (src/services/connection_service.py)

**Purpose**: Provides database metadata (connections, schemas, tables)

**Key Methods**:
```python
class ConnectionService:
    def get_connections(self) -> List[Dict[str, Any]]:
        """Get all available connections from config"""
        return config_loader.get_available_connections()
    
    def get_schemas(self, connection_id: str) -> List[str]:
        """Get schemas for specific connection"""
        return config_loader.get_schemas_for_connection(connection_id)
    
    async def get_tables(
        self, 
        connection_id: str, 
        schema_name: str
    ) -> List[Dict[str, Any]]:
        """Get tables for specific schema (calls ICC API)"""
        return await config_loader.get_tables_for_schema(connection_id, schema_name)
```

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

## Stage Handlers (Strategy Pattern)

**Architecture Overview**:
- **Base Class**: `StageStrategy` (abstract)
  - Method: `execute(memory, user_input)` - implemented by each strategy
  - Method: `handle_with_help(memory, user_input)` - checks for help, delegates to execute
  - Integration: Automatic help system detection

- **Handler Orchestration**:
  - Handler has `StageStrategyRegistry`
  - Registry maps `Stage` enum → strategy instance
  - Handler delegates to strategy via `strategy.handle_with_help()`

- **Strategy Location**: `src/ai/router/stage_handlers/strategies/{job_type}/`

**Handler Dependencies:**
- **ReadSQLHandler**: Uses both SQL agent (query generation) and job agent (parameters)
- **CompareSQLHandler**: Uses both SQL agent (two queries) and job agent (parameters)
- **WriteDataHandler**: Uses only job agent (no SQL generation needed)
- **SendEmailHandler**: Uses only job agent (auto-generates query from table info, no SQL agent)

### ReadSQL Handler (src/ai/router/stage_handlers/readsql_handler.py)

**Architecture**: Strategy Pattern with `StageStrategyRegistry`

**Managed Stages & Strategies**:
- `Stage.ASK_SQL_METHOD` → `AskSqlMethodStrategy`
- `Stage.NEED_NATURAL_LANGUAGE` → `NeedNaturalLanguageStrategy`
- `Stage.NEED_USER_SQL` → `NeedUserSqlStrategy`
- `Stage.CONFIRM_GENERATED_SQL` → `ConfirmGeneratedSqlStrategy`
- `Stage.CONFIRM_USER_SQL` → `ConfirmUserSqlStrategy`
- `Stage.EXECUTE_SQL` → `ExecuteSqlStrategy`
- `Stage.SHOW_RESULTS` → `ShowResultsStrategy`
- `Stage.NEED_WRITE_OR_EMAIL` → `NeedWriteOrEmailStrategy`

**Strategy Location**: `src/ai/router/stage_handlers/strategies/readsql/`

**Typical Flow**:
```
Stage.ASK_SQL_METHOD → Stage.NEED_NATURAL_LANGUAGE → Stage.CONFIRM_GENERATED_SQL → Stage.EXECUTE_SQL → Stage.SHOW_RESULTS
```

**Handler Implementation**:
```python
class ReadSQLHandler(BaseStageHandler):
    def __init__(self, config, sql_agent, job_agent):
        # Create registry
        self.strategy_registry = StageStrategyRegistry()
        
        # Register strategies
        self.strategy_registry.register(
            Stage.NEED_NATURAL_LANGUAGE,
            NeedNaturalLanguageStrategy(sql_agent=sql_agent)
        )
        # ... register all 8 strategies
    
    async def handle(self, memory: Memory, user_input: str):
        # Get strategy for current stage
        strategy = self.strategy_registry.get_strategy(memory.current_stage)
        
        if strategy:
            # Automatically checks for help before executing
            return await strategy.handle_with_help(memory, user_input)
```

**Example Logic** (simplified pseudocode):

1. **Handling natural language input**:
   ```python
   async def handle(self, memory: Memory, user_input: str):
       # Call SQL agent to generate SQL (with prompt logging if enabled)
       sql_query = await call_sql_agent(
           memory=memory,
           user_input=user_input,
           model=self.sql_agent
       )
       # Note: If ENABLE_PROMPT_LOGGING=true, prompt saved to:
       # prompt_logs/session_TIMESTAMP/NNNN_sql_agent.txt
       
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
               new_stage=Stage.EXECUTE_SQL,
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
           memory.stage = Stage.SHOW_RESULTS
           return StageHandlerResult(
               new_stage=Stage.SHOW_RESULTS,
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

**Managed Stages**: `Stage.NEED_WRITE_OR_EMAIL` (shared entry point with ReadSQL)

**Stage Flow**:
```
Stage.NEED_WRITE_OR_EMAIL → execute write job
```

**Key Features**:

1. **Dropdown Optimization**
   ```python
   async def _handle_need_write_params(self, memory: Memory, user_input: str):
       # Call job agent with prompt logging if enabled
       action = call_job_agent(memory, user_input, "write_data")
       # Prompt saved to: prompt_logs/session_TIMESTAMP/NNNN_job_agent.txt
       
       if action.action_type == "FETCH_CONNECTIONS":
           # Return dropdown format
           connections = memory.available_connections
           return StageHandlerResult(
               new_stage=Stage.NEED_WRITE_OR_EMAIL,
               message=f"CONNECTION_DROPDOWN:{json.dumps(connections)}"
           )
       
       if action.action_type == "FETCH_SCHEMAS":
           connection = memory.gathered_params["write_count_connection"]
           schemas = fetch_schemas(connection)
           return StageHandlerResult(
               new_stage=Stage.NEED_WRITE_OR_EMAIL,
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

**Managed Stages**: `Stage.CONFIRM_EMAIL_QUERY`, `Stage.NEED_EMAIL_QUERY`

**Stage Flow**:
```
Stage.CONFIRM_EMAIL_QUERY → Stage.NEED_EMAIL_QUERY (optional) → execute_email_job
```

**Why No SQL Agent?**:
- Email always sends from a result table (created by WriteData)
- Simple `SELECT *` query is auto-generated from table metadata
- No need for natural language to SQL conversion

### CompareSQL Handler (src/ai/router/stage_handlers/comparesql_handler.py)

**Purpose**: Compare results of two SQL queries with column mapping

**Architecture**: Strategy Pattern with 14 dedicated strategy classes

**Uses Both Agents**:
- SQL agent for generating queries from natural language
- Job agent for gathering comparison parameters

**Strategy Location**: `src/ai/router/stage_handlers/strategies/comparesql/`

**Managed Stages & Strategies**: 14 total
- `AskFirstSQLMethodStrategy`, `NeedFirstNaturalLanguageStrategy`, `NeedFirstUserSQLStrategy`
- `ConfirmFirstSQLStrategy` (handles both generated and manual)
- `AskSecondSQLMethodStrategy`, `NeedSecondNaturalLanguageStrategy`, `NeedSecondUserSQLStrategy`
- `ConfirmSecondSQLStrategy` (handles both generated and manual)
- `AskAutoMatchStrategy`, `WaitingMapTableStrategy`
- `AskReportingTypeStrategy`, `AskCompareSchemaStrategy`, `AskCompareTableNameStrategy`
- `AskCompareJobNameStrategy` (handles execution)

**Stage Flow**:
```
Stage.ASK_FIRST_SQL_METHOD → [generate or manual first SQL] → Stage.CONFIRM_FIRST_GENERATED_SQL
  → Stage.ASK_SECOND_SQL_METHOD → [generate or manual second SQL] → Stage.CONFIRM_SECOND_GENERATED_SQL
  → Stage.ASK_AUTO_MATCH → [optional: Stage.WAITING_MAP_TABLE]
  → Stage.ASK_REPORTING_TYPE → Stage.ASK_COMPARE_SCHEMA → Stage.ASK_COMPARE_TABLE_NAME
  → Stage.ASK_COMPARE_JOB_NAME → Stage.EXECUTE_COMPARE_SQL
```

**Key Features**:
1. Each stage isolated in dedicated strategy class
2. Supports both generated and manual SQL for each query
3. Auto-column matching or manual mapping
4. Flexible reporting types
5. Automatic help system integration for all 14 stages
6. Stores comparison results in specified table

## Help System

### HelpHandler (src/ai/router/utils/help_handler.py)

**Purpose**: Context-aware help responses for any stage

**Key Components**:

1. **Help Detection** (`is_help_request()`):
   ```python
   def is_help_request(user_input: str) -> bool:
       """Check if user is asking for help"""
       help_keywords = ["help", "?", "what", "how", "explain"]
       return any(keyword in user_input.lower() for keyword in help_keywords)
   ```

2. **Stage Descriptions** (`_get_stage_description()`):
   ```python
   descriptions = {
       Stage.NEED_USER_SQL: "providing your SQL query",
       Stage.NEED_SECOND_USER_SQL: "providing your SECOND SQL query for comparison",
       Stage.ASK_REPORTING_TYPE: "selecting the reporting type (identical, different, or all)",
       # 25+ stage descriptions
   }
   ```

3. **Context-Aware Responses**:
   - Shows gathered parameters
   - Shows current SQL (for CompareSQL, shows first SQL when asking for second)
   - Lists available options (connections, schemas)
   - Human-readable stage explanations (prevents literal interpretation)

**Integration with Strategy Pattern**:
```python
class StageStrategy(ABC):
    async def handle_with_help(self, memory: Memory, user_input: str):
        """Check for help request, delegate to execute if not help"""
        if is_help_request(user_input):
            help_response = self._help_handler.get_help_response(
                memory,
                user_input,
                current_stage=self.get_stage()
            )
            return self._create_result(memory, message=help_response)
        
        # Not help - execute normal strategy logic
        return await self.execute(memory, user_input)
```

**Example Help Flow**:
```
User at Stage.NEED_SECOND_USER_SQL types: "help"

Help System:
1. Detects help keyword via is_help_request()
2. Gets stage description: "providing your SECOND SQL query for comparison"
3. Injects context:
   - Current stage: need_second_user_sql
   - First SQL already provided: "SELECT * FROM customers"
   - Gathered params: {...}
4. Builds LLM prompt with instructions:
   - "DO NOT interpret stage names literally"
   - "Explain what user needs to do at this stage"
5. Returns: "You're providing the second SQL query to compare against your first query: SELECT * FROM customers..."
```

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

**Prompt Logging** (when `ENABLE_PROMPT_LOGGING=true`):
- Saves every prompt to: `prompt_logs/session_TIMESTAMP/NNNN_job_agent.txt`
- Includes system prompt, user prompt, response, and metadata
- Useful for debugging parameter extraction issues

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

**Prompt Logging** (when `ENABLE_PROMPT_LOGGING=true`):
- Saves every prompt to: `prompt_logs/session_TIMESTAMP/NNNN_sql_agent.txt`
- Includes schema context, table metadata, user request, and generated SQL
- Useful for debugging SQL generation quality and table context issues

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

## Job Prompts

### Job Prompt Organization (src/ai/router/prompts/job_prompts/)

**Purpose**: Organized, reusable prompt templates for each job type

**Structure**:
```
job_prompts/
  __init__.py
  write_data_prompt.py     # WriteDataPrompt class
  read_sql_prompt.py       # ReadSQLPrompt class
  send_email_prompt.py     # SendEmailPrompt class
```

**Pattern**: Each prompt class contains:
- `TOOL_NAME`: Job identifier
- `REQUIRED_PARAMS`: List of required parameters
- `PARAM_DESCRIPTIONS`: Human-readable descriptions
- `get_system_message()`: Build system prompt
- `get_user_message()`: Build user prompt

**Example**:
```python
class WriteDataPrompt:
    TOOL_NAME = "write_data"
    
    REQUIRED_PARAMS = [
        "name",
        "write_count_connection",
        "write_count_schema",
        "write_count_table",
        "drop_or_truncate"
    ]
    
    PARAM_DESCRIPTIONS = {
        "name": "Job name",
        "write_count_connection": "Database connection ID",
        "write_count_schema": "Target schema name",
        "write_count_table": "Target table name",
        "drop_or_truncate": "Action before insert (DROP or TRUNCATE)"
    }
    
    @staticmethod
    def get_system_message(gathered_params):
        return f"""Extract parameters for write_data job.
        
Required:
- name: Job name
- write_count_connection: Connection (UI shows dropdown)
- write_count_schema: Schema (UI shows dropdown)
- write_count_table: Table name
- drop_or_truncate: DROP or TRUNCATE

IMPORTANT: Only extract actual values from user input.
"""
```

**Usage in PromptManager**:
```python
from .job_prompts import WriteDataPrompt, ReadSQLPrompt, SendEmailPrompt

TOOL_PARAMS = {
    "write_data": {
        "required": WriteDataPrompt.REQUIRED_PARAMS,
        "descriptions": WriteDataPrompt.PARAM_DESCRIPTIONS
    },
    # ...
}
```

**Note**: CompareSQL uses stage-by-stage validation (no dedicated prompt file)

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
