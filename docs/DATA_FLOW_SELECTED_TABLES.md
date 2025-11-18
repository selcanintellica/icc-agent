# Data Flow: UI Selection → Job Execution

This document explains how user selections from the UI flow through the system to populate job fields.

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (app.py)                  │
│                                                                   │
│  1️⃣ Connection Dropdown    →  oracle_10                         │
│  2️⃣ Schema Dropdown        →  SALES                             │
│  3️⃣ Tables Dropdown        →  [customers, orders]               │
│                                                                   │
│  Stored in: config-store = {                                     │
│    "connection": "oracle_10",                                    │
│    "schema": "SALES",                                            │
│    "tables": ["customers", "orders"]                             │
│  }                                                                │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         │ User asks: "Get customers from USA"
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              ROUTER INVOCATION (app.py:254)                      │
│                                                                   │
│  invoke_router_async(                                            │
│    user_message="Get customers from USA",                        │
│    connection="oracle_10",     ← from config-store              │
│    schema="SALES",              ← from config-store              │
│    selected_tables=["customers", "orders"]  ← from config-store │
│  )                                                                │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              MEMORY UPDATE (app.py:285-287)                      │
│                                                                   │
│  memory.connection = "oracle_10"                                 │
│  memory.schema = "SALES"                                         │
│  memory.selected_tables = ["customers", "orders"]                │
│                                                                   │
│  Memory stored in: session_memories["web-chat-session"]          │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              ROUTER: NEED_QUERY STAGE (router.py:48-55)         │
│                                                                   │
│  call_sql_agent(                                                 │
│    user_utterance="Get customers from USA",                      │
│    connection=memory.connection,      ← "oracle_10"             │
│    schema=memory.schema,              ← "SALES"                  │
│    selected_tables=memory.selected_tables  ← ["customers",...]  │
│  )                                                                │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│           SQL AGENT: LOAD SCHEMAS (sql_agent.py:86-87)          │
│                                                                   │
│  schema_definitions = load_table_definitions(                    │
│    connection="oracle_10",                                       │
│    schema="SALES",                                               │
│    tables=["customers", "orders"]                                │
│  )                                                                │
│                                                                   │
│  ↓ Calls schema_loader.load_multiple_tables()                   │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│        SCHEMA LOADER: LOAD FILES (schema_loader.py:160-178)     │
│                                                                   │
│  For each table in ["customers", "orders"]:                      │
│    1. Load file: schema_docs/oracle_10/SALES/customers.txt      │
│    2. Load file: schema_docs/oracle_10/SALES/orders.txt         │
│    3. Combine content with separators                            │
│                                                                   │
│  Returns: Full text of both table definitions                    │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│         SQL AGENT: GENERATE SQL (sql_agent.py:93-96)            │
│                                                                   │
│  Builds prompt with schema_definitions:                          │
│                                                                   │
│  "You have access to these tables:                               │
│   [Full customers.txt content]                                   │
│   =====================================                           │
│   [Full orders.txt content]                                      │
│                                                                   │
│   Generate SQL for: Get customers from USA"                      │
│                                                                   │
│  LLM Response: {                                                 │
│    "sql": "SELECT * FROM customers WHERE country = 'USA'",       │
│    "reasoning": "..."                                            │
│  }                                                                │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              ROUTER: HAVE_SQL STAGE (router.py:67-105)          │
│                                                                   │
│  Generated SQL stored in: memory.last_sql                        │
│                                                                   │
│  When executing read_sql_job:                                    │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ ReadSqlLLMRequest(                                   │       │
│  │   variables=[ReadSqlVariables(                       │       │
│  │     query=memory.last_sql,  ← Generated SQL          │       │
│  │     connection=memory.connection,  ← "oracle_10"     │       │
│  │     execute_query=True                               │       │
│  │   )]                                                  │       │
│  │ )                                                     │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  Response: {                                                     │
│    "job_id": "12345",                                            │
│    "columns": ["customer_id", "first_name", "country"]           │
│  }                                                                │
│                                                                   │
│  Stored in memory:                                               │
│    memory.last_job_id = "12345"                                  │
│    memory.last_columns = ["customer_id", ...]                    │
└────────────────────────┬──────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│       ROUTER: NEED_WRITE_OR_EMAIL STAGE (router.py:122-230)     │
│                                                                   │
│  User chooses: "write to customer_data"                          │
│                                                                   │
│  When executing write_data_job:                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ WriteDataLLMRequest(                                 │       │
│  │   variables=[WriteDataVariables(                     │       │
│  │     data_set=memory.last_job_id,  ← "12345"         │       │
│  │     connection=params.get("connection"),             │       │
│  │     table=params.get("table"),                       │       │
│  │     columns=columns_from_memory,                     │       │
│  │     drop_or_truncate=params.get("drop_or_truncate"), │       │
│  │     only_dataset_columns=True                        │       │
│  │   )]                                                  │       │
│  │ )                                                     │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  OR                                                               │
│                                                                   │
│  User chooses: "email to user@example.com"                       │
│                                                                   │
│  When executing send_email_job:                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ SendEmailLLMRequest(                                 │       │
│  │   variables=[SendEmailVariables(                     │       │
│  │     query=memory.last_sql,  ← Generated SQL          │       │
│  │     connection=memory.connection,  ← "oracle_10"     │       │
│  │     to=params.get("to"),                             │       │
│  │     subject=params.get("subject"),                   │       │
│  │     text=params.get("text"),                         │       │
│  │     attachment=True                                  │       │
│  │   )]                                                  │       │
│  │ )                                                     │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Field Mappings by Job Type

