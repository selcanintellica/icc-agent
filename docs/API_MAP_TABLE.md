# Map Table API Documentation

## Overview

The Map Table API allows any UI to handle column mapping for Compare SQL operations. When the agent needs to compare two SQL queries, it will request column mappings from the user.

## How It Works

### 1. Detect Map Table Request

When you send a message via `/api/chat/message`, check the response for:

```json
{
  "session_id": "...",
  "response": "Map Table: Please map columns between your two queries...",
  "stage": "WAITING_MAP_TABLE",
  "requires_mapping": true,
  "mapping_data": {
    "first_columns": ["customer_id", "name", "email"],
    "second_columns": ["cust_id", "customer_name", "contact_email"],
    "auto_matched": true,
    "pre_mappings": [
      {
        "FirstMappedColumn": "name",
        "SecondMappedColumn": "customer_name"
      }
    ]
  }
}
```

### 2. Display Mapping UI

Your UI should:
1. Check `requires_mapping: true`
2. Extract `mapping_data`:
   - `first_columns`: Array of column names from first query
   - `second_columns`: Array of column names from second query
   - `auto_matched`: Boolean indicating if auto-matching was performed
   - `pre_mappings`: Array of pre-matched columns (if auto_matched is true)
3. Present a mapping interface where users can:
   - Map columns from first query to second query
   - Mark key columns for joining

### 3. Submit Mappings

POST to `/api/chat/submit-mapping`:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "column_mappings": [
    {
      "FirstMappedColumn": "customer_id",
      "SecondMappedColumn": "cust_id"
    },
    {
      "FirstMappedColumn": "name",
      "SecondMappedColumn": "customer_name"
    }
  ],
  "key_mappings": [
    {
      "FirstKey": "customer_id",
      "SecondKey": "cust_id"
    }
  ],
  "connection": "ORACLE_10",
  "schema_name": "SALES",
  "tables": ["customers", "orders"]
}
```

### 4. Continue Conversation

The response from `/submit-mapping` is a standard `ChatMessageResponse`, so the conversation continues normally.

## API Endpoints

### POST /api/chat/message

Standard chat endpoint. Check response for `requires_mapping: true`.

**Response Fields (new)**:
- `requires_mapping` (boolean): True if map table is needed
- `mapping_data` (object): Column mapping data

### POST /api/chat/submit-mapping

Submit column mappings to continue conversation.

**Request Body**:
```typescript
{
  session_id: string;          // Session ID (required)
  column_mappings: Array<{     // At least 1 mapping required
    FirstMappedColumn: string;
    SecondMappedColumn: string;
  }>;
  key_mappings?: Array<{       // Optional key columns for joining
    FirstKey: string;
    SecondKey: string;
  }>;
  connection?: string;         // Optional connection ID
  schema_name?: string;        // Optional schema name
  tables?: string[];           // Optional table list
}
```

**Response**: Standard `ChatMessageResponse`

## Example Flow

### Step 1: User asks to compare queries

```bash
POST /api/chat/message
{
  "session_id": "123",
  "message": "Compare customers in both databases"
}
```

### Step 2: Agent returns map table request

```json
{
  "session_id": "123",
  "response": "Map Table: Please map columns...",
  "requires_mapping": true,
  "mapping_data": {
    "first_columns": ["id", "name"],
    "second_columns": ["customer_id", "full_name"],
    "auto_matched": false
  }
}
```

### Step 3: UI shows mapping interface

User maps:
- `id` → `customer_id` (mark as key)
- `name` → `full_name`

### Step 4: Submit mappings

```bash
POST /api/chat/submit-mapping
{
  "session_id": "123",
  "column_mappings": [
    {"FirstMappedColumn": "id", "SecondMappedColumn": "customer_id"},
    {"FirstMappedColumn": "name", "SecondMappedColumn": "full_name"}
  ],
  "key_mappings": [
    {"FirstKey": "id", "SecondKey": "customer_id"}
  ]
}
```

### Step 5: Agent processes and responds

```json
{
  "session_id": "123",
  "response": "Great! I'll compare the queries using those mappings. Running comparison now...",
  "stage": "COMPARING_RESULTS"
}
```

## UI Implementation Examples

### React Example

```tsx
function ChatInterface() {
  const [mappingData, setMappingData] = useState(null);

  const handleSendMessage = async (message) => {
    const response = await fetch('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({ session_id, message })
    });
    const data = await response.json();

    if (data.requires_mapping) {
      // Show mapping modal
      setMappingData(data.mapping_data);
    } else {
      // Show regular message
      displayMessage(data.response);
    }
  };

  const handleSubmitMappings = async (mappings) => {
    const response = await fetch('/api/chat/submit-mapping', {
      method: 'POST',
      body: JSON.stringify({
        session_id,
        column_mappings: mappings.columns,
        key_mappings: mappings.keys
      })
    });
    const data = await response.json();
    displayMessage(data.response);
    setMappingData(null);
  };

  return (
    <>
      <ChatWindow />
      {mappingData && (
        <MappingModal
          data={mappingData}
          onSubmit={handleSubmitMappings}
        />
      )}
    </>
  );
}
```

### Vue Example

```vue
<template>
  <div>
    <ChatWindow />
    <MappingModal
      v-if="mappingData"
      :data="mappingData"
      @submit="handleSubmitMappings"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      mappingData: null
    };
  },
  methods: {
    async sendMessage(message) {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        body: JSON.stringify({ session_id: this.sessionId, message })
      });
      const data = await response.json();

      if (data.requires_mapping) {
        this.mappingData = data.mapping_data;
      } else {
        this.displayMessage(data.response);
      }
    },
    async handleSubmitMappings(mappings) {
      const response = await fetch('/api/chat/submit-mapping', {
        method: 'POST',
        body: JSON.stringify({
          session_id: this.sessionId,
          column_mappings: mappings.columns,
          key_mappings: mappings.keys
        })
      });
      const data = await response.json();
      this.displayMessage(data.response);
      this.mappingData = null;
    }
  }
};
</script>
```

## Benefits

✅ **UI Agnostic**: Any frontend (React, Vue, Angular, Mobile) can implement map tables

✅ **Consistent API**: Same structure as other dropdowns (connection, schema, table)

✅ **Auto-matching Support**: Backend can suggest mappings based on column names

✅ **Flexible**: Supports both column mappings and key mappings

✅ **Type-safe**: Full Pydantic validation on backend

## Testing

You can test the map table API with curl:

```bash
# 1. Start a session
curl -X POST http://localhost:8000/api/chat/sessions

# 2. Send a compare query
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "message": "compare customers table in both databases"
  }'

# 3. If you get requires_mapping: true, submit mappings
curl -X POST http://localhost:8000/api/chat/submit-mapping \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "column_mappings": [
      {"FirstMappedColumn": "id", "SecondMappedColumn": "customer_id"}
    ],
    "key_mappings": [
      {"FirstKey": "id", "SecondKey": "customer_id"}
    ]
  }'
```

## Migration from Dash UI

The existing Dash UI in `app.py` will continue to work. To migrate to the new API:

1. The Dash UI already receives `MAP_TABLE_POPUP` responses
2. Instead of handling it in Dash callbacks, send it to backend
3. Backend will parse and return structured `mapping_data`
4. Dash can then use the same mapping modal but submit via API

This maintains backward compatibility while enabling new UIs.
