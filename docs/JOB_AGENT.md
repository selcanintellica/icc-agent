# Job Agent - Parameter Extraction and Job Creation

## Overview

The Job Agent is responsible for extracting parameters from user input to create database jobs (read, write, email). It uses the main language model (`qwen3:8b`) with moderate temperature (0.3) for flexible parameter extraction while maintaining accuracy.

## How It Works

### 1. Parameter Extraction

The Job Agent analyzes user responses to extract structured parameters needed for job creation. It operates during specific stages when job creation is required.

**Model Configuration:**
- Model: `qwen3:8b` (8B parameter general model)
- Temperature: `0.3` (moderate for flexible extraction with accuracy)
- Provider: Ollama (local)

**Why qwen3:8b?**
- Excellent instruction following
- Strong parameter extraction capabilities
- 8B size provides good balance of quality and speed
- Moderate temperature allows flexibility without randomness

### 2. Job Types

The Job Agent handles three types of jobs:

**Read Jobs (SQL Execution):**
- Executes SELECT queries
- Returns query results
- Requires: SQL query, connection ID

**Write Jobs (Data Insertion):**
- Writes query results to target database
- Requires: Source query results, target connection, schema, table, column mappings

**Email Jobs (Result Distribution):**
- Sends query results via email
- Requires: Query results, recipient email, subject, body

## Stage Integration

The Job Agent operates in multiple stages:

### EXECUTE_SQL Stage

**Purpose:** Create and execute read jobs

**Parameters to Extract:**
- Connection name → Convert to connection ID
- SQL query (from memory)
- Schema name (from memory)
- Tables (from memory)

**Example:**
```python
# User has confirmed SQL execution
# Memory contains: connection="ORACLE_10", sql="SELECT * FROM customers"

# Job Agent creates read job:
job_params = {
    "connection_id": get_connection_id("ORACLE_10"),  # Converts name to ID
    "query": "SELECT * FROM customers",
    "database_type": "oracle"
}
```

### NEED_WRITE_OR_EMAIL Stage

**Purpose:** Determine next action after showing results

**User Options:**
1. Write results to database
2. Send results via email  
3. Done (end conversation)

**Example Interaction:**
```
Agent: What would you like to do next? (write/email/done)
User: write to customers_backup table
```

**Job Agent extracts:**
- Action type: "write"
- Target table: "customers_backup"
- Target schema: (asks if not provided)
- Target connection: (asks if not provided)

### Write Job Creation

**Required Parameters:**
- Source results (from previous query)
- Target connection ID
- Target schema
- Target table
- Column mappings (optional, auto-mapped if not specified)

**Example:**
```python
write_params = {
    "source_data": memory.results,  # Previous query results
    "target_connection_id": get_connection_id("ORACLE_11"),
    "target_schema": "BACKUP",
    "target_table": "customers_backup",
    "column_mappings": {
        "customer_id": "backup_customer_id",
        "first_name": "backup_first_name"
    }
}
```

### Email Job Creation

**Required Parameters:**
- Results to send (from previous query)
- Recipient email address(es)
- Email subject
- Email body (optional, auto-generated if not specified)

**Example:**
```python
email_params = {
    "results": memory.results,
    "recipients": ["manager@company.com"],
    "subject": "Customer Query Results - USA Customers",
    "body": "Attached are the requested customer records.",
    "format": "csv"  # or "excel", "json"
}
```

## Implementation

### Location
`src/ai/router/job_agent.py`

### Key Functions

**`extract_write_parameters(user_input: str, context: dict) -> dict`**

Extracts parameters for write job creation.

**Parameters:**
- `user_input`: User's natural language response
- `context`: Current conversation context (memory state)

**Returns:**
- Dictionary with extracted parameters

**Example:**
```python
user_input = "write to backup schema customers_archive table"
context = {
    "connection": "ORACLE_10",
    "results": [...],  # Previous query results
}

params = extract_write_parameters(user_input, context)
# Returns:
# {
#     "target_connection": "ORACLE_10",
#     "target_schema": "BACKUP",
#     "target_table": "customers_archive",
#     "column_mappings": None  # Auto-map columns
# }
```

**`extract_email_parameters(user_input: str, context: dict) -> dict`**

Extracts parameters for email job creation.

**Parameters:**
- `user_input`: User's natural language response
- `context`: Current conversation context

**Returns:**
- Dictionary with extracted email parameters

**Example:**
```python
user_input = "send results to john@company.com with subject Customer Report"
context = {
    "results": [...],  # Previous query results
}

params = extract_email_parameters(user_input, context)
# Returns:
# {
#     "recipients": ["john@company.com"],
#     "subject": "Customer Report",
#     "body": None,  # Auto-generate
#     "format": "csv"
# }
```

**`validate_parameters(params: dict, job_type: str) -> tuple[bool, str]`**

Validates extracted parameters before job creation.

**Parameters:**
- `params`: Extracted parameters dictionary
- `job_type`: Type of job ("read", "write", "email")

**Returns:**
- Tuple of (is_valid, error_message)

## Prompt Engineering

### Write Job Extraction Prompt

```
You are a parameter extraction expert. Extract the following from the user's request:
- target_schema: The database schema to write to
- target_table: The table name to write to
- target_connection: The connection name (if mentioned, otherwise use current)

Current context:
- Connection: {connection}
- Schema: {schema}

User request: {user_input}

Return only a JSON object with the extracted parameters.
```

### Email Job Extraction Prompt