### 1. SEND EMAIL JOB (`send_email_job`)

**Location**: `router.py:189-214`

```python
SendEmailLLMRequest(
    rights={"owner": "184431757886694"},
    props={...},
    variables=[SendEmailVariables(
        query=memory.last_sql,              # ✅ SQL generated by SQL agent
        connection=memory.connection,        # ✅ User selected from UI
        to=params.get("to"),                # User provides in chat
        subject=params.get("subject"),      # User provides in chat
        text=params.get("text"),            # User provides in chat
        attachment=True                     # Fixed value
    )]
)
```

**Field Sources**:
- ✅ `query` → `memory.last_sql` (generated by SQL agent in NEED_QUERY stage)
- ✅ `connection` → `memory.connection` (user selected from UI dropdown)
- ❓ `to`, `subject`, `text` → Extracted from user's chat message by `job_agent`

---

### 2. READ SQL JOB (`read_sql_job`)

**Location**: `router.py:82-96`

```python
ReadSqlLLMRequest(
    rights={"owner": "184431757886694"},
    props={...},
    variables=[ReadSqlVariables(
        query=memory.last_sql,           # ✅ SQL generated by SQL agent
        connection=memory.connection,     # ✅ User selected from UI
        execute_query=True,              # Fixed value
        table_name="",                   # ⚠️ Currently not set (should be empty)
    )]
)
```

**Field Sources**:
- ✅ `query` → `memory.last_sql` (generated by SQL agent)
- ✅ `connection` → `memory.connection` (user selected from UI)
- ✅ `table_name` → **Should always be empty** (as per your requirement)
- ✅ `execute_query` → `True` (always execute)

**Returns**:
- `job_id` → Stored in `memory.last_job_id`
- `columns` → Stored in `memory.last_columns`

---

### 3. WRITE DATA JOB (`write_data_job`)

**Location**: `router.py:146-175`

```python
WriteDataLLMRequest(
    rights={"owner": "184431757886694"},
    props={...},
    variables=[WriteDataVariables(
        data_set=memory.last_job_id,                 # ✅ Job ID from read_sql
        columns=columns,                             # From memory.last_columns
        add_columns=[],                              # ⚠️ Should always be empty
        connection=params.get("connection"),          # ❓ Should use memory.connection
        schemas=params.get("schemas"),                # ❓ Should use memory.schema
        table=params.get("table"),                   # User provides table name
        drop_or_truncate=params.get("drop_or_truncate"), # User chooses: DROP/TRUNCATE/INSERT
        only_dataset_columns=True                    # Fixed value
    )]
)
```

