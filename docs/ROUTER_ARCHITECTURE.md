# Router System Architecture

## Overview

The Router is the central orchestrator of the ICC Agent system. It implements a **staged conversation flow** with 10 distinct stages, managing state transitions, agent invocation, and conversation memory. This architecture is specifically designed for small language models (7B-8B parameters) by eliminating complex reasoning loops.

## Core Concepts

### Why Staged Router?

Traditional AI agents use ReAct (Reasoning + Acting) patterns where the LLM:
1. Reasons about what to do next
2. Chooses and calls tools
3. Evaluates results
4. Repeats until task is complete

**Problems with ReAct for small LLMs:**
- ❌ Multi-step reasoning is unreliable
- ❌ Tool selection is ambiguous
- ❌ Easy to loop infinitely or fail
- ❌ Requires 70B+ models for reliability

**Staged Router Solution:**
- ✅ Each stage has ONE clear purpose
- ✅ Router handles ALL flow logic (deterministic)
- ✅ Specialized agents at specific stages only
- ✅ Clear success/failure paths
- ✅ Works reliably with 7B-8B models

### State Machine

The router implements a finite state machine where:
- **States** are conversation stages (10 total)
- **Transitions** are deterministic based on user input/job results
- **Memory** persists context across stages
- **Agents** are invoked only at specific stages

## Stage Definitions

All stages are defined in `src/ai/router/memory.py`:

```python
class Stage(str, Enum):
    START = "START"
    ASK_SQL_METHOD = "ASK_SQL_METHOD"
    NEED_NATURAL_LANGUAGE = "NEED_NATURAL_LANGUAGE"
    NEED_USER_SQL = "NEED_USER_SQL"
    CONFIRM_GENERATED_SQL = "CONFIRM_GENERATED_SQL"
    CONFIRM_USER_SQL = "CONFIRM_USER_SQL"
    EXECUTE_SQL = "EXECUTE_SQL"
    SHOW_RESULTS = "SHOW_RESULTS"
    NEED_WRITE_OR_EMAIL = "NEED_WRITE_OR_EMAIL"
    DONE = "DONE"
```

## 10-Stage Flow

### 1. START

**Purpose:** Initialize conversation and greet user

**Router Behavior:**
- Outputs welcome message
- Transitions to ASK_SQL_METHOD

**User Input:** N/A (automatic transition)

**Memory Updates:**
- `stage` = START
- Initial connection set from UI selection

**Transition:**
```
START → ASK_SQL_METHOD (automatic)
```

---

### 2. ASK_SQL_METHOD

**Purpose:** Let user choose between agent-generated SQL or providing their own

**Router Behavior:**
- Asks: "Would you like me to generate SQL or provide your own? (generate/provide)"
- Waits for user response

**User Input:**
- "generate" → Agent will create SQL from natural language
- "provide" → User will write SQL directly

**Memory Updates:**
- `stage` = ASK_SQL_METHOD
- `sql_method` = user's choice

**Transitions:**
```
ASK_SQL_METHOD → NEED_NATURAL_LANGUAGE (if "generate")
ASK_SQL_METHOD → NEED_USER_SQL (if "provide")
```

---

### 3A. NEED_NATURAL_LANGUAGE (Generation Path)

**Purpose:** Get natural language description from user for SQL generation

**Router Behavior:**
- Asks: "What would you like to query?"
- Waits for user description
- Invokes SQL Agent with table definitions
- Stores generated SQL in memory

**User Input:** Natural language query description
- Example: "Get all customers from USA who ordered in 2024"

**Agent Invoked:** SQL Agent (`qwen2.5-coder:7b`, temp=0.1)

**Memory Updates:**
- `stage` = NEED_NATURAL_LANGUAGE
- `natural_language_query` = user's description
- `sql` = generated SQL query

**Transitions:**
```
NEED_NATURAL_LANGUAGE → CONFIRM_GENERATED_SQL (after SQL generation)
```

---

### 3B. NEED_USER_SQL (Direct Path)

**Purpose:** Get SQL query directly from user

**Router Behavior:**
- Asks: "Please provide your SQL query:"
- Waits for user to paste/type SQL
- Stores SQL in memory (no generation)

**User Input:** Complete SQL query
- Example: "SELECT * FROM customers WHERE country = 'USA'"

**Agent Invoked:** None

**Memory Updates:**
- `stage` = NEED_USER_SQL
- `sql` = user's provided SQL

**Transitions:**
```
NEED_USER_SQL → CONFIRM_USER_SQL (after SQL provided)
```

---

### 4A. CONFIRM_GENERATED_SQL

