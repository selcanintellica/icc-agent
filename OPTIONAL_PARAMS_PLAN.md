# Optional Parameters with Default Values - Implementation Plan

## Overview
Add support for optional parameters with default values that:
1. Are NOT asked during normal parameter gathering
2. Are shown in the final confirmation summary with default values
3. Can be edited at the confirmation stage
4. Trigger additional sub-flows when enabled (e.g., write_count needs connection/schema)

## Optional Parameters by Job Type

### ReadSQL
- `write_count`: boolean (default: `false`)
  - If `true`, requires:
    - `write_count_connection`: string (dropdown)
    - `write_count_schema`: string (dropdown)
    - `write_count_table`: string (user input)

### WriteData
- `write_count`: boolean (default: `false`)
  - If `true`, requires:
    - `write_count_connection`: string (dropdown)
    - `write_count_schema`: string (dropdown)
    - `write_count_table`: string (user input)

### SendEmail
- `cc`: string (default: `""` or `null`)

### CompareSQL
- No optional parameters currently

## Implementation Steps

### Step 1: Update Validators to Set Defaults

**File**: `src/ai/router/validators/parameter_validator.py`

For each job type validator, set defaults when all required params are present:

```python
# In validate_read_sql_params
if not params.get("write_count"):
    params["write_count"] = False

# In validate_write_data_params
if not params.get("write_count"):
    params["write_count"] = False

# In validate_send_email_params
if not params.get("cc"):
    params["cc"] = ""
```

### Step 2: Create ConfirmJobStrategy

**File**: `src/ai/router/stage_handlers/strategies/common/confirm_job.py` (NEW)

This strategy:
1. Shows formatted summary of all job parameters (including defaults with labels)
2. Handles confirmation: `yes` → Execute job
3. Handles rejection: `no` / `cancel` → Ask what to edit
4. Handles edit commands: `edit write_count`, `edit cc` → Edit flow
5. Supports all 4 job types (read_sql, write_data, send_email, compare_sql)

Key methods:
- `execute()` - Main entry point
- `_show_summary()` - Format and display job summary
- `_handle_edit()` - Route edit requests to specific handlers
- `_edit_write_count()` - Handle write_count editing (with sub-flow)
- `_edit_cc()` - Handle cc editing
- `_fetch_write_count_connection()` - Dropdown for write_count connection
- `_fetch_write_count_schema()` - Dropdown for write_count schema

### Step 3: Update EditTargetResolver

**File**: `src/ai/router/utils/edit_target_resolver.py`

Add mappings for optional parameters:
```python
# In EDIT_MAP or similar
"write count": {
    "clear_params": ["write_count", "write_count_connection", "write_count_schema", "write_count_table"],
    "transition_to": None,  # Stay in confirmation stage
    "message": "Do you want to enable row count writing? (yes/no)"
},
"cc": {
    "clear_params": ["cc"],
    "transition_to": None,
    "message": "Please provide CC email addresses (comma-separated):"
}
```

### Step 4: Add Confirmation Stages

**File**: `src/ai/router/context/stage_context.py`

Add to Stage enum (if not already present):
```python
CONFIRM_READ_SQL_JOB = "confirm_read_sql_job"
CONFIRM_WRITE_DATA_JOB = "confirm_write_data_job"
CONFIRM_SEND_EMAIL_JOB = "confirm_send_email_job"
CONFIRM_COMPARE_SQL_JOB = "confirm_compare_sql_job"
```

### Step 5: Update Execute Strategies

Modify job execution strategies to show confirmation first:

**Files**:
- `src/ai/router/stage_handlers/strategies/readsql/execute_sql.py`
- `src/ai/router/stage_handlers/writedata_handler.py`
- `src/ai/router/stage_handlers/sendemail_handler.py`

Change from direct execution to:
```python
# Before (direct execution)
return await self._execute_read_sql_job(memory, params)

# After (show confirmation first)
memory.gathered_params.update(params)
return self._create_result(memory, response="", next_stage=Stage.CONFIRM_READ_SQL_JOB)
```

### Step 6: Register ConfirmJobStrategy in Handlers

**Files**:
- `src/ai/router/stage_handlers/readsql_handler.py`
- `src/ai/router/stage_handlers/writedata_handler.py`
- `src/ai/router/stage_handlers/sendemail_handler.py`
- `src/ai/router/stage_handlers/comparesql_handler.py`

```python
from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy

# In handler registration
self.strategy_registry.register(
    Stage.CONFIRM_READ_SQL_JOB,
    ConfirmJobStrategy(job_type="read_sql", execution_callback=self._execute_job)
)
```

## User Flow Examples

### Example 1: ReadSQL with Default write_count

```
[User provides all required params via job agent]

Agent: 📋 ReadSQL Job Summary

**SQL Query:**
```sql
SELECT * FROM employees WHERE dept='IT'
```

**Execution Settings:**
- Connection: prod_db
- Execute Query: true
- Schema: results
- Table: employee_query
- Job Name: IT_Employees

**Optional Settings:**
- Write Count: false ✓ (default)

**Ready to create this job?**
- Type 'yes' or 'confirm' to proceed
- Type 'edit <parameter>' to modify (e.g., 'edit write count')
- Type 'cancel' to abort

User: yes

Agent: ✅ ReadSQL Job 'IT_Employees' created successfully!
```

