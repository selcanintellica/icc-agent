# Fetch Connections - Usage Guide

## Overview

The `fetch_connections.py` module fetches database connection information from the ICC API and converts it to the format used by the application.

## Setup

### 1. Set Environment Variable

Add the connection list API endpoint to your environment:

```bash
# PowerShell
$env:ICC_CONNECTION_LIST_URL = "https://172.16.22.13:8084/connection/list"

# Or add to .env file
ICC_CONNECTION_LIST_URL=https://172.16.22.13:8084/connection/list
```

### 2. Ensure VPN Connection

Make sure you're connected to the VPN if the API requires it.

## Usage Methods

### Method 1: Standalone Testing (Command Line)

Test the connection fetching independently:

```powershell
# Run the script directly
uv run python src/utils/fetch_connections.py
```

This will:
- Fetch connections from the API
- Convert them to the internal format
- Save them to `data/connections_from_icc_TIMESTAMP.json`
- Print the list of connection names

**Output Example:**
```
[OK] Saved 17 connections to C:\Users\...\data\connections_from_icc_20251126_160530.json

✅ Success! Wrote 17 connections to connections_from_icc.json

Connection names:
  - Cassandra (Cassandra)
  - HANA (SAP HANA)
  - MSSQL (SQL Server)
  - ORACLE_10 (Oracle)
  - ORACLE_11 (Oracle)
  - POSTGRE_11 (PostgreSQL)
  ...
```

### Method 2: In Your Application Code

#### Option A: Direct Function Call

```python
from src.utils.fetch_connections import fetch_and_map_connections

# Fetch and convert connections
connections = fetch_and_map_connections()

# Result format:
# {
#     "ORACLE_10": {
#         "id": "4976629955435844",
#         "db_type": "Oracle",
#         "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
#         "user": "icc_test"
#     },
#     ...
# }
```

#### Option B: With Authentication

```python
from src.utils.fetch_connections import fetch_and_map_connections

# If API requires authentication
connections = fetch_and_map_connections(
    base_url="https://172.16.22.13:8084/connection/list",
    auth=("username", "password")
)
```

#### Option C: Populate Memory Directly

```python
from src.ai.router.memory import Memory
from src.utils.fetch_connections import populate_memory_connections

# Create memory instance
memory = Memory()

# Fetch and populate connections
success = populate_memory_connections(memory)

if success:
    print(f"Loaded {len(memory.connections)} connections")
    # Now memory.get_connection_id("ORACLE_10") will work
else:
    print("Failed to load connections, will use fallback")
```

### Method 3: In app.py (Recommended)

Integrate into your main application:

```python
# In app.py, before starting the chat

from src.ai.router.memory import Memory
from src.utils.fetch_connections import populate_memory_connections
import logging

logger = logging.getLogger(__name__)

# Initialize memory
memory = Memory()

# Try to load dynamic connections
try:
    if populate_memory_connections(memory):
        logger.info(f"✅ Loaded {len(memory.connections)} connections from API")
    else:
        logger.warning("⚠️ Failed to load connections, will use static fallback")
except Exception as e:
    logger.error(f"❌ Error loading connections: {e}")
    logger.info("Will use static connections.py as fallback")

# Continue with your application...
```

## API Response Format

The API should return JSON in this format:

```json
{
  "object": [
    {
      "id": "4976629955435844",
      "props": {
        "name": "ORACLE_10"
      },
      "databaseUrl": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
      "databaseUser": "icc_test",
      "connectionType": "jdbc"
    },
    {
      "id": "955225233921727",
      "props": {
        "name": "POSTGRE_11"
      },
      "databaseUrl": "jdbc:postgresql://172.16.44.11:5432/postgres",
      "databaseUser": "postgres",
      "connectionType": "jdbc"
    }
  ]
}
```

## Output Format

The module converts API responses to this format (same as `connections.py`):

```python
{
    "ORACLE_10": {
        "id": "4976629955435844",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
        "user": "icc_test"
    },
    "POSTGRE_11": {
        "id": "955225233921727",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.11:5432/postgres",
        "user": "postgres"
    }
}
```

