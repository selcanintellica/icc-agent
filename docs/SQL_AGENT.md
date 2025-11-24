# SQL Agent - Natural Language to SQL Conversion

## Overview

The SQL Agent is responsible for converting natural language descriptions into executable SQL queries. It uses a specialized code-focused language model (`qwen2.5-coder:7b`) with low temperature (0.1) for precise, deterministic SQL generation.

## How It Works

### 1. Table Definition Loading

When a user describes what they want to query, the SQL Agent first fetches the definitions of the selected tables from the Table API (or mock data in development mode).

**Table API Client** (`src/utils/table_api_client.py`):
```python
# Fetches table definitions from API or mock data
table_def = fetch_table_definition(connection, schema, table)
```

**Mock Mode Support:**
- Set `TABLE_API_MOCK=true` in `.env` for development
- Uses `src/utils/mock_table_data.py` for predefined table definitions
- No API calls needed during development

**Table Definition Format:**
```
Table: SALES.customers
Columns:
  - customer_id (NUMBER, Primary Key)
  - first_name (VARCHAR2)
  - last_name (VARCHAR2)
  - country (VARCHAR2)
  - email (VARCHAR2)
```

### 2. SQL Generation

The SQL Agent receives:
- User's natural language description
- Table definitions for selected tables
- Database connection type (Oracle, PostgreSQL, MSSQL, MongoDB)

**Model Configuration:**
- Model: `qwen2.5-coder:7b` (7B parameter code model)
- Temperature: `0.1` (very low for deterministic, precise SQL)
- Provider: Ollama (local)

**Why qwen2.5-coder:7b?**
- Specialized for code generation
- Excellent SQL understanding
- 7B size balances quality with speed
- Low temperature ensures consistent output

### 3. Context-Aware Generation

The agent constructs a prompt that includes:

```
You are a SQL expert. Generate a SQL query based on the user's request.

Available tables and their structures:
{table_definitions}

User request: {natural_language_query}

Generate only the SQL query, no explanations.
```

The LLM generates SQL that:
- Uses correct table/column names from definitions
- Applies appropriate syntax for the database type
- Includes necessary JOINs when multiple tables are involved
- Adds WHERE clauses based on user's filters
- Uses proper SQL conventions (uppercase keywords, etc.)

## Stage Integration

The SQL Agent is invoked during the **NEED_NATURAL_LANGUAGE** stage:

```
ASK_SQL_METHOD → NEED_NATURAL_LANGUAGE → [SQL Agent] → CONFIRM_GENERATED_SQL
```

**Stage Flow:**
1. User chooses "generate" when asked about SQL method
2. Router transitions to NEED_NATURAL_LANGUAGE stage
3. User provides natural language description
4. SQL Agent fetches table definitions for selected tables
5. SQL Agent generates SQL query
6. Router stores SQL in memory and transitions to CONFIRM_GENERATED_SQL
7. User reviews and confirms/rejects the generated SQL

## Implementation

### Location
`src/ai/router/sql_agent.py`

### Key Functions

**`generate_sql(natural_language: str, tables: list, connection: str, schema: str) -> str`**

Generates SQL from natural language description.

**Parameters:**
- `natural_language`: User's query description
- `tables`: List of table names to query
- `connection`: Database connection name (e.g., "ORACLE_10")
- `schema`: Schema name (e.g., "SALES")

**Returns:**
- Generated SQL query as string

**Process:**
1. Fetch table definitions using `table_api_client.fetch_multiple_tables()`
2. Construct prompt with table schemas and user request
3. Call Ollama with `qwen2.5-coder:7b` model (temp=0.1)
4. Extract and clean SQL from LLM response
5. Return SQL query

### Example

**Input:**
```python
natural_language = "Get all customers from USA who ordered in 2024"
tables = ["customers", "orders"]
connection = "ORACLE_10"
schema = "SALES"
```

**Table Definitions Fetched:**
```
Table: SALES.customers
  - customer_id (NUMBER, PK)
  - first_name (VARCHAR2)
  - last_name (VARCHAR2)
  - country (VARCHAR2)

Table: SALES.orders
  - order_id (NUMBER, PK)
  - customer_id (NUMBER, FK)
  - order_date (DATE)
  - total_amount (NUMBER)
```

