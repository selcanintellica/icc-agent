# ICC Agent - Intelligent Database Assistant

## Overview

ICC Agent is an AI-powered database assistant that helps users create, execute, and manage SQL queries through natural conversation. Built with a **staged router architecture** optimized for small language models (7B-8B parameters), it provides reliable SQL generation and database operations without complex reasoning loops.

### Key Features

- 🤖 **Dual SQL Creation** - Generate SQL from natural language OR provide your own SQL directly
- 🎯 **Staged Router Architecture** - Purpose-built workflow optimized for small LLMs
- 🔄 **Smart SQL Agent** - Context-aware SQL generation using table definitions
- 🔌 **Database Operations** - Execute queries, write results, send email reports
- 🌐 **Web Interface** - Clean Dash-based chat interface with database configuration
- 🔐 **Secure Authentication** - Token-based API authentication
- 📊 **Persistent Memory** - Conversation state maintained across turns
- 🎭 **Mock Mode** - Built-in mock data for development without API dependencies

## Architecture

The system uses a **staged conversation flow** with 10 distinct stages:

```
START → ASK_SQL_METHOD → [Generate Path OR Provide Path] → EXECUTE_SQL → SHOW_RESULTS → NEED_WRITE_OR_EMAIL → DONE
```

### Specialized Components

- **SQL Agent** (7B model, temp=0.1) - Generates SQL from natural language using table definitions
- **Job Agent** (8B model, temp=0.3) - Extracts parameters for job creation
- **Router** - Orchestrates conversation flow through stages
- **Config Loader** - Manages database connection hierarchy from JSON
- **Table API Client** - Fetches table definitions (supports mock mode)
- **Connection Manager** - Maps connection names to IDs for API calls

## How It Works

### Staged Router Pattern

Traditional AI agents use ReAct (Reasoning + Acting) patterns that require large models (70B+) for reliable multi-step reasoning. Our **Staged Router** architecture is specifically designed for small models (7B-8B parameters) by eliminating complex reasoning loops.

### 10-Stage Conversation Flow

**1. START** - Initial greeting and connection selection

**2. ASK_SQL_METHOD** - User chooses their preferred path:
   - Generate SQL from natural language (agent creates query)
   - Provide SQL directly (user writes query)

**3A. NEED_NATURAL_LANGUAGE** (Generation Path)
   - User describes what they want in natural language
   - SQL Agent fetches table definitions via API (or mock data)
   - Agent generates SQL query with context

**3B. NEED_USER_SQL** (Direct Path)
   - User provides their own SQL query
   - No agent generation needed

**4A. CONFIRM_GENERATED_SQL** - Review agent-generated SQL before execution

**4B. CONFIRM_USER_SQL** - Review user-provided SQL before execution

**5. EXECUTE_SQL** - Create read job and execute query via API

**6. SHOW_RESULTS** - Display query results and ask what's next

**7. NEED_WRITE_OR_EMAIL** - User chooses follow-up action:
   - Write results to database
   - Send results via email
   - Done

**8. DONE** - Conversation complete

### Why This Works for Small LLMs

✅ **Single-task focus** - Each stage has one clear purpose  
✅ **No reasoning loops** - Router handles all flow logic  
✅ **Optimized temperatures** - SQL generation (0.1), parameter extraction (0.3)  
✅ **Context management** - Table definitions loaded on-demand  
✅ **User control** - Choice between agent generation and direct SQL  
✅ **Deterministic transitions** - Clear success/failure paths  

This architecture allows 7B-8B parameter models to reliably:
- Generate correct SQL from natural language using table schemas
- Execute queries across multiple database types
- Write results to target databases
- Send email reports with query results

## Folder Structure

```
src/
  ai/
    router/              # Staged router components (10-stage flow)
      memory.py          # Stage definitions and conversation state
      sql_agent.py       # Natural language to SQL generation
      job_agent.py       # Parameter extraction for jobs
      router.py          # Main orchestrator (stage transitions)
    toolkits/            # Tool implementations
      icc_toolkit.py     # Database and email operations
  models/                # Pydantic models for API requests
  repositories/          # API communication layer
  payload_builders/      # Request builders for job creation
  utils/
    config_loader.py     # JSON-based database configuration
    table_api_client.py  # Table definition fetcher (mock mode support)
    connections.py       # Connection name to ID mapping
    mock_table_data.py   # Mock table definitions for development
    auth.py              # Token-based authentication
db_config.json           # Database hierarchy (connections/schemas/tables)
docs/                    # Detailed documentation
```

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) with models:
  - `qwen3:8b` (main agent, 8B parameters)
  - `qwen2.5-coder:7b` (SQL generation, 7B parameters)
- Database API access (or use mock mode for development)