```
You are a parameter extraction expert. Extract email parameters from the user's request:
- recipients: List of email addresses
- subject: Email subject line
- body: Email body (if specified)
- format: Attachment format (csv, excel, json)

User request: {user_input}

Return only a JSON object with the extracted parameters.
```

## Error Handling

### Missing Required Parameters

If the Job Agent cannot extract required parameters, it prompts the user:

```python
if not params.get("target_table"):
    return {
        "status": "missing_param",
        "message": "Which table should I write the results to?",
        "missing": "target_table"
    }
```

### Invalid Parameter Values

```python
if params.get("recipients") and not validate_email(params["recipients"]):
    return {
        "status": "invalid_param",
        "message": "The email address format is invalid. Please provide a valid email.",
        "invalid": "recipients"
    }
```

### Fallback Behavior

If extraction fails completely:
1. Ask user to rephrase with more specific information
2. Offer structured input format
3. Provide example of expected input

**Example:**
```
Agent: I couldn't extract the table name from your request. 
       Please specify: write to [schema].[table]
       Example: write to BACKUP.customers_archive
```

## Connection ID Conversion

The Job Agent works with connection names (user-friendly) but APIs require connection IDs.

**Conversion Process:**

```python
from src.utils.connections import get_connection_id

# User provides: "ORACLE_10"
connection_name = "ORACLE_10"

# Convert to ID for API
connection_id = get_connection_id(connection_name)
# Returns: 1

# Use in job creation
job_params = {
    "connection_id": connection_id,  # API expects integer ID
    ...
}
```

**Available Connections:**

18 connections defined in `src/utils/connections.py`:
- ORACLE_10 (ID: 1)
- ORACLE_11 (ID: 2)
- oracle_18 (ID: 3)
- POSTGRE_11 (ID: 4)
- POSTGRE_14 (ID: 5)
- MSSQL (ID: 6)
- mongo (ID: 7)
- oracle_pdb (ID: 8)
- ORACLE_19_NEW (ID: 9)
- postgre_15 (ID: 10)
- postgre_12 (ID: 11)
- postgre_13 (ID: 12)
- teradata (ID: 13)
- hive (ID: 14)
- snowflake (ID: 15)
- oracle_pdb2 (ID: 16)
- sqlserver (ID: 17)
- ibmdb2 (ID: 18)

## Tool Integration

The Job Agent works with tools from `src/ai/toolkits/icc_toolkit.py`:

### Read SQL Tool

```python
@tool
def read_sql_job(connection_id: int, query: str, database_type: str) -> str:
    """Execute a SELECT query and return results"""
    # Creates read job via API
    # Returns job_id for status tracking
```

### Write Data Tool

```python
@tool
def write_data_job(
    connection_id: int,
    schema: str,
    table: str,
    data: list,
    column_mappings: dict = None
) -> str:
    """Write data to target database table"""
    # Creates write job via API
```

### Send Email Tool

```python
@tool
def send_email_job(
    recipients: list,
    subject: str,
    body: str,
    attachment_data: list,
    format: str = "csv"
) -> str:
    """Send query results via email"""
    # Creates email job via API
```

## Configuration

### Environment Variables

```env
# Model for job agent
MODEL_NAME=qwen3:8b

# Ollama endpoint
OLLAMA_BASE_URL=http://localhost:11434

# API endpoints
BASE_URL=http://localhost:8000/api
```

### Model Parameters

In `job_agent.py`:
```python
llm = ChatOllama(
    model="qwen3:8b",
    temperature=0.3,  # Moderate temp for flexible extraction
    base_url="http://localhost:11434"
)
```

## Best Practices

**For Parameter Extraction:**
1. Provide clear context in prompts (current connection, schema, etc.)
2. Use moderate temperature (0.3) for balance of flexibility and accuracy
3. Validate extracted parameters before job creation
4. Prompt for missing required parameters rather than guessing
5. Provide examples when user input is unclear

**For Connection Handling:**
1. Always convert connection names to IDs using `get_connection_id()`
2. Validate connection names exist before conversion
3. Handle connection conversion errors gracefully
4. Provide clear error messages if connection is invalid

**For Job Creation:**
1. Validate all parameters before API call
2. Store job IDs in memory for tracking
3. Handle API errors gracefully with user-friendly messages
4. Allow user to retry with corrected parameters

## Debugging

**Enable Job Agent Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Test Parameter Extraction:**
```python
from src.ai.router.job_agent import extract_write_parameters

params = extract_write_parameters(
    user_input="write to backup_schema customers_archive table",
    context={"connection": "ORACLE_10", "schema": "SALES"}
)
print(params)
```

**Test Connection ID Conversion:**
```python
from src.utils.connections import get_connection_id, get_connection_info

connection_id = get_connection_id("ORACLE_10")
print(f"ID: {connection_id}")

connection_info = get_connection_info("ORACLE_10")
print(f"Info: {connection_info}")
```

**Test Job Creation:**
```python
from src.ai.toolkits.icc_toolkit import read_sql_job

job_id = read_sql_job(
    connection_id=1,  # ORACLE_10
    query="SELECT * FROM customers LIMIT 10",
    database_type="oracle"
)
print(f"Job ID: {job_id}")
```

## Related Documentation

- [Router Architecture](ROUTER_ARCHITECTURE.md) - Complete stage system
- [Connection ID Implementation](CONNECTION_ID_IMPLEMENTATION.md) - Connection mapping
- [SQL Agent](SQL_AGENT.md) - SQL generation process
