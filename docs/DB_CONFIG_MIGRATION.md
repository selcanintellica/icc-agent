# Database Configuration System - Migration Guide

## Overview

The system has been migrated from a **file-based schema documentation** approach to a **JSON configuration + API** approach.

### ✅ What Changed

#### **Before (File-based)**
- Scanned `schema_docs/` folder for connections, schemas, and tables
- Read `.txt` files for table definitions
- `schema_loader.py` handled both discovery and definition loading

#### **After (JSON + API)**
- `db_config.json` defines the hierarchy of connections, schemas, and tables
- API calls fetch table definitions dynamically
- Separate concerns: `config_loader.py` for UI, `table_api_client.py` for definitions

---

## New Architecture

### 📁 Files Created

1. **`db_config.json`** - Database hierarchy configuration
2. **`src/utils/config_loader.py`** - Reads JSON config for UI dropdowns
3. **`src/utils/table_api_client.py`** - Fetches table definitions from API

### 🔄 Files Modified

1. **`app.py`** - Now uses `config_loader` instead of `schema_loader`
2. **`src/ai/router/sql_agent.py`** - Now uses API client to fetch table definitions

---

## Configuration File Format

### `db_config.json` Structure

```json
{
  "connections": [
    {
      "name": "oracle_10",
      "label": "Oracle Production (10)",
      "schemas": [
        {
          "name": "SALES",
          "label": "SALES",
          "tables": [
            "customers",
            "orders",
            "order_items",
            "products"
          ]
        },
        {
          "name": "HR",
          "label": "HR",
          "tables": [
            "departments",
            "employees"
          ]
        }
      ]
    }
  ]
}
```

### Adding New Connections/Schemas/Tables

Simply edit `db_config.json`:

```json
{
  "connections": [
    {
      "name": "my_new_db",
      "label": "My New Database",
      "schemas": [
        {
          "name": "MY_SCHEMA",
          "label": "My Schema",
          "tables": ["table1", "table2", "table3"]
        }
      ]
    }
  ]
}
```

No need to create folders or files - just update the JSON!

---

## API Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Table definitions API base URL
TABLE_API_BASE_URL=http://localhost:8000/api/tables

# API timeout in seconds
TABLE_API_TIMEOUT=10

# Use mock data instead of real API calls (true/false)
TABLE_API_MOCK=true
```

### Mock Mode

For development and testing before the API is ready, you can enable **mock mode**:

1. Set `TABLE_API_MOCK=true` in your `.env` file
2. Mock data is provided in `src/utils/mock_table_data.py`
3. The system will return predefined table definitions without making API calls

**Mock Data Available:**
- `ORACLE_10.SALES`: customers, orders, order_items, products
- `ORACLE_10.HR`: employees, departments
- `POSTGRE_11.PUBLIC`: users

When the real API is ready, simply set `TABLE_API_MOCK=false` to switch to live API calls.

### API Endpoints Expected

The system expects the following API endpoints:

#### 1. **Single Table Definition**
```
GET /api/tables/{connection}/{schema}/{table}

Response:
{
  "connection": "oracle_10",
  "schema": "SALES",
  "table": "customers",
  "definition": "Table: customers\nSchema: SALES\n..."
}
```

#### 2. **Batch Table Definitions (Optional but recommended)**
```
POST /api/tables/batch

Request:
{
  "connection": "oracle_10",
  "schema": "SALES",
  "tables": ["customers", "orders"]
}

Response:
{
  "definitions": [
    {
      "table": "customers",
      "definition": "Table: customers\n..."
    },
    {
      "table": "orders",
      "definition": "Table: orders\n..."
    }
  ]
}
```

#### 3. **Health Check (Optional)**
```
GET /api/health

Response: 200 OK
```

---

## How It Works

### 1. UI Dropdowns (app.py)

```python
from src.utils.config_loader import get_config_loader

config_loader = get_config_loader()

# Populate dropdowns
connections = config_loader.get_available_connections()
schemas = config_loader.get_schemas_for_connection("oracle_10")
tables = config_loader.get_tables_for_schema("oracle_10", "SALES")
```

The dropdowns are populated from `db_config.json` - **no API calls needed**.

### 2. SQL Generation (sql_agent.py)

```python
from src.utils.table_api_client import fetch_table_definitions

# When user asks a question, fetch table definitions from API
schema_definitions = fetch_table_definitions(
    connection="oracle_10",
    schema="SALES", 
    tables=["customers", "orders"]
)