**Field Sources**:
- ✅ `data_set` → `memory.last_job_id` (from previous read_sql job)
- ✅ `columns` → `memory.last_columns` (columns returned by read_sql)
- ⚠️ `add_columns` → **Should always be empty array `[]`**
- ❓ `connection` → **Should use `memory.connection`** (user selected from UI)
- ❓ `schemas` → **Should use `memory.schema`** (user selected from UI)
- ❓ `table` → User provides in chat (destination table name)
- ❓ `drop_or_truncate` → User chooses: `"DROP"`, `"TRUNCATE"`, or `"INSERT"`
- ✅ `only_dataset_columns` → `True` (fixed)

---

## Current Issues & Required Fixes

### Issue 1: READ SQL - table_name field
**Current**: Not explicitly set
**Required**: Should always be empty `""`
**Fix Location**: `router.py:82-96`

```python
# Add table_name parameter
ReadSqlVariables(
    query=memory.last_sql,
    connection=memory.connection,
    execute_query=True,
    table_name=""  # ← ADD THIS
)
```

### Issue 2: WRITE DATA - add_columns field
**Current**: Not explicitly set
**Required**: Should always be empty array
**Fix Location**: `router.py:146-175`

```python
# Ensure add_columns is empty
WriteDataVariables(
    data_set=memory.last_job_id,
    columns=columns,
    add_columns=[],  # ← ENSURE THIS IS ALWAYS []
    connection=params.get("connection"),
    ...
)
```

### Issue 3: WRITE DATA - connection/schema should use memory
**Current**: Uses `params.get("connection")` which requires user to specify again
**Required**: Should use `memory.connection` and `memory.schema` from UI selection
**Fix Location**: `router.py:146-175`

```python
# Change from params to memory
WriteDataVariables(
    ...
    connection=memory.connection,  # ← Use memory instead of params
    schemas=memory.schema,         # ← Use memory instead of params (note: schemas in API but schema in memory)
    ...
)
```

### Issue 4: WRITE DATA - drop_or_truncate options
**Current**: Extracted from user message
**Required**: Validate that value is one of: `"DROP"`, `"TRUNCATE"`, or `"INSERT"`
**Fix Location**: `router.py` or `job_agent.py`

---

## Summary: Where selected_tables is Used

`selected_tables` flows through these locations:

1. **UI Selection** (`app.py:104`) → User selects tables from dropdown
2. **Config Store** (`app.py:190`) → Stored in browser state
3. **Router Invocation** (`app.py:470`) → Passed as parameter
4. **Memory Update** (`app.py:285-287`) → Stored in session memory
5. **SQL Agent Call** (`router.py:48-55`) → Passed to SQL generator
6. **Table Loading** (`sql_agent.py:86-87`) → Used to load specific `.txt` files
7. **Schema Context** (`schema_loader.py:160-178`) → Files loaded and combined

**selected_tables is NOT directly used in job creation** - it's only used to:
1. Load the correct table definition files
2. Build context for SQL generation
3. The generated SQL then references those tables

The actual job fields use:
- `connection` (from UI) → Used in all 3 jobs
- `schema` (from UI) → Used in write_data job
- `query` (generated SQL) → Used in read_sql and send_email jobs
- `job_id` (from read_sql result) → Used in write_data job

---

## Code References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| UI Dropdowns | `app.py` | 78-113 | User selects connection, schema, tables |
| Config Storage | `app.py` | 190 | Stores selections in browser |
| Router Invocation | `app.py` | 254-287 | Passes selections to router |
| Memory Class | `memory.py` | 27-33 | Stores connection, schema, selected_tables |
| SQL Agent Call | `router.py` | 48-55 | Passes to SQL generator |
| Schema Loading | `sql_agent.py` | 86-87 | Loads table definition files |
| File Loading | `schema_loader.py` | 160-178 | Reads `.txt` files |
| Read SQL Job | `router.py` | 82-96 | Creates read_sql job |
| Write Data Job | `router.py` | 146-175 | Creates write_data job |
| Send Email Job | `router.py` | 189-214 | Creates send_email job |
