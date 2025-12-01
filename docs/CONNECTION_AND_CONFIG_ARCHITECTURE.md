# Connection Management & Configuration Architecture

## Overview

The ICC system has **distinct connection management strategies** and **two configuration domains**. This document clarifies the architecture to prevent confusion.

## Connection Management (3 Systems)

### 1. Static Connections (Fallback)
**File**: `src/utils/connections.py`  
**Purpose**: Hardcoded fallback when dynamic API is unavailable  
**Contains**: ~20 pre-configured connections with IDs

```python
CONNECTIONS = {
    "ORACLE_10": {
        "id": "4976629955435844",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@...",
        "user": "icc_test"
    },
    ...
}

def get_connection_id(connection_name: str) -> Optional[str]:
    # Returns ID from static dict
```

**Usage**:
- Fallback when API is down
- Development/testing without live API
- Quick lookup of known connections

### 2. Dynamic Connections (Runtime API)
**File**: `src/utils/connection_api_client.py`  
**Purpose**: Fetch live connections from ICC API at runtime  
**Endpoint**: `{base_url}/connection/list`

```python
class ICCAPIClient:
    async def fetch_connections(self) -> Dict[str, Dict[str, Any]]:
        # Fetches from API: /connection/list
        # Returns same format as static CONNECTIONS
        
    async def fetch_schemas(self, connection_id: str) -> List[str]:
        # Fetches schemas for a connection: /utility/connection/{id}
```

**Usage**:
- Production runtime (gets latest connections)
- Router's ConnectionManager uses this
- Populates memory.connections dynamically

**Flow**:
```
Router startup → ICCAPIClient.fetch_connections() → memory.connections
→ User asks for connection → Check memory.connections
→ Fallback to static CONNECTIONS if API failed
```

### 3. Config-Based Connections (UI Structure)
**File**: `src/utils/config_loader.py`  
**Config**: `db_config.json`  
**Purpose**: Hierarchical database structure for UI dropdowns

```json
{
  "connections": [
    {
      "name": "ORACLE_10",
      "label": "Oracle Database 10",
      "schemas": [
        {
          "name": "SALES",
          "tables": ["customers", "orders", ...]
        }
      ]
    }
  ]
}
```

```python
class ConfigLoader:
    def get_available_connections(self) -> List[str]
    def get_schemas_for_connection(connection: str) -> List[str]
    def get_tables_for_schema(connection: str, schema: str) -> List[str]
```

**Usage**:
- Dash UI dropdown population
- Table/schema navigation
- NOT for connection IDs (use static/dynamic for that)

## Configuration Domains (2 Systems)

### 1. AI Configuration (`src/ai/configs/`)

**Purpose**: Agent configuration (models, prompts, tools)  
**Scope**: LLM agents, toolkits, agent behavior

**Files**:
- `base_config.py` - Abstract base for all agent configs
- `model_config.py` - LLM model configuration (Ollama)
- `icc_config.py` - ICC agent assembly
- `prompts/prompts.py` - Agent prompts

**Not related to**:
- Database connections
- API endpoints
- Database structure

### 2. Utils Configuration (`src/utils/`)

**Purpose**: Runtime configuration (API endpoints, database structure)  
**Scope**: API clients, database metadata, system configuration

**Files**:
- `config.py` - API endpoints, auth config
- `config_loader.py` - Database structure from JSON
- `connections.py` - Static connection fallback
- `connection_api_client.py` - Dynamic connection fetching

## Correct Usage Patterns

### Getting a Connection ID

```python
# Option 1: From dynamic API (preferred in production)
from src.utils.connection_api_client import ICCAPIClient
client = ICCAPIClient(auth_headers=headers)
connections = await client.fetch_connections()
conn_id = connections["ORACLE_10"]["id"]

# Option 2: From static fallback (dev/testing)
from src.utils.connections import get_connection_id
conn_id = get_connection_id("ORACLE_10")

# Option 3: From router memory (already populated)
# memory.connections already has dynamic or static data
conn_id = memory.connections["ORACLE_10"]["id"]
```

### Getting Database Structure for UI

