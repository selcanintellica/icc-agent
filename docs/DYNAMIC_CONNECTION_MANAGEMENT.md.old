# Dynamic Connection Management

## Overview

The system now supports **dynamic connection loading** from an API instead of relying on the static `connections.py` file. This allows for real-time updates to available database connections without code changes.

## Architecture Changes

### 1. **Memory Class Updates** (`src/ai/router/memory.py`)

Added new fields and methods to `Memory` class:

```python
class Memory:
    connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """Get connection ID from stored connections."""
        
    def get_connection_list_for_llm(self) -> str:
        """Format connection list for LLM to present to user."""
```

### 2. **Router Updates** (`src/ai/router/router.py`)

All connection ID lookups now use `memory.get_connection_id()` instead of importing from static `connections.py`:

```python
# Before:
from src.utils.connections import get_connection_id
connection_id = get_connection_id(memory.connection)

# After:
connection_id = memory.get_connection_id(memory.connection)
```

### 3. **Connection Loader** (`src/utils/connection_loader.py`)

New utility module for working with dynamic connection data:
- `format_connection_data()` - Convert API response to expected format
- `get_connection_names()` - Extract list of connection names
- `format_connections_for_display()` - Format for user display
- `validate_connection_exists()` - Validate connection name

## Integration Steps

### Step 1: Fetch Connections from API

Make your API call to retrieve the connection list:

```python
# Your API call (implement this)
def fetch_connections_from_api() -> List[Dict[str, Any]]:
    """
    Fetch connections from your API endpoint.
    
    Expected API response format:
    [
        {
            "name": "ORACLE_10",
            "id": "4976629955435844",
            "db_type": "Oracle",
            "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
            "user": "icc_test"
        },
        {
            "name": "POSTGRE_11",
            "id": "955225233921727",
            "db_type": "PostgreSQL",
            "url": "jdbc:postgresql://172.16.44.11:5432/postgres",
            "user": "postgres"
        }
    ]
    """
    response = requests.get("your-api-endpoint/connections")
    return response.json()
```

### Step 2: Format the Data

Convert API response to the format expected by Memory:

```python
from src.utils.connection_loader import format_connection_data

# Get data from API
api_connections = fetch_connections_from_api()

# Convert to required format
formatted_connections = format_connection_data(api_connections)

# Result:
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

### Step 3: Initialize Memory with Connections

When creating or initializing a Memory instance:

```python
from src.ai.router.memory import Memory
from src.utils.connection_loader import format_connection_data

# Create memory instance
memory = Memory()

# Fetch and load connections
api_connections = fetch_connections_from_api()
memory.connections = format_connection_data(api_connections)

# Optionally set default connection
if memory.connections:
    memory.connection = list(memory.connections.keys())[0]
```

### Step 4: Present Connections to User

Let the LLM ask the user which connection they want to use:

```python
# Get formatted list for display
connection_list = memory.get_connection_list_for_llm()

# Example output:
"""
• ORACLE_10 (Oracle)
• ORACLE_11 (Oracle)
• POSTGRE_11 (PostgreSQL)
• POSTGRE_14 (PostgreSQL)
• MSSQL (SQL Server)
"""

# In your router/agent:
return memory, f"Please select a connection:\n\n{connection_list}\n\nType the connection name:"
```

### Step 5: Validate User Selection

```python
from src.utils.connection_loader import validate_connection_exists

user_choice = user_utterance.strip()

if validate_connection_exists(user_choice, memory.connections):
    memory.connection = user_choice
    connection_id = memory.get_connection_id(user_choice)
    return memory, f"✅ Connected to {user_choice} (ID: {connection_id})"
else:
    return memory, f"❌ '{user_choice}' not found. Please choose from available connections."
```

## Complete Example

Here's a complete flow from API to execution:

```python
from src.ai.router.memory import Memory
from src.ai.router.router import handle_turn
from src.utils.connection_loader import format_connection_data

# 1. Initialize conversation
memory = Memory()

# 2. Fetch connections from API
api_connections = fetch_connections_from_api()  # Your implementation
memory.connections = format_connection_data(api_connections)

# 3. Start conversation
memory, response = await handle_turn(memory, "start")
# Response: "How would you like to proceed? 'readsql' or 'comparesql'?"

# 4. User chooses job type
memory, response = await handle_turn(memory, "readsql")

