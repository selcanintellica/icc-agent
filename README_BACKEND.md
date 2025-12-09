# ICC Agent - FastAPI Backend Integration Guide

## Overview

The ICC Agent backend provides a REST API for natural language database operations. This guide explains how to integrate the backend into your existing system.

## Architecture

```
Your Frontend/System          ICC Agent Backend (FastAPI)
       │                              │
       ├─ POST /api/chat/message ────>│
       │                              ├─ RouterService
       │                              ├─ LLM Agents (Local)
       │                              ├─ Job Execution
       │<─────────────────────────────┤
       │  JSON Response               │
```

## Quick Start

### 1. Installation

```bash
# Clone or receive the ICC Agent repository
cd ICC_try

# Install dependencies
pip install -r requirements_backend.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 2. Start the Backend Server

```bash
# Windows - Use the batch script (recommended)
.\start_backend.bat

# Linux/Mac - Use the shell script
./start_backend.sh

# Or start manually with uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the Python script directly
python backend/main.py
```

### 3. Verify Installation

```bash
# Health check
curl http://localhost:8000/api/health

# API documentation
open http://localhost:8000/docs
```

## API Endpoints

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: Configure in your deployment

---

### 1. Health Check

**GET** `/api/health`

Check if the service is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-12-09T10:30:00Z",
  "services": {
    "router": "ok",
    "session_manager": "ok",
    "connection_service": "ok"
  }
}
```

---

### 2. Create Session

**POST** `/api/chat/sessions`

Create a new conversation session. Sessions maintain context across multiple messages.

**Request:**
```json
{
  "session_id": "optional-custom-id"
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-09T10:30:00Z",
  "stage": "router",
  "message": "Session created successfully"
}
```

---

### 3. Send Message

**POST** `/api/chat/message`

Send a message to the agent and receive a response.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "get all customers from USA",
  "connection": "ORACLE_10",
  "schema": "SALES",
  "tables": ["customers", "orders"]
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Here's the SQL query:\nSELECT * FROM customers WHERE country = 'USA'\n\nLooks good?",
  "stage": "confirm_generated_sql",
  "gathered_params": {},
  "job_context": {
    "sql_query": "SELECT * FROM customers WHERE country = 'USA'"
  },
  "requires_dropdown": false,
  "dropdown_type": null,
  "dropdown_options": null,
  "error": null
}
```

**Dropdown Response Example:**
```json
{
  "session_id": "...",
  "response": "Please select a database connection:",
  "stage": "need_connection",
  "requires_dropdown": true,
  "dropdown_type": "connection",
  "dropdown_options": [
    {"id": "4976629955435844", "name": "ORACLE_10", "type": "oracle"},
    {"id": "4976629955435845", "name": "POSTGRES_01", "type": "postgres"}
  ]
}
```

**Handling Dropdown Selections:**

When `requires_dropdown: true`, display the options to the user. When user selects, send:

```json
{
  "session_id": "...",
  "message": "__CONNECTION_SELECTED__:4976629955435844"
}
```

Dropdown types and prefixes:
- Connection: `__CONNECTION_SELECTED__:{connection_id}`
- Schema: `__SCHEMA_SELECTED__:{schema_name}`
- Table: `__TABLE_SELECTED__:{table_name}`

---

### 4. Get Session Info

**GET** `/api/chat/sessions/{session_id}`

Retrieve information about an existing session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stage": "confirm_generated_sql",
  "message": "Session retrieved successfully"
}
```

---

### 5. Delete Session

**DELETE** `/api/chat/sessions/{session_id}`

Delete a session and its associated memory.

**Response:**
```json
{
  "message": "Session 550e8400-e29b-41d4-a716-446655440000 deleted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 6. List Connections

**GET** `/api/connections`

Get all available database connections.

**Response:**
```json
{
  "connections": [
    {"id": "4976629955435844", "name": "ORACLE_10", "type": "oracle"},
    {"id": "4976629955435845", "name": "POSTGRES_01", "type": "postgres"}
  ],
  "count": 2
}
```

---

### 7. List Schemas

**GET** `/api/connections/{connection_id}/schemas`

Get schemas for a specific connection.

**Response:**
```json
{
  "connection_id": "ORACLE_10",
  "schemas": [
    {"name": "SALES", "tables": ["customers", "orders", "products"]},
    {"name": "HR", "tables": ["employees", "departments"]}
  ],
  "count": 2
}
```

---

### 8. List Tables

**GET** `/api/connections/{connection_id}/schemas/{schema_name}/tables`

Get tables in a specific schema.

**Response:**
```json
{
  "connection_id": "ORACLE_10",
  "schema_name": "SALES",
  "tables": ["customers", "orders", "products", "order_items"],
  "count": 4
}
```

---

## Integration Workflow

### Typical Conversation Flow

```
1. Your Frontend: POST /api/chat/sessions
   ← {session_id: "abc-123"}

2. Frontend: POST /api/chat/message
   {session_id: "abc-123", message: "get customers"}
   ← {requires_dropdown: true, dropdown_type: "connection", ...}

3. User selects connection in your UI

4. Frontend: POST /api/chat/message
   {session_id: "abc-123", message: "__CONNECTION_SELECTED__:ORACLE_10"}
   ← {requires_dropdown: true, dropdown_type: "schema", ...}