### Example 2: Editing write_count at Confirmation

```
[At confirmation stage with default write_count=false]

User: edit write count

Agent: Do you want to write row counts? (yes/no)

User: yes

Agent: SELECT_CONNECTION_DROPDOWN:{"connections": [...], "param_name": "write_count_connection", ...}

User: __CONNECTION_SELECTED__:analytics_db

Agent: SELECT_SCHEMA_DROPDOWN:{"schemas": [...], "param_name": "write_count_schema", ...}

User: __SCHEMA_SELECTED__:stats

Agent: What table name should I use for row counts?

User: query_counts

Agent: 📋 ReadSQL Job Summary (UPDATED)

**SQL Query:**
```sql
SELECT * FROM employees WHERE dept='IT'
```

**Execution Settings:**
- Connection: prod_db
- Execute Query: true
- Schema: results
- Table: employee_query
- Job Name: IT_Employees

**Optional Settings:**
- Write Count: true ✓ (modified)
  - Write Count Connection: analytics_db
  - Write Count Schema: stats
  - Write Count Table: query_counts

**Ready to create this job?**
User: yes

Agent: ✅ ReadSQL Job 'IT_Employees' created successfully!
```

### Example 3: SendEmail with cc

```
[At confirmation stage]

Agent: 📋 SendEmail Job Summary

**Email Settings:**
- Recipients: john@example.com
- Subject: Q1 Sales Report
- Body: Please find the Q1 sales data attached.

**Data Source:**
- Job ID: 12345
- Table: sales_2024

**Optional Settings:**
- CC: (none) ✓ (default)

**Ready to send?**

User: edit cc

Agent: Please provide CC email addresses (comma-separated):

User: manager@example.com, cfo@example.com

Agent: 📋 SendEmail Job Summary (UPDATED)

**Email Settings:**
- Recipients: john@example.com
- Subject: Q1 Sales Report
- Body: Please find the Q1 sales data attached.
- CC: manager@example.com, cfo@example.com ✓ (modified)

**Ready to send?**

User: yes

Agent: ✅ Email sent successfully!
```

## Technical Details

### ConfirmJobStrategy State Management

The strategy needs to track sub-states for write_count editing:
- `CONFIRMING` - Showing summary, waiting for yes/edit/cancel
- `EDITING_WRITE_COUNT` - Asking yes/no for write_count
- `SELECTING_WC_CONNECTION` - Showing connection dropdown
- `SELECTING_WC_SCHEMA` - Showing schema dropdown
- `ENTERING_WC_TABLE` - Asking for table name
- `EDITING_CC` - Asking for CC emails

Use `memory.confirmation_state` or similar to track this.

### Dropdown Integration

Reuse existing connection/schema fetching:
```python
from src.ai.router.utils.connection_fetcher import ConnectionFetcher

# Fetch connections
result = await ConnectionFetcher.fetch_connections(memory)

# Fetch schemas
result = await ConnectionFetcher.fetch_schemas(connection_name, memory)
```

### Default Value Display

Format optional params with visual indicators:
```
- Write Count: false ✓ (default)
- Write Count: true ✓ (modified)
- CC: (none) ✓ (default)
- CC: manager@example.com ✓ (modified)
```

## Testing Checklist

- [ ] ReadSQL: Confirm with default write_count=false
- [ ] ReadSQL: Edit write_count to true, select connection/schema/table
- [ ] ReadSQL: Edit write_count back to false
- [ ] WriteData: Confirm with default write_count=false
- [ ] WriteData: Edit write_count to true
- [ ] SendEmail: Confirm with default cc=""
- [ ] SendEmail: Edit cc to add emails
- [ ] SendEmail: Edit cc to remove emails (set to "")
- [ ] All jobs: Cancel from confirmation → Job not created
- [ ] All jobs: Edit other params from confirmation (name, schema, etc.)
- [ ] All jobs: Back command from confirmation → Goes to previous stage

## Files to Create/Modify

### New Files
1. `src/ai/router/stage_handlers/strategies/common/confirm_job.py` (~400 lines)

### Modified Files
1. `src/ai/router/validators/parameter_validator.py` - Add defaults
2. `src/ai/router/utils/edit_target_resolver.py` - Add optional param mappings
3. `src/ai/router/context/stage_context.py` - Add confirmation stages (if needed)
4. `src/ai/router/stage_handlers/readsql_handler.py` - Register strategy, update MANAGED_STAGES
5. `src/ai/router/stage_handlers/writedata_handler.py` - Register strategy, transition to confirmation
6. `src/ai/router/stage_handlers/sendemail_handler.py` - Register strategy, transition to confirmation
7. `src/ai/router/stage_handlers/comparesql_handler.py` - Register strategy (for future optional params)
8. `src/ai/router/stage_handlers/strategies/readsql/execute_sql.py` - Transition to confirmation
9. `src/ai/router/stage_handlers/strategies/common/__init__.py` - Export ConfirmJobStrategy

## Benefits

1. **Better UX**: Users see all params before job creation
2. **Flexibility**: Can modify any parameter including optional ones
3. **Discoverability**: Users learn about optional features through confirmation
4. **Safety**: Final review prevents accidental job creation
5. **Consistency**: Same confirmation flow across all job types