**Purpose:** Let user review agent-generated SQL before execution

**Router Behavior:**
- Shows generated SQL
- Asks: "Shall I execute this query? (yes/no)"
- Waits for confirmation

**User Input:**
- "yes" → Execute SQL
- "no" → Go back to NEED_NATURAL_LANGUAGE to regenerate

**Memory Updates:**
- `stage` = CONFIRM_GENERATED_SQL

**Transitions:**
```
CONFIRM_GENERATED_SQL → EXECUTE_SQL (if "yes")
CONFIRM_GENERATED_SQL → NEED_NATURAL_LANGUAGE (if "no")
```

---

### 4B. CONFIRM_USER_SQL

**Purpose:** Let user review their provided SQL before execution

**Router Behavior:**
- Shows user's SQL
- Asks: "Should I execute this query? (yes/no)"
- Waits for confirmation

**User Input:**
- "yes" → Execute SQL
- "no" → Go back to NEED_USER_SQL to modify

**Memory Updates:**
- `stage` = CONFIRM_USER_SQL

**Transitions:**
```
CONFIRM_USER_SQL → EXECUTE_SQL (if "yes")
CONFIRM_USER_SQL → NEED_USER_SQL (if "no")
```

---

### 5. EXECUTE_SQL

**Purpose:** Create read job and execute SQL query via API

**Router Behavior:**
- Converts connection name to connection ID
- Calls `read_sql_job` tool with connection ID, SQL, database type
- Waits for job completion
- Stores results in memory
- Shows results to user

**User Input:** N/A (automatic after confirmation)

**Tool Invoked:** `read_sql_job(connection_id, query, database_type)`

**Memory Updates:**
- `stage` = EXECUTE_SQL
- `job_id` = read job ID from API
- `results` = query results

**Connection ID Conversion:**
```python
from src.utils.connections import get_connection_id

connection_id = get_connection_id(memory.connection)
# Example: "ORACLE_10" → 1
```

**Transitions:**
```
EXECUTE_SQL → SHOW_RESULTS (after successful execution)
EXECUTE_SQL → CONFIRM_GENERATED_SQL or CONFIRM_USER_SQL (if execution fails)
```

---

### 6. SHOW_RESULTS

**Purpose:** Display query results and determine next action

**Router Behavior:**
- Shows query results (formatted table)
- Asks: "What would you like to do next? (write/email/done)"
- Waits for user decision

**User Input:**
- "write" → Write results to database
- "email" → Send results via email
- "done" → End conversation

**Memory Updates:**
- `stage` = SHOW_RESULTS

**Transitions:**
```
SHOW_RESULTS → NEED_WRITE_OR_EMAIL (if "write" or "email")
SHOW_RESULTS → DONE (if "done")
```

---

### 7. NEED_WRITE_OR_EMAIL

**Purpose:** Handle write/email job creation with parameter extraction

**Router Behavior:**
- If write: Invokes Job Agent to extract target schema/table/connection
- If email: Invokes Job Agent to extract recipients/subject/body
- Creates job via appropriate tool
- Returns to SHOW_RESULTS for next action

**User Input Examples:**
- Write: "write to backup_schema customers_archive table"
- Email: "send to manager@company.com with subject Monthly Report"

**Agent Invoked:** Job Agent (`qwen3:8b`, temp=0.3)

**Tools Invoked:**
- Write: `write_data_job(connection_id, schema, table, data, mappings)`
- Email: `send_email_job(recipients, subject, body, data, format)`

**Memory Updates:**
- `stage` = NEED_WRITE_OR_EMAIL
- `write_job_id` or `email_job_id` = job ID from API

**Transitions:**
```
NEED_WRITE_OR_EMAIL → SHOW_RESULTS (after job created, ask what's next)
NEED_WRITE_OR_EMAIL → DONE (if user says done after job)
```

---

### 8. DONE

**Purpose:** End conversation gracefully

**Router Behavior:**
- Outputs farewell message
- Clears memory (optional)
- Conversation complete

**User Input:** N/A

**Memory Updates:**
- `stage` = DONE
- All memory can be cleared

**Transitions:** None (terminal state)

---

## Complete Flow Diagrams

### Generation Path (Agent Creates SQL)

```
START
  ↓ (automatic)
ASK_SQL_METHOD
  ↓ (user: "generate")
NEED_NATURAL_LANGUAGE
  ↓ (SQL Agent generates SQL)
CONFIRM_GENERATED_SQL
  ↓ (user: "yes")      ↓ (user: "no")
  ↓                    ↓
  ↓             [loop back to NEED_NATURAL_LANGUAGE]
  ↓
EXECUTE_SQL
  ↓ (job completes)
SHOW_RESULTS
  ↓ (user: "write" or "email")    ↓ (user: "done")
  ↓                                ↓
NEED_WRITE_OR_EMAIL               DONE
  ↓ (job created)
  ↓
[loop back to SHOW_RESULTS]
```