# 5. Before generating SQL, show available connections
connection_list = memory.get_connection_list_for_llm()
print(f"Available connections:\n{connection_list}")

# 6. User selects connection
user_choice = "ORACLE_10"
if validate_connection_exists(user_choice, memory.connections):
    memory.connection = user_choice

# 7. Continue with SQL generation
memory, response = await handle_turn(memory, "create")
memory, response = await handle_turn(memory, "get all customers from USA")

# 8. Execute job - connection ID is automatically retrieved
memory, response = await handle_turn(memory, "yes")

# Behind the scenes:
# - memory.get_connection_id("ORACLE_10") returns "4976629955435844"
# - API receives the numeric ID in the job request
```

## API Response Format Requirements

Your API should return connections in this format:

```json
[
  {
    "name": "ORACLE_10",
    "id": "4976629955435844",
    "db_type": "Oracle",
    "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
    "user": "icc_test"
  },
  {
    "name": "POSTGRE_11",
    "id": "955225233921727",
    "db_type": "PostgreSQL",
    "url": "jdbc:postgresql://172.16.44.11:5432/postgres",
    "user": "postgres"
  }
]
```

**Required fields:**
- `name` - Connection identifier (used in conversation)
- `id` - Numeric connection ID (used in API calls)

**Optional fields:**
- `db_type` - Database type for display
- `url` - JDBC connection URL
- `user` - Database username

## Where Connection Selection Can Happen

You have multiple options for when/how to set the connection:

### Option A: Set Before Conversation
```python
# In your main application (e.g., app.py)
memory = Memory()
api_connections = fetch_connections_from_api()
memory.connections = format_connection_data(api_connections)
memory.connection = "ORACLE_10"  # Pre-selected by UI
```

### Option B: Let LLM Ask User
```python
# Add a new stage in router.py
if memory.stage == Stage.ASK_CONNECTION:
    connection_list = memory.get_connection_list_for_llm()
    return memory, f"Which connection?\n\n{connection_list}"

# Handle user response
if memory.stage == Stage.CONNECTION_RESPONSE:
    if validate_connection_exists(user_utterance, memory.connections):
        memory.connection = user_utterance
        memory.stage = Stage.ASK_JOB_TYPE
```

### Option C: Accept from External System
```python
# Via API endpoint or message queue
def set_user_context(memory, user_selection):
    memory.connections = fetch_connections_from_api()
    memory.connection = user_selection["connection"]
    memory.schema = user_selection["schema"]
```

## Migration from Static connections.py

The old `src/utils/connections.py` file is **no longer used** by the router. However, you can keep it as a fallback:

```python
# Fallback if API is unavailable
try:
    api_connections = fetch_connections_from_api()
    memory.connections = format_connection_data(api_connections)
except Exception as e:
    logger.warning(f"API unavailable, using fallback: {e}")
    from src.utils.connections import CONNECTIONS
    memory.connections = CONNECTIONS
```

## Error Handling

```python
# Connection not found
connection_id = memory.get_connection_id(memory.connection)
if not connection_id:
    return memory, f"❌ Unknown connection '{memory.connection}'. Please select a valid connection."

# Empty connections list
if not memory.connections:
    return memory, "❌ No connections available. Please contact support."

# Invalid API response
try:
    memory.connections = format_connection_data(api_response)
except Exception as e:
    logger.error(f"Failed to parse connections: {e}")
    return memory, "❌ Failed to load connections. Please try again."
```

## Benefits

✅ **Dynamic Updates** - Connections can be updated without code changes
✅ **Centralized Management** - Connections managed in one place (API)
✅ **User Choice** - LLM can present options and let user choose
✅ **Validation** - Ensures selected connection exists before API call
✅ **Flexible Initialization** - Can be set from UI, API, or conversation
✅ **Backward Compatible** - Can still use static file as fallback

## Testing Checklist

- [ ] API call successfully fetches connection list
- [ ] `format_connection_data()` correctly converts API response
- [ ] `memory.connections` is set before conversation starts
- [ ] `memory.get_connection_id()` returns correct ID
- [ ] `memory.get_connection_list_for_llm()` formats nicely
- [ ] Router uses `memory.get_connection_id()` in all job types
- [ ] Error handling works when connection not found
- [ ] ReadSQL, WriteData, SendEmail, CompareSQL all work with dynamic connections