5. User selects schema in your UI

6. Frontend: POST /api/chat/message
   {session_id: "abc-123", message: "__SCHEMA_SELECTED__:SALES"}
   ← {response: "Here's the SQL...", stage: "confirm_sql"}

7. Frontend: POST /api/chat/message
   {session_id: "abc-123", message: "yes"}
   ← {response: "What should I name this job?"}

8. Frontend: POST /api/chat/message
   {session_id: "abc-123", message: "customer_report"}
   ← {response: "Job created! ID: 12345", stage: "show_results"}
```

### Example: Full Integration (Python)

```python
import requests
import uuid

BASE_URL = "http://localhost:8000"

# 1. Create session
session_id = str(uuid.uuid4())
response = requests.post(
    f"{BASE_URL}/api/chat/sessions",
    json={"session_id": session_id}
)
print(f"Session created: {session_id}")

# 2. Send first message
response = requests.post(
    f"{BASE_URL}/api/chat/message",
    json={
        "session_id": session_id,
        "message": "get all customers",
        "connection": "ORACLE_10",
        "schema": "SALES",
        "tables": ["customers"]
    }
)

data = response.json()
print(f"Agent: {data['response']}")
print(f"Stage: {data['stage']}")

# 3. Confirm SQL
if data['stage'] == 'confirm_generated_sql':
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "yes"
        }
    )
    data = response.json()
    print(f"Agent: {data['response']}")

# 4. Provide job name
response = requests.post(
    f"{BASE_URL}/api/chat/message",
    json={
        "session_id": session_id,
        "message": "customer_list"
    }
)

data = response.json()
print(f"Agent: {data['response']}")
print(f"Job ID: {data['job_context'].get('job_id')}")
```

### Example: JavaScript/TypeScript Integration

```typescript
const BASE_URL = 'http://localhost:8000';

class ICCAgentClient {
  private sessionId: string;

  constructor() {
    this.sessionId = '';
  }

  async createSession(): Promise<string> {
    const response = await fetch(`${BASE_URL}/api/chat/sessions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({})
    });
    
    const data = await response.json();
    this.sessionId = data.session_id;
    return this.sessionId;
  }

  async sendMessage(
    message: string,
    connection?: string,
    schema?: string,
    tables?: string[]
  ): Promise<any> {
    const response = await fetch(`${BASE_URL}/api/chat/message`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        session_id: this.sessionId,
        message,
        connection,
        schema,
        tables
      })
    });
    
    return await response.json();
  }

  async getConnections(): Promise<any> {
    const response = await fetch(`${BASE_URL}/api/connections`);
    return await response.json();
  }
}

// Usage
const client = new ICCAgentClient();
await client.createSession();

const response = await client.sendMessage(
  'get all customers',
  'ORACLE_10',
  'SALES',
  ['customers']
);

console.log(response.response);
```

---

## Error Handling

All errors follow a consistent structure:

```json
{
  "session_id": "...",
  "response": "Error message for display",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Failed to authenticate with ICC API",
    "details": {"status_code": 401},
    "category": "authentication"
  }
}
```

**Error Categories:**
- `authentication` - Authentication/authorization errors
- `connection` - Database connection errors
- `validation` - Input validation errors
- `job` - Job execution errors
- `llm` - LLM/AI errors
- `configuration` - Configuration errors
- `internal` - Internal server errors

**Error Codes:**
See `src/errors/error_codes.py` for complete list.

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# LLM Configuration
MODEL_NAME=qwen3:8b
SQL_MODEL_NAME=qwen2.5-coder:7b

# Logging
LOG_LEVEL=INFO
ENABLE_PROMPT_LOGGING=false
PROMPT_LOG_DIR=prompt_logs

# ICC API (if using external ICC backend)
ICC_API_BASE=https://your-icc-api.com
ICC_API_USER=your_username
ICC_API_PASSWORD=your_password
```

### CORS Configuration

The backend allows cross-origin requests. Configure allowed origins:

```bash
CORS_ORIGINS=http://localhost:3000,https://your-frontend.com
```

Or allow all (development only):
```bash
CORS_ORIGINS=*
```

---

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements_backend.txt .
RUN pip install --no-cache-dir -r requirements_backend.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t icc-agent-backend .
docker run -p 8000:8000 --env-file .env icc-agent-backend
```

### Production Server

**Linux/Mac** - Use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn

gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

**Windows** - Use Uvicorn directly (Gunicorn doesn't support Windows):

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Testing

The Dash UI (`app.py`) remains available for testing:

```bash
# Start Dash UI (port 8050)
uv run app.py

# Start FastAPI Backend (port 8000) - Windows
.\start_backend.bat

# Start FastAPI Backend (port 8000) - Linux/Mac
./start_backend.sh
```

Both can run simultaneously for testing and development.

**Note**: The startup scripts automatically:
- Activate the virtual environment (`.venv`)
- Set the correct PYTHONPATH
- Start uvicorn with auto-reload enabled

---

## API Documentation

Interactive API documentation is automatically generated:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error responses for detailed error information
3. Check logs for server-side errors
4. Consult the main documentation in `docs/` folder

---

## Architecture Documents

For detailed technical information:
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture
- [DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md) - Development guide
- [ADDING_NEW_JOB.md](../docs/ADDING_NEW_JOB.md) - Extending the system
