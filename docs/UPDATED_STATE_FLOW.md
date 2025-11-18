# Updated State System - SQL Method Choice

## New Stage Flow

The system now asks users whether they want to provide SQL directly or have the agent generate it from natural language.

## New Stages Added

```python
ASK_SQL_METHOD = "ask_sql_method"                    # Ask user's preference
NEED_NATURAL_LANGUAGE = "need_natural_language"      # Wait for NL query
NEED_USER_SQL = "need_user_sql"                      # Wait for user's SQL
CONFIRM_GENERATED_SQL = "confirm_generated_sql"      # Confirm generated SQL
CONFIRM_USER_SQL = "confirm_user_sql"                # Confirm user's SQL
EXECUTE_SQL = "execute_sql"                          # Ready to execute (replaces HAVE_SQL)
```

## Complete State Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                    │
│                 (Initial conversation state)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ASK_SQL_METHOD                                │
│   "How would you like to proceed?                               │
│    • 'create' - I'll generate SQL                               │
│    • 'provide' - You provide SQL"                               │
└─────────┬──────────────────────────────────────┬────────────────┘
          │                                      │
    User: "create"                         User: "provide"
          │                                      │
          ▼                                      ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│  NEED_NATURAL_LANGUAGE   │          │     NEED_USER_SQL        │
│ "Describe what you want" │          │  "Provide your SQL:"     │
└──────────┬───────────────┘          └──────────┬───────────────┘
           │                                     │
   User provides NL query              User provides SQL
   "get customers from USA"            "SELECT * FROM customers"
           │                                     │
     SQL Agent generates                   Store user SQL
           │                                     │
           ▼                                     ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│ CONFIRM_GENERATED_SQL    │          │   CONFIRM_USER_SQL       │
│ "I prepared: [SQL]       │          │ "You provided: [SQL]     │
│  Is this okay? (yes/no)" │          │  Is this correct?"       │
└──────────┬───────────────┘          └──────────┬───────────────┘
           │                                     │
    ┌──────┴──────┐                      ┌──────┴──────┐
    │             │                      │             │
User: "no"    User: "yes"            User: "no"   User: "yes"
    │             │                      │             │
    │      ┌──────┴──────────────────────┴──────┐      │
    │      │                                     │      │
    └──────┤          EXECUTE_SQL                ├──────┘
           │    "Executing the query..."         │
           │                                     │
           └──────────────┬──────────────────────┘
                          │
                Execute read_sql_job
                          │
                          ▼
           ┌─────────────────────────────────┐
           │       SHOW_RESULTS              │
           │  "✅ Query executed! Job ID: ..." │
           └──────────────┬──────────────────┘
                          │ (automatic)
                          ▼
           ┌─────────────────────────────────┐
           │   NEED_WRITE_OR_EMAIL           │
           │  "What next? write/email/done"  │
           └──────────────┬──────────────────┘
                          │
                   (write/email/done)
                          │
                          ▼
                       DONE
```

## Path Examples

### Path 1: Agent Generates SQL

```
1. START → ASK_SQL_METHOD
   Agent: "How would you like to proceed? create/provide"

2. User: "create"
   ASK_SQL_METHOD → NEED_NATURAL_LANGUAGE
   Agent: "Describe what you want"

3. User: "get all customers from USA"
   NEED_NATURAL_LANGUAGE → CONFIRM_GENERATED_SQL
   - SQL Agent generates: SELECT * FROM customers WHERE country = 'USA'
   Agent: "I prepared: [SQL]. Is this okay?"

4. User: "yes"
   CONFIRM_GENERATED_SQL → EXECUTE_SQL
   Agent: "Executing the query..."

5. EXECUTE_SQL → SHOW_RESULTS
   - Executes read_sql_job
   Agent: "✅ Query executed! Job ID: 123"
```

### Path 2: User Provides SQL

```
1. START → ASK_SQL_METHOD
   Agent: "How would you like to proceed? create/provide"

2. User: "provide"
   ASK_SQL_METHOD → NEED_USER_SQL
   Agent: "Please provide your SQL:"

3. User: "SELECT name, email FROM customers WHERE status = 'active'"
   NEED_USER_SQL → CONFIRM_USER_SQL
   Agent: "You provided: [SQL]. Is this correct?"

4. User: "yes"
   CONFIRM_USER_SQL → EXECUTE_SQL
   Agent: "Executing the query..."

5. EXECUTE_SQL → SHOW_RESULTS
   - Executes read_sql_job
   Agent: "✅ Query executed! Job ID: 456"
```

### Path 3: User Wants to Modify Generated SQL

```
1. START → ASK_SQL_METHOD → NEED_NATURAL_LANGUAGE
   User: "create"
   User: "get customers"

2. NEED_NATURAL_LANGUAGE → CONFIRM_GENERATED_SQL
   Agent generates: SELECT * FROM customers
   Agent: "I prepared: [SQL]. Is this okay?"