**Generated SQL:**
```sql
SELECT c.customer_id, c.first_name, c.last_name, o.order_id, o.order_date, o.total_amount
FROM SALES.customers c
JOIN SALES.orders o ON c.customer_id = o.customer_id
WHERE c.country = 'USA'
  AND EXTRACT(YEAR FROM o.order_date) = 2024
ORDER BY o.order_date DESC
```

## Error Handling

**Missing Table Definitions:**
- If API returns no data (and not in mock mode), agent fails gracefully
- Router can transition back to NEED_NATURAL_LANGUAGE for retry

**Invalid SQL Generation:**
- Low temperature (0.1) minimizes invalid SQL generation
- User reviews SQL in CONFIRM_GENERATED_SQL stage before execution
- If user rejects, can loop back to regenerate

**API Failures:**
- In mock mode, always uses local data (no failures)
- In production mode, API errors bubble up and router handles retry logic

## Mock Mode

### Configuration

Set in `.env`:
```env
TABLE_API_MOCK=true
TABLE_API_BASE_URL=http://localhost:8000/api/tables
TABLE_API_TIMEOUT=30
```

### Available Mock Tables

Defined in `src/utils/mock_table_data.py`:

**ORACLE_10.SALES:**
- `customers`: customer_id, first_name, last_name, email, country
- `orders`: order_id, customer_id, order_date, total_amount, status
- `order_items`: item_id, order_id, product_id, quantity, price
- `products`: product_id, product_name, category, price, stock_quantity

**ORACLE_10.HR:**
- `employees`: employee_id, first_name, last_name, email, hire_date, job_id, salary, department_id
- `departments`: department_id, department_name, manager_id, location_id

**POSTGRE_11.PUBLIC:**
- `users`: user_id, username, email, created_at, is_active

### Adding Mock Tables

Edit `src/utils/mock_table_data.py`:

```python
MOCK_TABLE_DEFINITIONS = {
    "ORACLE_10.SALES.your_table": """
Table: SALES.your_table
Columns:
  - column1 (TYPE)
  - column2 (TYPE)
""",
}
```

## Configuration

### Environment Variables

```env
# Model for SQL generation
SQL_MODEL_NAME=qwen2.5-coder:7b

# Ollama endpoint
OLLAMA_BASE_URL=http://localhost:11434

# Table API settings
TABLE_API_BASE_URL=http://localhost:8000/api/tables
TABLE_API_TIMEOUT=30
TABLE_API_MOCK=true  # Set to false for production API
```

### Model Parameters

In `sql_agent.py`:
```python
llm = ChatOllama(
    model="qwen2.5-coder:7b",
    temperature=0.1,  # Low temp for deterministic SQL
    base_url="http://localhost:11434"
)
```

## Best Practices

**For SQL Generation:**
1. Always fetch table definitions first (provides column names and types)
2. Use low temperature (0.1) for consistent, valid SQL
3. Include database type context in prompt for syntax differences
4. Validate table/column names against fetched definitions

**For Table Definitions:**
1. Use mock mode during development (faster, no API dependency)
2. Keep mock data synchronized with production schemas
3. Include all columns used in common queries
4. Specify data types for LLM context

**For Error Handling:**
1. Allow user to review generated SQL (CONFIRM_GENERATED_SQL stage)
2. Provide clear error messages if generation fails
3. Support regeneration if user rejects SQL
4. Log failed generations for debugging

## Debugging

**Enable SQL Agent Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check Generated SQL:**
- SQL is stored in `memory.sql` after generation
- User sees SQL in CONFIRM_GENERATED_SQL stage
- Review prompt construction in logs

**Test Mock Mode:**
```python
from src.utils.table_api_client import fetch_table_definition

# Should use mock data
table_def = fetch_table_definition("ORACLE_10", "SALES", "customers")
print(table_def)
```

**Test SQL Generation:**
```python
from src.ai.router.sql_agent import generate_sql

sql = generate_sql(
    natural_language="Get customers from USA",
    tables=["customers"],
    connection="ORACLE_10",
    schema="SALES"
)
print(sql)
```

## Related Documentation

- [Router Architecture](ROUTER_ARCHITECTURE.md) - Complete stage system
- [Mock Table API](MOCK_TABLE_API.md) - Mock mode details
- [Connection ID Implementation](CONNECTION_ID_IMPLEMENTATION.md) - API integration
