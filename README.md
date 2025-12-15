# ICC Agent - Natural Language Database Interface

> **Production-Ready REST API Backend** for converting natural language into database operations

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

ICC Agent is a **FastAPI backend service** that translates natural language requests into executable database operations. It provides a REST API for external systems to integrate conversational AI capabilities for database workflows.

**What it does:**
- Takes natural language input: *"read customer data from sales database"*
- Processes through LLM agents (SQL generation + parameter extraction)
- Executes database jobs: ReadSQL, WriteData, SendEmail, CompareSQL
- Returns structured responses with conversation state

**Built for:**
- Integration with existing frontends/applications
- Stateful conversation management
- Production workloads with reliable small models (7B-8B parameters)
- Docker deployment with health monitoring

---

## 🚀 Quick Start

### Prerequisites

1. **Ollama** (Required for LLM processing)
   ```bash
   # Install from https://ollama.ai
   
   # Pull required models
   ollama pull qwen3:8b
   ollama pull qwen2.5-coder:7b
   
   # Verify Ollama is running
   ollama list
   ```

2. **Python 3.11+** or **Docker**

3. **Database Configuration** (`db_config.json`)
   ```json
   {
     "connections": [
       {
         "id": "connection-id",
         "name": "ORACLE_PROD",
         "type": "oracle",
         "schemas": [...]
       }
     ]
   }
   ```

### Installation & Running

#### Option 1: Docker (Recommended)

```bash
# Build image
docker build -t icc-agent-backend .

# Run container
docker run -d -p 8000:8000 --name icc-backend icc-agent-backend

# Or use docker-compose
docker-compose up -d

# Check status
docker ps
curl http://localhost:8000/api/health
```

#### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Or use startup script
./scripts/start_backend.sh    # Linux/Mac
.\scripts\start_backend.bat   # Windows
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "services": {
#     "router": "ok",
#     "session_manager": "ok",
#     "connection_service": "ok"
#   }
# }

# View API documentation
open http://localhost:8000/docs
```

---

## 📡 API Usage

### Basic Flow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create session
response = requests.post(f"{BASE_URL}/api/chat/sessions")
session_id = response.json()["session_id"]

# 2. Send message
response = requests.post(f"{BASE_URL}/api/chat/message", json={
    "session_id": session_id,
    "message": "read customer data",
    "connection": "ORACLE_PROD",
    "schema_name": "SALES",
    "tables": ["customers"]
})

result = response.json()
print(f"Agent: {result['response']}")
print(f"Stage: {result['stage']}")
print(f"Params: {result['gathered_params']}")

# 3. Continue conversation
response = requests.post(f"{BASE_URL}/api/chat/message", json={
    "session_id": session_id,
    "message": "generate sql to select all customers from USA"
})

# 4. Clean up when done
requests.delete(f"{BASE_URL}/api/chat/sessions/{session_id}")
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/sessions` | Create new conversation session |
| `POST` | `/api/chat/message` | Send message to agent |
| `GET` | `/api/chat/sessions/{id}` | Get session details |
| `DELETE` | `/api/chat/sessions/{id}` | Delete session |
| `GET` | `/api/connections` | List database connections |
| `GET` | `/api/connections/{id}/schemas` | List schemas |
| `GET` | `/api/connections/{id}/schemas/{name}/tables` | List tables |
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

See full API reference at `/docs` endpoint when server is running.

---

## 🏗️ Architecture

### High-Level Flow

```
External Application
        │
        │ HTTP/REST
        ▼
  FastAPI Backend (Port 8000)
        │
        ├─── Service Layer
        │    ├─ RouterService
        │    ├─ SessionManager
        │    └─ ConnectionService
        │
        ├─── Router Orchestrator (Singleton)
        │    └─ Stage Handlers (Strategy Pattern)
        │         ├─ ReadSQL Handler (8 strategies)
        │         ├─ WriteData Handler (1 strategy)
        │         ├─ SendEmail Handler (2 strategies)
        │         └─ CompareSQL Handler (14 strategies)
        │
        └─── LLM Agents (Singleton)
             ├─ SQL Agent (qwen2.5-coder:7b)
             └─ Job Agent (qwen3:8b)
```

### Key Design Patterns

1. **Service Layer Pattern** - Business logic separate from HTTP layer
2. **Singleton Pattern** - LLM agents stay loaded in memory (~0.5-2s responses)
3. **Strategy Pattern** - Each conversation stage = dedicated strategy class
4. **Stateful Sessions** - Memory objects track conversation context

### Why This Architecture?

Traditional agentic systems (LangChain, AutoGPT) give LLMs full autonomy to decide tool calls, leading to:
- ❌ Unreliable tool selection with small models (7B-8B)
- ❌ Infinite reasoning loops
- ❌ Unpredictable multi-step planning (5-15 LLM calls)

Our **semi-static router** approach:
- ✅ Deterministic workflow (95%+ success rate)
- ✅ Fast responses (0.5-2s with singleton pattern)
- ✅ Predictable behavior (users know what to expect)
- ✅ Production ready (consistent performance, low resources)

See [docs/ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) for detailed rationale.

---

## 📂 Project Structure

```
ICC_try/
├── backend/                 # FastAPI application
│   ├── main.py             # Application entry point
│   └── api/
│       ├── routes/         # API endpoints
│       └── models/         # Pydantic schemas
│
├── src/                     # Core business logic
│   ├── ai/
│   │   └── router/         # Router orchestrator & handlers
│   │       ├── router.py   # Main orchestrator (singleton)
│   │       └── stage_handlers/  # Strategy implementations
│   ├── services/           # Service layer
│   │   ├── router_service.py
│   │   ├── session_manager.py
│   │   └── connection_service.py
│   ├── errors/             # Error handling
│   └── utils/              # Utilities
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # System architecture
│   ├── DEVELOPER_GUIDE.md   # Development guide
│   ├── DEPLOYMENT.md        # Deployment guide
│   └── TESTING.md           # Testing guide
│
├── tests/                   # Test suite
│   ├── test_backend.py      # Automated API tests
│   └── test_message_endpoint.py
│
├── scripts/                 # Utility scripts
│   ├── start_backend.bat    # Windows startup
│   └── start_backend.sh     # Linux/Mac startup
│
├── Dockerfile               # Container image
├── docker-compose.yml       # Docker orchestration
├── requirements.txt         # Python dependencies
├── db_config.json          # Database configuration
└── app.py                  # 🧪 Optional: Dash test UI
```

---

## 🧪 Testing

### Automated Tests

```bash
# Run full test suite (7 endpoints)
python tests/test_backend.py

# Expected output:
# ✓ Health Check
# ✓ Create Session
# ✓ Get Session
# ✓ Send Message
# ✓ List Connections
# ✓ Delete Session
# ✓ API Documentation
# 
# All tests passed! (7/7)
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Create session
curl -X POST http://localhost:8000/api/chat/sessions

# Send message
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "message": "help"
  }'

# List connections
curl http://localhost:8000/api/connections
```

### Test UI (Optional)

A Dash-based web UI is available for **testing purposes only**:

```bash
# Install test UI dependencies
pip install -r requirements-dev.txt

# Run test UI
python app.py

# Open browser
open http://localhost:8050
```

**Note**: The Dash UI (`app.py`) is a testing tool, not for production. External applications should integrate via the FastAPI REST API.

---

## 🔧 Configuration

### Environment Variables

```bash
# LLM Models (optional, defaults shown)
MODEL_NAME=qwen3:8b              # Job agent for parameter extraction
SQL_MODEL_NAME=qwen2.5-coder:7b  # SQL agent for query generation

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*                   # Comma-separated origins

# Prompt Logging (optional, for debugging)
ENABLE_PROMPT_LOGGING=false
PROMPT_LOG_DIR=prompt_logs

# Ollama Connection
OLLAMA_HOST=http://localhost:11434
```

### Database Configuration

Edit `db_config.json`:

```json
{
  "connections": [
    {
      "id": "unique-connection-id",
      "name": "ORACLE_PROD",
      "type": "oracle",
      "host": "db.example.com",
      "port": 1521,
      "schemas": [
        {
          "name": "SALES",
          "tables": ["customers", "orders", "products"]
        },
        {
          "name": "HR",
          "tables": ["employees", "departments"]
        }
      ]
    }
  ]
}
```

---

## 🚀 Deployment

### Docker Production

```bash
# Build production image
docker build -t icc-agent-backend:prod .

# Run with environment file
docker run -d \
  -p 8000:8000 \
  --name icc-backend \
  --env-file .env \
  --restart unless-stopped \
  icc-agent-backend:prod

# Check logs
docker logs -f icc-backend

# Monitor health
curl http://localhost:8000/api/health
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  icc-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=*
      - MODEL_NAME=qwen3:8b
      - SQL_MODEL_NAME=qwen2.5-coder:7b
    volumes:
      - ./db_config.json:/app/db_config.json:ro
      - ./prompt_logs:/app/prompt_logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Cloud Deployment

The backend can be deployed to:
- **AWS**: ECS/Fargate, EC2
- **Azure**: Container Instances, App Service
- **GCP**: Cloud Run, GKE
- **Kubernetes**: Deployment + Service + Ingress

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed guides.

---

## 📚 Documentation

Comprehensive documentation in `docs/` folder:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and components
- **[ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md)** - Why semi-static router over agents
- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** - Development patterns and best practices
- **[TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)** - Implementation deep dive
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guides
- **[TESTING.md](docs/TESTING.md)** - Testing strategies and examples
- **[ADDING_NEW_JOB.md](docs/ADDING_NEW_JOB.md)** - How to add new job types

---

## 🛠️ Development

### Local Development Setup

```bash
# Clone repository
git clone <repository-url>
cd ICC_try

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH=$(pwd)   # Linux/Mac
$env:PYTHONPATH="$(pwd)"   # Windows PowerShell

# Run in development mode
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Features

1. **New Job Type**: See [docs/ADDING_NEW_JOB.md](docs/ADDING_NEW_JOB.md)
2. **New API Endpoint**: Add to `backend/api/routes/`
3. **New Service**: Add to `src/services/`
4. **Testing**: Add tests to `tests/`

### Code Organization

- **backend/**: HTTP layer (FastAPI routes, schemas)
- **src/services/**: Business logic (service layer)
- **src/ai/router/**: Core AI logic (router, handlers, strategies)
- **src/errors/**: Error handling and custom exceptions
- **src/utils/**: Shared utilities

---

## 🤝 Integration Examples

### Python Client

```python
class ICCAgentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def create_session(self):
        response = requests.post(f"{self.base_url}/api/chat/sessions")
        self.session_id = response.json()["session_id"]
        return self.session_id
    
    def send_message(self, message, **kwargs):
        return requests.post(
            f"{self.base_url}/api/chat/message",
            json={"session_id": self.session_id, "message": message, **kwargs}
        ).json()
    
    def close_session(self):
        requests.delete(f"{self.base_url}/api/chat/sessions/{self.session_id}")

# Usage
client = ICCAgentClient()
client.create_session()
result = client.send_message("read customer data")
print(result["response"])
client.close_session()
```

### JavaScript/TypeScript

```typescript
class ICCAgentClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  
  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }
  
  async createSession(): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/chat/sessions`, {
      method: "POST"
    });
    const data = await response.json();
    this.sessionId = data.session_id;
    return this.sessionId;
  }
  
  async sendMessage(message: string, options?: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: this.sessionId,
        message,
        ...options
      })
    });
    return response.json();
  }
  
  async closeSession(): Promise<void> {
    await fetch(`${this.baseUrl}/api/chat/sessions/${this.sessionId}`, {
      method: "DELETE"
    });
  }
}

// Usage
const client = new ICCAgentClient();
await client.createSession();
const result = await client.sendMessage("read customer data");
console.log(result.response);
await client.closeSession();
```

---

## 🔍 Troubleshooting

### Backend Won't Start

```bash
# Check if Ollama is running
ollama list

# Check if port 8000 is available
netstat -an | grep 8000

# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip list | grep fastapi
```

### LLM Not Responding

```bash
# Verify Ollama models
ollama list
# Should show: qwen3:8b and qwen2.5-coder:7b

# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b",
  "prompt": "Hello"
}'

# Check backend logs
docker logs icc-backend
```

### Connection Issues

```bash
# Verify db_config.json is valid
python -c "import json; json.load(open('db_config.json'))"

# Test connections endpoint
curl http://localhost:8000/api/connections

# Check CORS settings if calling from browser
# Add your origin to CORS_ORIGINS environment variable
```

See [docs/TESTING.md](docs/TESTING.md) for more troubleshooting tips.

---

## 📊 Performance

- **Response Time**: 0.5-2s (with warm models)
- **Cold Start**: 5-10s (first request, model loading)
- **Memory**: ~2GB (with both models loaded)
- **Concurrency**: Handles multiple sessions concurrently
- **Model Persistence**: `keep_alive=3600s` keeps models in memory

### Optimization Tips

1. Keep Ollama models loaded (set `keep_alive` high)
2. Use singleton pattern (already implemented)
3. Pre-populate database metadata cache
4. Use connection pooling for database operations
5. Scale horizontally with Redis session storage

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **API Reference**: http://localhost:8000/docs
- **Issues**: Open an issue in the repository
- **Architecture Questions**: See [docs/ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md)

---

## ✨ Key Highlights

✅ **Production Ready** - FastAPI + Docker + Health checks  
✅ **Fast** - Singleton LLM agents, 0.5-2s responses  
✅ **Reliable** - 95%+ success rate with 7B-8B models  
✅ **Scalable** - Stateless API, pluggable session storage  
✅ **Well Documented** - Comprehensive docs in `docs/`  
✅ **Easy Integration** - REST API with OpenAPI spec  
✅ **Tested** - Automated test suite included  

**Built for developers who need reliable NL→SQL conversion without the complexity of agentic systems.**

