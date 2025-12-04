# ICC Agent - System Architecture

## Overview

The ICC Agent is a natural language interface for database operations. Users describe what they want in plain English, and the system translates those requests into executable database jobs.

## High-Level Architecture

```
┌─────────────────┐
│   Dash Web UI   │  (User Interface)
│   (app.py)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Router         │  (Orchestrator - singleton instance)
│  Orchestrator   │  Manages state machine & delegates to handlers
└────────┬────────┘
         │
         ├──────────────┬──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ ReadSQL  │   │WriteData │   │SendEmail │   │CompareSQL│   │  Router  │
  │ Handler  │   │ Handler  │   │ Handler  │   │ Handler  │   │ Handler  │
  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
       │              │              │              │              │
       ├──────────────┴──────────────┼──────────────┴──────────────┤
       ▼                             ▼                             ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │              LLM Agents (Singleton)                             │
  │  ┌──────────────┐         ┌──────────────┐                    │
  │  │  SQL Agent   │         │  Job Agent   │                    │
  │  │(SQL Generate)│         │ (Parameters) │                    │
  │  └──────────────┘         └──────────────┘                    │
  │                                                                 │
  │  ReadSQL: both agents  │  CompareSQL: both agents             │
  │  WriteData: job agent  │  SendEmail: job agent only           │
  └─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Web UI (app.py)
- **Purpose**: Dash-based web interface
- **Responsibilities**:
  - Renders chat interface
  - Displays dropdown menus for connections/schemas
  - Manages user sessions
  - Handles dropdown selections with special prefixes
- **Key Features**:
  - Connection/schema selection bypasses LLM
  - Dropdown rendering based on handler responses
  - Session-based memory management

### 2. Router Orchestrator (src/ai/router/router.py)
- **Purpose**: Central state machine controller
- **Pattern**: **Singleton** - single instance reused across all requests via `get_default_router_orchestrator()`
- **Responsibilities**:
  - Receives user input and current stage
  - Delegates to appropriate stage handler
  - Maintains conversation flow
  - Manages memory state
- **Performance**: Singleton pattern prevents LLM reloading between requests

### 3. Stage Handlers
Each handler manages a specific job type's conversation flow:

#### ReadSQL Handler (src/ai/router/stage_handlers/readsql_handler.py)
- **Stages**: 
  - `Stage.ASK_SQL_METHOD` → Choose between generating SQL or providing manually
  - `Stage.NEED_NATURAL_LANGUAGE` → Generate SQL from natural language
  - `Stage.NEED_USER_SQL` → User provides SQL manually
  - `Stage.CONFIRM_GENERATED_SQL` / `Stage.CONFIRM_USER_SQL` → Show SQL for user approval
  - `Stage.EXECUTE_SQL` → Gather parameters (job name)
  - `Stage.SHOW_RESULTS` → Display results & offer next actions
  - `Stage.NEED_WRITE_OR_EMAIL` → Ask what to do with results
- **Key Feature**: Filters confirmation words to prevent extraction as parameters
- **Managed Stages**: 8 stages total (defined in `MANAGED_STAGES` set)

#### WriteData Handler (src/ai/router/stage_handlers/writedata_handler.py)
- **Stages**:
  - `Stage.NEED_WRITE_OR_EMAIL` → Entry point (delegates from ReadSQL results)
  - Gathers: connection, schema, table, drop_or_truncate option
- **Parameter Optimization**: Uses dropdowns for connection/schema selection
- **Note**: Triggered after ReadSQL execution when user chooses "write"
- **Managed Stages**: 1 stage (shares `NEED_WRITE_OR_EMAIL` with ReadSQL)

#### SendEmail Handler (src/ai/router/stage_handlers/sendemail_handler.py)
- **Stages**:
  - `Stage.CONFIRM_EMAIL_QUERY` → Confirm auto-generated query from result table
  - `Stage.NEED_EMAIL_QUERY` → User provides custom query
- **Note**: Does NOT use SQL agent - generates query automatically from output_table_info
- **Flow**: Requires WriteData first → auto-generates `SELECT * FROM schema.table` from result table
- **Key Feature**: Validates that data was written to table before allowing email
- **Managed Stages**: 2 stages for email flow

#### CompareSQL Handler (src/ai/router/stage_handlers/comparesql_handler.py)
- **Stages**:
  - `Stage.ASK_FIRST_SQL_METHOD` → Choose generation or manual SQL for first query
  - `Stage.NEED_FIRST_NATURAL_LANGUAGE` → Generate first SQL from natural language
  - `Stage.NEED_FIRST_USER_SQL` → User provides first SQL manually
  - `Stage.CONFIRM_FIRST_GENERATED_SQL` / `Stage.CONFIRM_FIRST_USER_SQL` → Confirm first SQL
  - `Stage.ASK_SECOND_SQL_METHOD` → Choose method for second query
  - `Stage.NEED_SECOND_NATURAL_LANGUAGE` → Generate second SQL
  - `Stage.NEED_SECOND_USER_SQL` → User provides second SQL
  - `Stage.CONFIRM_SECOND_GENERATED_SQL` / `Stage.CONFIRM_SECOND_USER_SQL` → Confirm second SQL
  - `Stage.ASK_AUTO_MATCH` → Ask if auto-match columns
  - `Stage.WAITING_MAP_TABLE` → Wait for manual column mapping
  - `Stage.ASK_REPORTING_TYPE` → Choose reporting type
  - `Stage.ASK_COMPARE_SCHEMA` → Select schema for comparison results
  - `Stage.ASK_COMPARE_TABLE_NAME` → Name the comparison table
  - `Stage.ASK_COMPARE_JOB_NAME` → Name the comparison job
  - `Stage.EXECUTE_COMPARE_SQL` → Execute comparison
- **Uses Both Agents**: SQL agent for query generation, job agent for parameters
- **Managed Stages**: 14 stages for complete comparison workflow

### 4. LLM Agents (Singleton Pattern)

#### SQL Agent (src/ai/router/sql_agent.py)
- **Purpose**: Generate SQL from natural language
- **Model**: `qwen2.5-coder:7b` (configurable via `SQL_MODEL_NAME` env var)
- **Configuration**:
  - `temperature=0.1`
  - `keep_alive="3600s"`
  - `num_predict=2048`
- **Used By**: ReadSQLHandler, CompareSQLHandler
- **Note**: Specialized coding model for better SQL generation
- **Prompt Logging**: When `ENABLE_PROMPT_LOGGING=true`, saves all prompts to `prompt_logs/session_TIMESTAMP/NNNN_sql_agent.txt`

#### Job Agent (src/ai/router/job_agent.py)
- **Purpose**: Extract job parameters from user input
- **Model**: `qwen3:8b` (configurable via `MODEL_NAME` env var)
- **Configuration**: 
  - `temperature=0.1`
  - `keep_alive="3600s"`
  - `num_predict=4096`
  - `timeout=30.0`
- **Key Feature**: Filters confirmation words ("yes", "ok", "okay", etc.)
- **Used By**: All handlers (ReadSQL, WriteData, SendEmail, CompareSQL)
- **Prompt Logging**: When `ENABLE_PROMPT_LOGGING=true`, saves all prompts to `prompt_logs/session_TIMESTAMP/NNNN_job_agent.txt`

### 5. Parameter Validator (src/ai/router/validators/parameter_validator.py)
- **Purpose**: Check required parameters & determine next action
- **Actions**:
  - `ASK` → Use LLM to ask user for missing parameter
  - `FETCH_CONNECTIONS` → Trigger connection dropdown
  - `FETCH_SCHEMAS` → Trigger schema dropdown
  - `TOOL` → Execute job with complete parameters
- **Optimization**: Returns FETCH actions instead of ASK when dropdowns available

### 6. Payload Builders (src/payload_builders/)
- **Purpose**: Convert parameters to wire protocol format
- **Pattern**: Template method with excluded fields
- **Key Classes**:
  - `BaseBuilder` - Base processing with exclusion support
  - `WriteDataBuilder` - Handles columns/data_set JSON serialization
  - `QueryBuilder` - Builds ReadSQL payloads
- **Fix**: Excluded fields pattern prevents duplicate wire variables

## Data Flow

### 1. Standard Request Flow
```
User Input → Router → Handler → Job Agent → Parameter Validator
                                              ↓
                                      [Has all params?]
                                              ↓
                                         Yes ┘ └ No
                                         ↓         ↓
                                      TOOL      ASK/FETCH
                                         ↓         ↓
                                   Execute Job   Get Input