### Installation

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd ICC_try
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements_app.txt
   ```

3. **Install Ollama and pull the models:**
   ```sh
   # Install Ollama from https://ollama.ai
   ollama pull qwen3:8b
   ollama pull qwen2.5-coder:7b
   ```

4. **Configure database hierarchy:**
   
   Edit `db_config.json` to define your database connections, schemas, and tables:
   ```json
   {
     "connections": [
       {
         "name": "ORACLE_10",
         "schemas": [
           {
             "name": "SALES",
             "tables": ["customers", "orders", "order_items", "products"]
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

5. **Configure environment:**
   ```sh
   # Copy example env file
   cp .env.example .env
   
   # Edit .env with your settings:
   # - Model names (MODEL_NAME, SQL_MODEL_NAME)
   # - API endpoints (BASE_URL, TABLE_API_BASE_URL)
   # - Authentication (TOKEN_ENDPOINT, AUTH_USERPASS)
   # - Mock mode (TABLE_API_MOCK=true for development without API)
   ```

## Usage

### Running the Chat Interface

```sh
python app.py
```

Then open your browser to: http://localhost:8050

### Example Conversation (Agent Generates SQL)

```
Agent: Would you like me to generate SQL or provide your own? (generate/provide)
User: generate
Agent: What would you like to query?
User: Get all customers from USA
Agent: [Fetches table definitions for SALES.customers]
Agent: [Generates SQL] → SELECT * FROM customers WHERE country = 'USA'
Agent: Shall I execute this query? (yes/no)
User: yes
Agent: [Executes query via API] ✅ Query executed successfully! Found 150 rows.
Agent: What would you like to do next? (write/email/done)
User: done
```

### Example Conversation (User Provides SQL)

```
Agent: Would you like me to generate SQL or provide your own? (generate/provide)
User: provide
Agent: Please provide your SQL query:
User: SELECT * FROM employees WHERE salary > 50000
Agent: Review your SQL:
      SELECT * FROM employees WHERE salary > 50000
      Should I execute this? (yes/no)
User: yes
Agent: [Executes query via API] ✅ Query executed successfully!
```

### Mock Mode (Development)

Set `TABLE_API_MOCK=true` in `.env` to use mock table definitions without API access:

```env
TABLE_API_MOCK=true
```

Mock data includes sample tables:
- ORACLE_10.SALES: customers, orders, order_items, products
- ORACLE_10.HR: employees, departments
- POSTGRE_11.PUBLIC: users

### Configuration

**Connection Management:**
- Connections defined in `db_config.json` (name, schemas, tables hierarchy)
- Connection IDs mapped in `src/utils/connections.py` (18 connections)
- User selects connection in UI dropdowns (via `config_loader.py`)
- Connection names automatically converted to IDs for API calls

**Model Configuration:**
- Main agent: `qwen3:8b` (temperature=0.3) - Parameter extraction and orchestration
- SQL agent: `qwen2.5-coder:7b` (temperature=0.1) - SQL generation (more precise)
- Both models run via Ollama (localhost:11434)

**Authentication:**
- Token-based authentication configured in `.env`
- Set `TOKEN_ENDPOINT` and `AUTH_USERPASS` (base64 encoded username:password)
- Tokens automatically included in all API requests

## Documentation

Detailed documentation is available in the `docs/` folder:

- **[SQL Agent Guide](docs/SQL_AGENT.md)** - Natural language to SQL conversion
- **[Job Agent Guide](docs/JOB_AGENT.md)** - Parameter extraction and job creation
- **[Router Architecture](docs/ROUTER_ARCHITECTURE.md)** - Complete 10-stage system design
- **[Visual Guide](docs/VISUAL_GUIDE.md)** - Flow diagrams and conversation paths

Technical references:
- [DB Config Migration](docs/DB_CONFIG_MIGRATION.md) - JSON configuration system
- [Connection ID Implementation](docs/CONNECTION_ID_IMPLEMENTATION.md) - API integration
- [Mock Table API](docs/MOCK_TABLE_API.md) - Development without API
- [Updated State Flow](docs/UPDATED_STATE_FLOW.md) - 10-stage implementation details

## Development

### Why Staged Router for Small LLMs?

Traditional ReAct agents require large models (70B+) for reliable multi-step reasoning. Our staged approach is optimized for 7B-8B models:

**Problems with ReAct for Small LLMs:**
- Complex reasoning loops fail or loop infinitely
- Tool selection is ambiguous without strong reasoning
- Multi-step planning overwhelms smaller models

**Staged Router Solution:**
- ✅ Each stage has ONE clear purpose (no ambiguity)
- ✅ Router handles flow logic (no LLM reasoning about transitions)
- ✅ Specialized agents with optimized temperatures
- ✅ Deterministic success/failure paths
- ✅ Memory-driven context (persistent state across turns)

### Key Components

- `app.py` - Dash web interface with database selection
- `db_config.json` - Database hierarchy configuration
- `src/ai/router/router.py` - Main orchestrator (10-stage flow)
- `src/ai/router/memory.py` - Stage definitions and conversation state
- `src/ai/router/sql_agent.py` - Natural language to SQL generation
- `src/ai/router/job_agent.py` - Parameter extraction for jobs
- `src/utils/config_loader.py` - JSON configuration reader
- `src/utils/table_api_client.py` - Table definition fetcher
- `src/utils/connections.py` - Connection name to ID mapping
- `src/utils/mock_table_data.py` - Mock data for development

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes.

## License

See the `LICENSE` file for details.

