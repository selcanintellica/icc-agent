# Connection ID Implementation

## Overview

Updated the system to use **connection IDs** instead of connection names when making API calls for job creation. The API expects numeric IDs, not connection names.

## Changes Made

### 1. ✨ **New File: `src/utils/connections.py`**

Created a mapping of connection names to their IDs and metadata:

```python
CONNECTIONS: Dict[str, Dict[str, Any]] = {
    "ORACLE_10": {
        "id": "955448816772621",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
        "user": "icc_test",
    },
    "POSTGRE_11": {
        "id": "955225233921727",
        "db_type": "PostgreSQL",
        ...
    },
    # ... 18 total connections
}
```

**Helper Functions:**
- `get_connection_id(connection_name)` - Returns connection ID for API calls
- `get_connection_info(connection_name)` - Returns full connection metadata
- `list_connections()` - Returns all available connections

### 2. 🔄 **Updated: `db_config.json`**

Changed connection names to match the keys in `CONNECTIONS` dict:

**Before:**
```json
{
  "name": "oracle_10",
  "label": "Oracle Production (10)"
}
```

**After:**
```json
{
  "name": "ORACLE_10",
  "label": "Oracle Production (10)"
}
```

Added more connections from the CONNECTIONS dict:
- `ORACLE_10`, `ORACLE_11`, `oracle_18`
- `POSTGRE_11`, `POSTGRE_14`
- `MSSQL`

### 3. 🔧 **Updated: `src/ai/router/router.py`**

Modified all three job creation functions to convert connection names to IDs:

#### **Read SQL Job** (Line ~82)

```python
# Get connection ID from connection name
connection_id = get_connection_id(memory.connection)
if not connection_id:
    return memory, f"❌ Error: Unknown connection '{memory.connection}'."

# Use connection ID in API request
request = ReadSqlLLMRequest(
    variables=[ReadSqlVariables(
        query=memory.last_sql,
        connection=connection_id,  # ← ID instead of name
        ...
    )]
)
```

#### **Write Data Job** (Line ~168)

```python
# Get connection ID
connection_id = get_connection_id(memory.connection)

request = WriteDataLLMRequest(
    variables=[WriteDataVariables(
        connection=connection_id,  # ← ID instead of name
        schemas=memory.schema,
        table=table_name,
        ...
    )]
)
```

#### **Send Email Job** (Line ~230)

```python
# Get connection ID
connection_id = get_connection_id(memory.connection)

request = SendEmailLLMRequest(
    variables=[SendEmailVariables(
        connection=connection_id,  # ← ID instead of name
        query=memory.last_sql,
        ...
    )]
)
```

### 4. 📝 **Updated: `src/ai/router/memory.py`**

Changed default connection name to match new format:

```python
connection: str = "ORACLE_10"  # Was "oracle_10"
```

## Flow Diagram

```
User Selects in UI
     ↓
Connection Name: "ORACLE_10"
     ↓
Stored in Memory
     ↓
Router needs to create job
     ↓
get_connection_id("ORACLE_10")
     ↓
Returns: "955448816772621"
     ↓
API Request uses ID: "955448816772621"
     ↓
Job Created Successfully
```

## Connection Name → ID Mapping

| Connection Name | Connection ID | Database Type |
|----------------|---------------|---------------|
| ORACLE_10 | 955448816772621 | Oracle |
| ORACLE_11 | 9592123237737 | Oracle |
| oracle_18 | 23061586410134803 | Oracle |
| POSTGRE_11 | 955225233921727 | PostgreSQL |
| POSTGRE_14 | 2433676967192755 | PostgreSQL |
| POSTGRE_DEMO | 3134782933199896 | PostgreSQL |
| MSSQL | 8449030761986558 | SQL Server |
| Mongo | 2929902649070900 | MongoDB |
| Cassandra | 5861393593217446 | Cassandra |
| HANA | 8448800292564427 | SAP HANA |
| Hive | 8453303386327603 | Hive |
| NETEZZA | 1829742320324078 | Netezza |
| Postgresql | 8449161086856529 | PostgreSQL |
| VFPT_POSTGRESQL | 31817712937260880 | PostgreSQL |
| SFTP_SERVER | 32050305818626884 | SFTP |
| ozlem_908 | 13926603303722332 | Azure Data Lake |
| piateam_azure_data_lake | 13924989252846968 | Azure Data Lake |

## Error Handling

If an unknown connection is selected:

```python
connection_id = get_connection_id("UNKNOWN_DB")
if not connection_id:
    # Returns error message to user
    return memory, "❌ Error: Unknown connection 'UNKNOWN_DB'. Please select a valid connection."
```

## Benefits

✅ **API Compatible**: Jobs now use correct numeric IDs as expected by API
✅ **Centralized Mapping**: All connection info in one place
✅ **Error Prevention**: Validates connection exists before making API call
✅ **Metadata Available**: Can access db_type, url, user for each connection
✅ **Maintainable**: Easy to add new connections to the mapping

## Testing Checklist

- [ ] Select connection in UI (e.g., "ORACLE_10")
- [ ] Ask for SQL query (e.g., "get all customers")
- [ ] Verify job creation uses connection ID "955448816772621"
- [ ] Check logs show: `🔌 Using connection: ORACLE_10 (ID: 955448816772621)`
- [ ] Verify API receives correct ID in request payload
- [ ] Test with different connections to ensure mapping works

## Next Steps

1. **Update Table API**: The `table_api_client.py` may also need connection IDs
2. **Add Validation**: Ensure UI only shows connections that exist in `CONNECTIONS` dict
3. **Sync Config**: Keep `db_config.json` in sync with `CONNECTIONS` mapping