```

### 2. Dropdown Optimization Flow
```
User: "read data from customers"
        ↓
Router → ReadSQL Handler → Job Agent
        ↓
Parameter Validator: Missing connection
        ↓
Return: FETCH_CONNECTIONS
        ↓
Handler returns: CONNECTION_DROPDOWN:{json}
        ↓
UI renders dropdown → User selects "ORACLE_10"
        ↓
UI sends: __CONNECTION_SELECTED__:ORACLE_10
        ↓
Router: Direct memory assignment (bypasses LLM)
        ↓
Continue parameter gathering...
```

### 3. Confirmation Word Filtering
```
System: "Great! Executing SQL..."
User: "okay"
        ↓
ReadSQL Handler → _handle_execute_sql
        ↓
Checks: gathered_params is empty?
        ↓
Filters: "okay" in ["yes", "ok", "okay", "sure", "correct"]
        ↓
Sets user_input = "" (ignore confirmation)
        ↓
Job Agent doesn't extract "okay" as job name
```

## Key Optimizations

### 1. Singleton Pattern for LLM Persistence
**Problem**: Creating new router on every request → new LLM instances → model reload
**Solution**: Module-level singleton agents
- `_default_router_orchestrator` - Single router instance
- `_default_sql_agent` - Single SQL agent instance
- `_default_job_agent` - Single job agent instance
**Result**: LLMs stay loaded in memory, ~5s response time improvement

### 2. Dropdown Bypass
**Problem**: LLM extraction unreliable for connections/schemas, wastes tokens
**Solution**: Return FETCH actions → UI dropdown → special prefix selection
**Result**: 
- No LLM calls for connection/schema selection
- Reduced prompt size (~1000 chars saved)
- Faster, more reliable selections

### 3. Excluded Fields Pattern
**Problem**: Fields like `columns` added twice (base + template-specific builder)
**Solution**: Template builders declare excluded fields
**Result**: Clean payloads, no JSON serialization errors

### 4. Confirmation Word Filtering
**Problem**: "okay" acknowledgments extracted as parameter values
**Solution**: Filter confirmation words when no params gathered yet
**Result**: Natural conversation flow without spurious parameter extraction

## Memory Management

### Memory Structure
```python
{
    "conversation_history": [...],  # Full chat history
    "available_connections": [...], # Cached from config
    "available_schemas": {...},     # Cached per connection
    "gathered_params": {...},       # Current job parameters
    "current_stage": "...",         # State machine position
    "job_context": {...}            # Job-specific data (SQL, results, etc.)
}
```

### Special Memory Keys
- `available_connections` - Populated from db_config.json at startup
- `available_schemas[connection_id]` - Cached after first fetch
- `gathered_params` - Cleared when switching job types
- `job_context.sql_query` - SQL generated by SQL agent
- `job_context.job_id` - ID of last executed job

## Configuration

### LLM Settings
```python
# Job Agent (Parameter Extraction)
ChatOllama(
    model="qwen3:8b",         # Default, configurable via MODEL_NAME
    temperature=0.1,
    keep_alive="3600s",       # Keep in memory 1 hour
    num_predict=4096,         # Max response tokens
    timeout=30.0
)