3. User: "no, I want only active customers"
   CONFIRM_GENERATED_SQL → NEED_NATURAL_LANGUAGE (loop back)
   Agent: "No problem! Please describe what you want differently:"

4. User: "get active customers only"
   NEED_NATURAL_LANGUAGE → CONFIRM_GENERATED_SQL
   Agent generates: SELECT * FROM customers WHERE status = 'active'
   Agent: "I prepared: [SQL]. Is this okay?"

5. User: "yes"
   CONFIRM_GENERATED_SQL → EXECUTE_SQL → SHOW_RESULTS
```

## Code Changes Summary

### 1. New Stages in `memory.py`

**Old (6 stages):**
- START
- NEED_QUERY
- HAVE_SQL
- SHOW_RESULTS
- NEED_WRITE_OR_EMAIL
- DONE

**New (10 stages):**
- START
- ASK_SQL_METHOD ✨
- NEED_NATURAL_LANGUAGE ✨
- NEED_USER_SQL ✨
- CONFIRM_GENERATED_SQL ✨
- CONFIRM_USER_SQL ✨
- EXECUTE_SQL (renamed from HAVE_SQL)
- SHOW_RESULTS
- NEED_WRITE_OR_EMAIL
- DONE

### 2. Router Logic Updates in `router.py`

#### **START → ASK_SQL_METHOD**
```python
if memory.stage == Stage.START:
    memory.stage = Stage.ASK_SQL_METHOD
    return memory, "How would you like to proceed?\n• 'create'\n• 'provide'"
```

#### **ASK_SQL_METHOD** (Branch Point)
```python
if memory.stage == Stage.ASK_SQL_METHOD:
    if "create" in user_utterance:
        memory.stage = Stage.NEED_NATURAL_LANGUAGE
    elif "provide" in user_utterance:
        memory.stage = Stage.NEED_USER_SQL
```

#### **NEED_NATURAL_LANGUAGE** (Generate SQL)
```python
if memory.stage == Stage.NEED_NATURAL_LANGUAGE:
    spec = call_sql_agent(user_utterance, ...)
    memory.last_sql = spec.sql
    memory.stage = Stage.CONFIRM_GENERATED_SQL
```

#### **NEED_USER_SQL** (Store User SQL)
```python
if memory.stage == Stage.NEED_USER_SQL:
    memory.last_sql = user_utterance.strip()
    # Basic SQL validation
    memory.stage = Stage.CONFIRM_USER_SQL
```

#### **CONFIRM_GENERATED_SQL** (Verify Generated)
```python
if memory.stage == Stage.CONFIRM_GENERATED_SQL:
    if "yes" in user_utterance:
        memory.stage = Stage.EXECUTE_SQL
    elif "no" in user_utterance:
        memory.stage = Stage.NEED_NATURAL_LANGUAGE  # Loop back
```

#### **CONFIRM_USER_SQL** (Verify User's)
```python
if memory.stage == Stage.CONFIRM_USER_SQL:
    if "yes" in user_utterance:
        memory.stage = Stage.EXECUTE_SQL
    elif "no" in user_utterance:
        memory.stage = Stage.NEED_USER_SQL  # Loop back
```

#### **EXECUTE_SQL** (formerly HAVE_SQL)
```python
if memory.stage == Stage.EXECUTE_SQL:
    # Same logic as before
    action = call_job_agent(memory, user_utterance, tool_name="read_sql")
    # Execute read_sql_job
    memory.stage = Stage.SHOW_RESULTS
```

## Key Features

### 1. **User Choice**
Users can now choose their preferred method at the start

### 2. **Modification Loop**
Both paths allow users to go back and modify:
- Generated SQL: "no" → back to NEED_NATURAL_LANGUAGE
- User SQL: "no" → back to NEED_USER_SQL

### 3. **SQL Validation**
Basic validation for user-provided SQL (checks for SQL keywords)

### 4. **Clear Confirmation**
Explicit confirmation step before execution for both paths

### 5. **Flexible Input**
Accepts variations:
- "create", "generate" → agent generates
- "provide", "write", "my own" → user provides

## Benefits

✅ **More Control**: Users choose how they interact
✅ **Expert-Friendly**: SQL experts can provide queries directly
✅ **Beginner-Friendly**: Non-SQL users can describe in natural language
✅ **Iterative**: Can refine SQL before execution
✅ **Transparent**: Always shows SQL before execution

## Testing Scenarios

### Test 1: Agent Generation
```
User: "create"
User: "get all active customers"
Agent shows SQL
User: "yes"
→ Executes
```

### Test 2: Direct Provision
```
User: "provide"
User: "SELECT * FROM orders WHERE status = 'pending'"
Agent confirms SQL
User: "yes"
→ Executes
```

### Test 3: Modification
```
User: "create"
User: "get customers"
Agent shows: SELECT * FROM customers
User: "no, only from USA"
Agent shows: SELECT * FROM customers WHERE country = 'USA'
User: "yes"
→ Executes
```

### Test 4: Invalid Choice
```
User: "maybe"
Agent: "Please choose: 'create' or 'provide'"
```
