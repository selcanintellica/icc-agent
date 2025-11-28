# ICC API Client - Schema Fetching Integration

## Overview
Enhanced the ICC agent to dynamically fetch and present available schemas to users when writing data to a database connection.

## Architecture

### New Module: `src/utils/connection_api_client.py`
Professional, unified ICC API client that handles:
- **Connection fetching**: GET `/connection/list`
- **Schema fetching**: POST `/utility/connection/{connection_id}`
- **Authentication**: Uses `src.utils.auth.authenticate()`
- **Response mapping**: Converts API responses to internal formats

### Key Components

#### 1. ICCAPIClient Class
```python
class ICCAPIClient:
    async def fetch_connections() -> Dict[str, Dict[str, Any]]
    async def fetch_schemas(connection_id: str) -> List[str]
```

#### 2. Helper Functions
```python
async def populate_memory_connections(memory, auth_headers) -> bool
async def fetch_schemas_for_connection(connection_id: str, auth_headers) -> List[str]
```

## Flow

### Write Data Job - Schema Selection Flow

1. **User completes ReadSQL job**
   - User says "write" or "write data"
   - System enters write_data parameter gathering

2. **System asks for job name**
   - User provides name (e.g., "write449")

3. **System asks for table name**
   - User provides table (e.g., "target_table")

4. **System presents connection list** (from 30 fetched connections)
   ```
   Which connection should I use to write the data?
   
   Available connections:
   • NETEZZA (Generic)
   • netezza_Test (Generic)
   • ORACLE_10 (Oracle)
   • ...
   ```

5. **User selects connection** (e.g., "ORACLE_10")
   - System performs fuzzy matching (handles "ORACLE_10", "oracle10", "ORACLE_10 (Oracle)")
   - Gets connection ID: "4976629955435844"

6. **System fetches schemas dynamically**
   - POST to `https://172.16.22.13:8084/utility/connection/4976629955435844`
   - Receives list of ~50 schemas
   - Caches in `memory.available_schemas`

7. **System presents schema list**
   ```
   Which schema should I write the data to?
   
   Available schemas:
   • ANONYMOUS
   • HR
   • ICC_META
   • ICC_TEST
   • SYSTEM
   • ...
   ```

8. **User selects schema** (e.g., "ICC_TEST")
   - System uses schema name directly (not ID)
   - Continues with remaining parameters

9. **System executes write_data job**
   - Uses connection ID for API call
   - Uses schema name as string

## Memory Enhancements

### New Fields
```python
@dataclass
class Memory:
    connections: Dict[str, Dict[str, Any]]  # Cached connection list
    available_schemas: List[str]  # Cached schema list for selected connection
```

### New Methods
```python
def get_connection_id(self, connection_name: str) -> Optional[str]:
    """Fuzzy matching for connection names"""
    
def get_schema_list_for_llm(self) -> str:
    """Format schemas for display to user"""
```

## Job Agent Enhancements

### New Action Type: FETCH_SCHEMAS
```python
{
    "action": "FETCH_SCHEMAS",
    "connection": "ORACLE_10",
    "question": "Fetching available schemas..."
}
```

This signals the router to:
1. Get connection ID from connection name
2. Make async API call to fetch schemas
3. Cache schemas in memory
4. Present schema list to user

## Router Enhancements

### FETCH_SCHEMAS Handler
```python
if action.get("action") == "FETCH_SCHEMAS":
    connection_id = memory.get_connection_id(connection_name)
    schemas = await fetch_schemas_for_connection(connection_id, auth_headers)
    memory.available_schemas = schemas
    return memory, "Which schema...?\n\nAvailable schemas:\n{schema_list}"
```

## API Endpoints Used

### 1. Connection List
- **URL**: `https://172.16.22.13:8084/connection/list`
- **Method**: GET
- **Auth**: HTTPBasicAuth + TokenKey header
- **Response**: `{ "object": [...] }`

### 2. Schema List
- **URL**: `https://172.16.22.13:8084/utility/connection/{connection_id}`
- **Method**: POST
- **Body**: Empty
- **Auth**: HTTPBasicAuth + TokenKey header
- **Response**: `["SCHEMA1", "SCHEMA2", ...]`

## Fuzzy Matching

Connection names support flexible matching:
- **Exact**: "ORACLE_10" → "ORACLE_10"
- **With type**: "ORACLE_10 (Oracle)" → "ORACLE_10"
- **No separators**: "oracle10" → "ORACLE_10"
- **Case insensitive**: "ORACLE10" → "ORACLE_10"

## Error Handling

### Schema Fetch Failures
- If fetch fails, falls back to asking for schema without list
- User can still manually type schema name
- Logs error for debugging

### Missing Connection ID
- If connection not found, shows error message
- User must select valid connection

## Testing

### Test Script
```bash
python src/utils/connection_api_client.py
```

Tests:
1. Connection fetching (30 connections)
2. Schema fetching for first connection
3. Authentication flow
4. Response mapping

## Migration Notes

### Old Files
- `src/utils/fetch_connections.py` - Still exists, contains legacy logic
- Can be deprecated once new client is stable

### New Files
- `src/utils/connection_api_client.py` - Professional unified API client

### Updated Files
- `app.py` - Uses `connection_api_client` instead of `fetch_connections`
- `src/ai/router/memory.py` - Added schema caching and formatting
- `src/ai/router/job_agent.py` - Added FETCH_SCHEMAS action
- `src/ai/router/router.py` - Added FETCH_SCHEMAS handler

## Benefits

1. **Dynamic Schema Lists**: No hardcoding, always up-to-date
2. **Better UX**: Users see available schemas, reducing typos
3. **Professional Structure**: Unified API client, easy to extend
4. **Fuzzy Matching**: Flexible connection name matching
5. **Caching**: Schemas cached in memory, no redundant fetches
6. **Error Handling**: Graceful degradation if API fails

## Future Enhancements

Potential additions to `ICCAPIClient`:
- Table list fetching for a schema
- Column metadata fetching
- Connection testing/validation
- Batch operations
- Caching layer with TTL
- Retry logic with exponential backoff