# SQL Agent (SQL Generation)
ChatOllama(
    model="qwen2.5-coder:7b", # Default, configurable via SQL_MODEL_NAME
    temperature=0.1,
    keep_alive="3600s",       # Keep in memory 1 hour
    num_predict=2048          # Max SQL length
)
```

### keep_alive Behavior
- Timer resets on every request (Ollama feature)
- Model stays loaded as long as requests arrive within timeout
- Singleton pattern ensures same instance reused
- Check with `ollama ps` - should show model loaded continuously

## Development Workflow

### Adding a New Job Type
1. Create handler in `src/ai/router/stage_handlers/`
2. Define stage flow and transitions
3. Add parameter definitions to `src/ai/router/prompts/`
4. Create payload builder in `src/payload_builders/builders/`
5. Register handler in `router.py`
6. Add toolkit function in `src/ai/toolkits/`

### Modifying Prompts
- Job agent prompts: `src/ai/router/prompts/prompt_manager.py`
- SQL agent prompts: `src/ai/router/sql_agent.py`
- Keep prompts concise to reduce tokens
- Avoid listing all connections (use dropdowns)

### Testing
- Unit tests: Test handlers, validators, builders in isolation
- Integration tests: Test full flow from user input to job creation
- Use `test_router.py` for router testing
- Use `test_auth.py` for API authentication