## Database Type Detection

The module automatically detects database types based on:

1. **URL patterns**: `jdbc:postgresql`, `jdbc:oracle`, `jdbc:sqlserver`, etc.
2. **Connection names**: "oracle", "postgre", "mssql", "mongo", etc.
3. **Connection type**: "oauth2" for Azure Data Lake

Supported types:
- PostgreSQL
- Oracle
- SQL Server
- Hive
- SAP HANA
- MongoDB
- Cassandra
- Snowflake
- Azure Data Lake
- SFTP
- Generic (fallback)

## Error Handling

The module handles various errors:

```python
try:
    connections = fetch_and_map_connections()
except RuntimeError as e:
    # ICC_CONNECTION_LIST_URL not set
    print(f"Configuration error: {e}")
except requests.exceptions.RequestException as e:
    # Network error, API unavailable
    print(f"Network error: {e}")
except json.JSONDecodeError as e:
    # Invalid JSON response
    print(f"Parse error: {e}")
```

## Complete Integration Example

```python
# In app.py

from src.ai.router.memory import Memory
from src.utils.fetch_connections import populate_memory_connections
from src.ai.router.router import handle_turn
import logging

logger = logging.getLogger(__name__)

def initialize_memory():
    """Initialize memory with dynamic connections"""
    memory = Memory()
    
    # Try to load connections from API
    try:
        if populate_memory_connections(memory):
            logger.info(f"✅ Loaded {len(memory.connections)} connections from API")
            
            # Optionally print connection names
            conn_names = list(memory.connections.keys())
            logger.info(f"Available connections: {', '.join(conn_names[:5])}...")
        else:
            logger.warning("⚠️ Using static connections.py as fallback")
    except Exception as e:
        logger.error(f"❌ Failed to load dynamic connections: {e}")
        logger.info("Will use static connections.py")
    
    return memory

# Initialize
memory = initialize_memory()

# Use in conversation
async def chat(user_input):
    memory, response = await handle_turn(memory, user_input)
    return response
```

## Troubleshooting

### Issue: "ICC_CONNECTION_LIST_URL env variable is not set"

**Solution:**
```powershell
# Set in PowerShell
$env:ICC_CONNECTION_LIST_URL = "https://172.16.22.13:8084/connection/list"

# Or add to .env file
echo 'ICC_CONNECTION_LIST_URL=https://172.16.22.13:8084/connection/list' >> .env
```

### Issue: "Failed to fetch connection list"

**Possible causes:**
1. Not connected to VPN
2. API endpoint is incorrect
3. API is down
4. Authentication required but not provided

**Solution:**
- Check VPN connection
- Verify the API URL
- Try with authentication:
  ```python
  connections = fetch_and_map_connections(auth=("user", "pass"))
  ```

### Issue: "No connections found"

**Possible causes:**
1. API returned empty list
2. All connections missing required fields (name or id)

**Solution:**
- Check API response format
- Check logs for "Skipping connection" messages
- Run standalone test to see raw data

### Issue: "Unknown connection 'ORACLE_10'"

**Possible causes:**
1. `memory.connections` is empty
2. Connection name doesn't exist in API response

**Solution:**
- Check if `populate_memory_connections()` returned True
- Verify connection name matches exactly (case-sensitive)
- The system will automatically fall back to static `connections.py`

## Testing

```powershell
# Test fetching connections
uv run python src/utils/fetch_connections.py

# Test in Python REPL
uv run python
>>> from src.utils.fetch_connections import fetch_and_map_connections
>>> connections = fetch_and_map_connections()
>>> print(f"Found {len(connections)} connections")
>>> print(list(connections.keys())[:5])
```

## Notes

- ✅ The system has a **fallback mechanism** - if dynamic connections fail, it uses `connections.py`
- ✅ Connection data is cached in `Memory` for the session
- ✅ No need to re-fetch on every request
- ✅ Saved JSON files include timestamps for debugging
- ✅ All functions have proper logging for troubleshooting