### Direct Path (User Provides SQL)

```
START
  ↓ (automatic)
ASK_SQL_METHOD
  ↓ (user: "provide")
NEED_USER_SQL
  ↓ (user provides SQL)
CONFIRM_USER_SQL
  ↓ (user: "yes")      ↓ (user: "no")
  ↓                    ↓
  ↓             [loop back to NEED_USER_SQL]
  ↓
EXECUTE_SQL
  ↓ (job completes)
SHOW_RESULTS
  ↓ (user: "write" or "email")    ↓ (user: "done")
  ↓                                ↓
NEED_WRITE_OR_EMAIL               DONE
  ↓ (job created)
  ↓
[loop back to SHOW_RESULTS]
```

## Memory Management

### Memory Dataclass

Defined in `src/ai/router/memory.py`:

```python
@dataclass
class Memory:
    stage: Stage = Stage.START
    connection: str = "oracle_10"
    schema: str = ""
    tables: list = field(default_factory=list)
    sql: str = ""
    job_id: str = ""
    results: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    params: dict = field(default_factory=dict)
    natural_language_query: str = ""
    sql_method: str = ""  # "generate" or "provide"
    write_job_id: str = ""
    email_job_id: str = ""
```

### Memory Lifecycle

**Initialization:**
```python
memory = Memory(connection="oracle_10")  # Set from UI selection
```

**Throughout Conversation:**
- Memory persists across all stages
- Router updates memory fields as stages progress
- Agents read from memory for context

**At Each Stage:**
```python
# Update stage
memory.stage = Stage.NEED_NATURAL_LANGUAGE

# Store user input
memory.natural_language_query = user_input

# Store agent output
memory.sql = generated_sql

# Store job results
memory.results = query_results
memory.job_id = job_id
```

**Memory Cleanup:**
- Can clear after DONE stage
- Or persist for conversation history

## Router Implementation

### Location
`src/ai/router/router.py`

### Main Function

**`handle_turn(user_input: str, memory: Memory) -> tuple[str, Memory]`**

**Parameters:**
- `user_input`: User's message
- `memory`: Current conversation state

**Returns:**
- Tuple of (agent_response, updated_memory)

**Process:**
1. Check current stage
2. Process user input based on stage logic
3. Invoke agents if needed
4. Update memory
5. Transition to next stage
6. Return response and updated memory

### Stage Handlers

Each stage has a dedicated handler function:

```python
def handle_start(memory: Memory) -> tuple[str, Memory]:
    """Initialize conversation"""
    response = "Hello! I'm your database assistant."
    memory.stage = Stage.ASK_SQL_METHOD
    return response, memory

def handle_ask_sql_method(user_input: str, memory: Memory) -> tuple[str, Memory]:
    """Ask user to choose SQL method"""
    if "generate" in user_input.lower():
        memory.sql_method = "generate"
        memory.stage = Stage.NEED_NATURAL_LANGUAGE
        response = "What would you like to query?"
    elif "provide" in user_input.lower():
        memory.sql_method = "provide"
        memory.stage = Stage.NEED_USER_SQL
        response = "Please provide your SQL query:"
    else:
        response = "Would you like me to generate SQL or provide your own? (generate/provide)"
    return response, memory

def handle_need_natural_language(user_input: str, memory: Memory) -> tuple[str, Memory]:
    """Generate SQL from natural language"""
    memory.natural_language_query = user_input
    
    # Invoke SQL Agent
    sql = generate_sql(
        natural_language=user_input,
        tables=memory.tables,
        connection=memory.connection,
        schema=memory.schema
    )
    memory.sql = sql
    memory.stage = Stage.CONFIRM_GENERATED_SQL
    
    response = f"Generated SQL:\n{sql}\n\nShall I execute this query? (yes/no)"
    return response, memory

# ... more handlers for each stage
```

## Agent Invocation

### SQL Agent (NEED_NATURAL_LANGUAGE stage)

```python
from src.ai.router.sql_agent import generate_sql

sql = generate_sql(
    natural_language=memory.natural_language_query,
    tables=memory.tables,
    connection=memory.connection,
    schema=memory.schema
)
```

### Job Agent (NEED_WRITE_OR_EMAIL stage)

