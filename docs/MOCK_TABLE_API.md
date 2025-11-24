# Mock Table API Implementation

## Overview

Added mock data support for the table definitions API, allowing development and testing before the real API is ready.

## Changes Made

### 1. ✨ **New File: `src/utils/mock_table_data.py`**

Contains mock table definitions for testing:

```python
MOCK_TABLE_DEFINITIONS = {
    "ORACLE_10": {
        "SALES": {
            "customers": "Table: customers\n...",
            "orders": "Table: orders\n...",
            "order_items": "Table: order_items\n...",
            "products": "Table: products\n..."
        },
        "HR": {
            "employees": "Table: employees\n...",
            "departments": "Table: departments\n..."
        }
    },
    "POSTGRE_11": {
        "PUBLIC": {
            "users": "Table: users\n..."
        }
    }
}
```

**Helper Function:**
- `get_mock_table_definition(connection, schema, table)` - Returns mock definition or None

### 2. 🔧 **Updated: `.env`**

Added new environment variables:

```bash
# Table Definitions API Configuration
TABLE_API_BASE_URL=http://localhost:8000/api/tables
TABLE_API_TIMEOUT=10
TABLE_API_MOCK=true    # ← NEW: Enable/disable mock mode
```

### 3. 🔄 **Updated: `src/utils/table_api_client.py`**

Added mock mode support:

#### **Initialization:**
```python
def __init__(self, base_url=None, use_mock=None):
    # Check TABLE_API_MOCK environment variable
    if use_mock is None:
        mock_env = os.getenv("TABLE_API_MOCK", "false").lower()
        self.use_mock = mock_env in ("true", "1", "yes")
    
    if self.use_mock:
        logger.info("🎭 TableAPIClient initialized in MOCK mode")
```

#### **fetch_table_definition:**
```python
def fetch_table_definition(self, connection, schema, table):
    # Use mock data if enabled
    if self.use_mock:
        logger.info(f"🎭 Using mock data for: {connection}.{schema}.{table}")
        return get_mock_table_definition(connection, schema, table)
    
    # Otherwise, make real API call
    response = requests.get(url, timeout=self.timeout)
    ...
```

#### **fetch_multiple_tables_batch:**
```python
def fetch_multiple_tables_batch(self, connection, schema, tables):
    # In mock mode, use individual calls
    if self.use_mock:
        return self.fetch_multiple_tables(connection, schema, tables)
    
    # Otherwise, try batch API endpoint
    ...
```

## Usage

### Enable Mock Mode (Default for Development)

In `.env`:
```bash
TABLE_API_MOCK=true
```

The system will:
- ✅ Log: `🎭 TableAPIClient initialized in MOCK mode`
- ✅ Return predefined table definitions from `mock_table_data.py`
- ✅ No actual HTTP requests made
- ✅ Instant response (no network latency)

### Disable Mock Mode (For Production)

In `.env`:
```bash
TABLE_API_MOCK=false
```

The system will:
- ✅ Log: `🌐 TableAPIClient initialized with base URL: ...`
- ✅ Make real API calls to `TABLE_API_BASE_URL`
- ✅ Handle network errors and timeouts

## Mock Data Available

Currently includes:

### ORACLE_10.SALES
- **customers**: 10 columns (customer_id, first_name, last_name, email, phone, etc.)
- **orders**: 8 columns (order_id, customer_id, order_date, status, total_amount, etc.)
- **order_items**: 7 columns (order_item_id, order_id, product_id, quantity, etc.)
- **products**: 9 columns (product_id, product_name, category, price, stock_quantity, etc.)

### ORACLE_10.HR
- **employees**: 11 columns (employee_id, name, email, hire_date, department_id, etc.)
- **departments**: 5 columns (department_id, department_name, manager_id, location, budget)

### POSTGRE_11.PUBLIC
- **users**: 7 columns (user_id, username, email, password_hash, created_at, etc.)

## Adding More Mock Data

To add mock data for a new table:

1. Open `src/utils/mock_table_data.py`
2. Add to the `MOCK_TABLE_DEFINITIONS` dict:

```python
MOCK_TABLE_DEFINITIONS = {
    "YOUR_CONNECTION": {
        "YOUR_SCHEMA": {
            "your_table": """Table: your_table
Schema: YOUR_SCHEMA
Connection: YOUR_CONNECTION

Description:
Your table description here.

Columns:
- column1 (TYPE, constraints): Description
- column2 (TYPE): Description

...
"""
        }
    }
}
```

## Testing

### Test Mock Mode:

```bash
# In .env
TABLE_API_MOCK=true
```

```bash
# Run app
uv run app.py
```

1. Select `ORACLE_10` connection
2. Select `SALES` schema
3. Select `customers`, `orders` tables
4. Ask: "Show all customers"
5. Check logs: Should see `🎭 Using mock data for: ORACLE_10.SALES.customers`

### Test Real API Mode:

```bash
# In .env
TABLE_API_MOCK=false
TABLE_API_BASE_URL=http://your-api-endpoint/api/tables
```

```bash
# Run app
uv run app.py
```

1. Same steps as above
2. Check logs: Should see `🔍 Fetching table definition from API: ...`
3. System will make real HTTP requests

## Benefits

✅ **No API Required**: Can develop and test without waiting for API
✅ **Fast Testing**: Instant responses, no network delays
✅ **Offline Development**: Works without internet/API connection
✅ **Easy Toggle**: Single environment variable to switch modes
✅ **Realistic Data**: Mock definitions match expected API format
✅ **Production Ready**: Simple switch to real API when ready

## Migration Path

1. **Current (Development)**: `TABLE_API_MOCK=true` - Use mock data
2. **Testing**: Switch between mock/real to test API integration
3. **Production**: `TABLE_API_MOCK=false` - Use real API

No code changes needed - just flip the environment variable!