# Use definitions in LLM prompt
```

The SQL agent makes **API calls** to fetch table definitions **only when generating SQL**.

### 3. Memory System

The memory still works exactly the same:
- Selected connection, schema, and tables are stored in memory
- Router passes them to SQL agent
- SQL agent uses them to make API calls

---

## Benefits of New Approach

### ✅ Advantages

1. **Centralized Configuration**: Single JSON file instead of complex folder structure
2. **API-Driven**: Table definitions come from live API (can be database-generated)
3. **Hot Reload**: API changes reflected immediately without file updates
4. **Separation of Concerns**: UI config separate from data fetching
5. **Scalability**: Easier to add new databases without creating files
6. **Version Control**: JSON config is easier to diff and track

### 🔄 Backward Compatibility

The old `schema_loader.py` still exists if needed, but:
- `app.py` now uses `config_loader`
- `sql_agent.py` now uses `table_api_client`
- `schema_docs/` folder is no longer used

---

## Testing the New System

### 1. Update `db_config.json`

Ensure your connections, schemas, and tables are listed correctly.

### 2. Set Up API Endpoint

Make sure your API is running and accessible at the configured base URL.

### 3. Test API Manually

```bash
# Test single table
curl http://localhost:8000/api/tables/oracle_10/SALES/customers

# Test batch endpoint
curl -X POST http://localhost:8000/api/tables/batch \
  -H "Content-Type: application/json" \
  -d '{"connection":"oracle_10","schema":"SALES","tables":["customers","orders"]}'
```

### 4. Run the Application

```bash
uv run app.py
```

### 5. Verify Behavior

1. ✅ Dropdowns populate from `db_config.json`
2. ✅ Selecting connection/schema/tables works
3. ✅ SQL agent fetches definitions from API when generating queries
4. ✅ Check logs for API calls: `🌐 Fetching table definitions from API...`

---

## Troubleshooting

### Issue: Dropdowns not populating

**Cause**: `db_config.json` not found or invalid JSON

**Solution**: 
- Verify `db_config.json` exists in project root
- Validate JSON syntax: `python -m json.tool db_config.json`

### Issue: SQL generation fails with empty schema

**Cause**: API not reachable or returning errors

**Solution**:
- Check `TABLE_API_BASE_URL` in `.env`
- Test API manually with curl
- Check logs for API error messages

### Issue: API timeout

**Cause**: API is slow or unreachable

**Solution**:
- Increase `TABLE_API_TIMEOUT` in `.env`
- Check network connectivity
- Verify API server is running

---

## Migration Checklist

- [x] ✅ Created `db_config.json` with all connections/schemas/tables
- [x] ✅ Created `src/utils/config_loader.py` for JSON reading
- [x] ✅ Created `src/utils/table_api_client.py` for API calls
- [x] ✅ Updated `app.py` to use `config_loader`
- [x] ✅ Updated `sql_agent.py` to use `table_api_client`
- [ ] ⏳ Set up table definitions API endpoint
- [ ] ⏳ Configure environment variables
- [ ] ⏳ Test end-to-end functionality

---

## Next Steps

1. **Implement the API**: Create the API endpoint that serves table definitions
2. **Configure `.env`**: Set `TABLE_API_BASE_URL` to your API location
3. **Test**: Run the application and verify everything works
4. **Optional**: Remove `schema_docs/` folder if no longer needed
5. **Optional**: Add caching to `table_api_client.py` for performance

---

## API Implementation Example

Here's a simple Flask example for the table definitions API:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/api/tables/<connection>/<schema>/<table>')
def get_table(connection, schema, table):
    # Fetch from database or cache
    definition = fetch_from_database(connection, schema, table)
    
    return jsonify({
        "connection": connection,
        "schema": schema,
        "table": table,
        "definition": definition
    })

@app.route('/api/tables/batch', methods=['POST'])
def get_tables_batch():
    data = request.json
    connection = data['connection']
    schema = data['schema']
    tables = data['tables']
    
    definitions = []
    for table in tables:
        definition = fetch_from_database(connection, schema, table)
        definitions.append({
            "table": table,
            "definition": definition
        })
    
    return jsonify({"definitions": definitions})

if __name__ == '__main__':
    app.run(port=8000)
```

---

## Questions?

Check the code in:
- `src/utils/config_loader.py` - For JSON configuration loading
- `src/utils/table_api_client.py` - For API client implementation
- `app.py` - For UI integration
- `src/ai/router/sql_agent.py` - For SQL agent integration