```python
# Use config_loader for UI dropdowns
from src.utils.config_loader import get_connections, get_schemas, get_tables

connections = get_connections()  # ["ORACLE_10", "MSSQL", ...]
schemas = get_schemas("ORACLE_10")  # ["SALES", "HR", ...]
tables = get_tables("ORACLE_10", "SALES")  # ["customers", "orders", ...]
```

### Getting API Endpoints

```python
# Use utils/config.py for API configuration
from src.utils.config import API_CONFIG, AUTH_CONFIG

base_url = API_CONFIG["api_base_url"]
token_endpoint = AUTH_CONFIG["token_endpoint"]
```

### Configuring AI Agent

```python
# Use ai/configs for agent configuration
from src.ai.configs.icc_config import ICCAgentConfig
from src.ai.configs.model_config import OllamaModelConfig

model_config = OllamaModelConfig(model_name="qwen3:1.7b")
agent_config = ICCAgentConfig(model_config=model_config)
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ICC Application                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌──────────────────┐         │
│  │   AI Configs    │         │  Utils Configs   │         │
│  │  (src/ai/       │         │  (src/utils/)    │         │
│  │   configs/)     │         │                  │         │
│  ├─────────────────┤         ├──────────────────┤         │
│  │ • base_config   │         │ • config.py      │         │
│  │ • model_config  │         │   (API endpoints)│         │
│  │ • icc_config    │         │ • config_loader  │         │
│  │ • prompts       │         │   (DB structure) │         │
│  └─────────────────┘         └──────────────────┘         │
│                                                             │
│  Connection Management (3 systems):                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. Static (connections.py) - Fallback               │  │
│  │    ├─ Hardcoded connection IDs                      │  │
│  │    └─ Used when API unavailable                     │  │
│  │                                                       │  │
│  │ 2. Dynamic (connection_api_client.py) - Runtime     │  │
│  │    ├─ Fetches from /connection/list                 │  │
│  │    ├─ Fetches schemas from /utility/connection/{id} │  │
│  │    └─ Populates router memory                       │  │
│  │                                                       │  │
│  │ 3. Config (config_loader.py) - UI Structure         │  │
│  │    ├─ Loads from db_config.json                     │  │
│  │    ├─ Connection/Schema/Table hierarchy             │  │
│  │    └─ For UI dropdowns only                         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Distinctions

| Aspect | Static | Dynamic | Config-based |
|--------|--------|---------|--------------|
| **Source** | Python dict | ICC API | JSON file |
| **Contains** | Connection IDs | Connection IDs + metadata | Structure only |
| **Runtime** | Always available | Requires API | Always available |
| **Purpose** | Fallback lookup | Production runtime | UI navigation |
| **Updates** | Code changes only | Every API call | File changes only |
| **Used by** | Fallback logic | Router, agents | Dash UI |

## Why This Architecture?

### Separation of Concerns
- **AI configs**: Agent behavior (models, prompts)
- **Utils configs**: System integration (APIs, DBs)

### Redundancy for Reliability
- **Static**: Works offline, development
- **Dynamic**: Latest connections, production
- **Config**: Curated structure for UI

### SOLID Compliance
- **SRP**: Each config system has one responsibility
- **OCP**: Easy to extend with new connections
- **DIP**: Router depends on abstractions (memory.connections)

## Migration Notes

**Do NOT**:
- ❌ Mix AI agent config with API endpoint config
- ❌ Use config_loader.py for connection IDs
- ❌ Assume static connections are up-to-date

**Do**:
- ✅ Use dynamic API connections in production
- ✅ Fall back to static for development
- ✅ Use config_loader for UI hierarchy only
- ✅ Keep AI configs separate from utils configs

## Summary

1. **Two config domains**: AI (agent behavior) vs Utils (system integration)
2. **Three connection systems**: Static (fallback), Dynamic (runtime), Config (UI structure)
3. **Clear separation**: Each system has distinct purpose and usage
4. **No confusion**: Static connections.py ≠ Dynamic API ≠ Config JSON

**Last Updated**: 2025-12-01