```python
from src.ai.router.job_agent import extract_write_parameters, extract_email_parameters

if "write" in user_input:
    params = extract_write_parameters(user_input, {
        "connection": memory.connection,
        "results": memory.results
    })
elif "email" in user_input:
    params = extract_email_parameters(user_input, {
        "results": memory.results
    })
```

## Connection ID Conversion

The router converts connection names to IDs for all API calls:

```python
from src.utils.connections import get_connection_id

# Before executing SQL
connection_id = get_connection_id(memory.connection)

# Call job creation tool with ID
job_id = read_sql_job(
    connection_id=connection_id,  # Integer ID required by API
    query=memory.sql,
    database_type="oracle"
)
```

**Why Conversion?**
- UI and memory use connection names (user-friendly: "ORACLE_10")
- APIs expect connection IDs (database keys: 1)
- `connections.py` maintains the mapping

## Error Handling

### Stage-Specific Errors

**SQL Generation Failure:**
```python
try:
    sql = generate_sql(...)
except Exception as e:
    response = f"Failed to generate SQL: {e}. Please try rephrasing your query."
    # Stay in NEED_NATURAL_LANGUAGE stage
    return response, memory
```

**Query Execution Failure:**
```python
try:
    job_id = read_sql_job(...)
except Exception as e:
    response = f"Query execution failed: {e}. Would you like to modify the SQL?"
    memory.stage = Stage.CONFIRM_GENERATED_SQL  # or CONFIRM_USER_SQL
    return response, memory
```

**Job Creation Failure:**
```python
try:
    write_job_id = write_data_job(...)
except Exception as e:
    response = f"Failed to create write job: {e}. Please check parameters."
    # Stay in NEED_WRITE_OR_EMAIL stage
    return response, memory
```

### General Error Handling

```python
def handle_turn(user_input: str, memory: Memory) -> tuple[str, Memory]:
    try:
        # Stage-specific logic
        ...
    except Exception as e:
        response = f"An error occurred: {e}. Let's start over."
        memory.stage = Stage.START
        return response, memory
```

## Best Practices

### Stage Design
1. ✅ Each stage has ONE clear purpose
2. ✅ Transitions are deterministic (no ambiguity)
3. ✅ Agents invoked only when necessary
4. ✅ Memory updated at every stage
5. ✅ User always knows what to do next

### Memory Management
1. ✅ Store all context needed for future stages
2. ✅ Clear temporary data when no longer needed
3. ✅ Validate memory state before stage transitions
4. ✅ Persist job IDs for status tracking

### Error Recovery
1. ✅ Catch errors at appropriate levels
2. ✅ Provide clear error messages to users
3. ✅ Offer recovery paths (retry, modify, restart)
4. ✅ Log errors for debugging

### Agent Integration
1. ✅ Call agents with complete context
2. ✅ Validate agent outputs before using
3. ✅ Handle agent failures gracefully
4. ✅ Use appropriate temperatures for each agent

## Configuration

### Environment Variables

```env
# Main agent model
MODEL_NAME=qwen3:8b

# SQL generation model
SQL_MODEL_NAME=qwen2.5-coder:7b

# Ollama endpoint
OLLAMA_BASE_URL=http://localhost:11434

# API endpoints
BASE_URL=http://localhost:8000/api
TABLE_API_BASE_URL=http://localhost:8000/api/tables
TABLE_API_MOCK=true
```

## Debugging

### Enable Router Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Trace Stage Transitions

```python
def handle_turn(user_input: str, memory: Memory) -> tuple[str, Memory]:
    print(f"Current Stage: {memory.stage}")
    print(f"User Input: {user_input}")
    
    response, memory = stage_handler(user_input, memory)
    
    print(f"Next Stage: {memory.stage}")
    print(f"Response: {response}")
    
    return response, memory
```

### Test Individual Stages

```python
# Test ASK_SQL_METHOD stage
memory = Memory(stage=Stage.ASK_SQL_METHOD)
response, memory = handle_ask_sql_method("generate", memory)
assert memory.stage == Stage.NEED_NATURAL_LANGUAGE

# Test NEED_NATURAL_LANGUAGE stage
memory = Memory(
    stage=Stage.NEED_NATURAL_LANGUAGE,
    connection="ORACLE_10",
    schema="SALES",
    tables=["customers"]
)
response, memory = handle_need_natural_language("Get customers from USA", memory)
assert memory.sql != ""
assert memory.stage == Stage.CONFIRM_GENERATED_SQL
```

## Related Documentation

- [SQL Agent](SQL_AGENT.md) - Natural language to SQL generation
- [Job Agent](JOB_AGENT.md) - Parameter extraction for jobs
- [Visual Guide](VISUAL_GUIDE.md) - Flow diagrams and examples
