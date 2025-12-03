# ICC Agent - Natural Language Database Interface

## Overview

ICC Agent is a conversational AI system that translates natural language requests into database operations. Users describe what they want in plain English, and the system executes the appropriate database jobs (ReadSQL, WriteData, SendEmail, CompareSQL).

Built with a **handler-based architecture** using specialized LLM agents (7B-8B parameters), it provides reliable parameter extraction and SQL generation optimized for production workloads.

### Key Features

- 💬 **Natural Language Interface** - Describe database operations in plain English
- 🎯 **Handler Architecture** - Specialized handlers for each job type (ReadSQL, WriteData, SendEmail, CompareSQL)
- 🤖 **Dual LLM Agents** - SQL generation (qwen2.5-coder:7b) + parameter extraction (qwen3:8b)
- 🔄 **Flexible SQL Options** - Generate SQL from natural language OR provide your own
- 📊 **Complete Workflows** - Query → Write → Email in single conversation
- 🌐 **Web Interface** - Dash-based chat with dynamic dropdowns for connections/schemas
- 🔐 **API Integration** - Full integration with database and table metadata APIs
- ⚡ **Singleton Pattern** - LLM instances stay loaded in memory for fast responses (~0.5-2s)
- 📋 **Smart Parameter Extraction** - Dropdown optimization (FETCH vs ASK) for better UX

## Architecture

The system uses a **handler-based router architecture** with specialized stage handlers for each job type:

```
User Input → Router Orchestrator → Stage Handler → LLM Agents → Parameter Validator → Execute Job
                    ↓
    ┌───────────────┼───────────────┬───────────────┬───────────────┐
    ▼               ▼               ▼               ▼               ▼
ReadSQLHandler  WriteDataHandler SendEmailHandler CompareSQLHandler  RouterHandler
(both agents)   (job agent)      (job agent)      (both agents)      (job agent)
```

### Core Components

- **Router Orchestrator** - Singleton orchestrator that routes stages to appropriate handlers
- **Stage Handlers** - Specialized handlers manage stage transitions for each job type
## How It Works

### Handler-Based Router Pattern

Each job type (ReadSQL, WriteData, SendEmail, CompareSQL) has a dedicated handler that manages its conversation stages. The router orchestrator dispatches work to the appropriate handler based on the current stage.

**Example: ReadSQL Flow**

```
User: "Get customers from USA"
  ↓
Router → ReadSQLHandler (ASK_SQL_METHOD stage)
  ↓
Handler asks: "Generate SQL or provide your own?"
  ↓
User: "generate"
  ↓
Router → ReadSQLHandler (NEED_NATURAL_LANGUAGE stage)
  ↓
SQL Agent generates: SELECT * FROM customers WHERE country = 'USA'
  ↓
Router → ReadSQLHandler (CONFIRM_GENERATED_SQL stage)
  ↓
User: "yes"
  ↓
Router → ReadSQLHandler (EXECUTE_SQL stage)
  ↓
Job Agent extracts parameters → Validator checks completeness
  ↓
Execute job via API → Show results
  ↓
Router → ReadSQLHandler (NEED_WRITE_OR_EMAIL stage)
  ↓
User: "write to database"
  ↓
Router → WriteDataHandler (NEED_WRITE_OR_EMAIL stage)
  ↓
[WriteData flow continues...]
```

### Key Architecture Benefits

✅ **Separation of Concerns** - Each handler manages its own stages independently  
✅ **Singleton LLM Agents** - Single instances stay loaded, keep_alive="3600s" prevents reload  
✅ **Smart Parameter Extraction** - FETCH dropdowns when available, ASK only when needed  
✅ **Optimized for Small LLMs** - Temperature=0.1 for deterministic outputs  
✅ **Flexible Workflows** - ReadSQL → WriteData → SendEmail in single conversation  
✅ **Production Ready** - Handles errors, validates parameters, confirms actions  

This architecture allows 7B-8B parameter models to:
- Generate accurate SQL from natural language with table schema context
- Extract parameters from conversational input while filtering confirmations
- Execute complete multi-step workflows (query → write → email)
## Project Structure

```
src/
  ai/
    router/
      router.py                  # RouterOrchestrator (singleton pattern)
      memory.py                  # Memory state and Stage enum
      sql_agent.py               # SQL generation from natural language
      job_agent.py               # Parameter extraction from user input
      stage_handlers/
        base_handler.py          # BaseStageHandler abstract class
        readsql_handler.py       # ReadSQL workflow (8 stages)
        writedata_handler.py     # WriteData workflow (1 stage)
        sendemail_handler.py     # SendEmail workflow (3 stages)
        comparesql_handler.py    # CompareSQL workflow (14 stages)
        router_handler.py        # Initial routing (2 stages)
      validators/
        parameter_validator.py   # Parameter completeness checker
    toolkits/
      icc_toolkit.py             # Job execution functions
  models/                        # Pydantic request/response models
  repositories/                  # API communication layer
  payload_builders/              # Wire protocol builders
  utils/
    connection_api_client.py     # Fetch connections/schemas from API
    table_api_client.py          # Fetch table schemas (with mock mode)
    auth.py                      # Token-based authentication
    config.py                    # Environment configuration
app.py                           # Dash web interface
db_config.json                   # Database configuration (deprecated)
docs/                            # Comprehensive documentation
  ARCHITECTURE.md                # System architecture overview
### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) with models:
  - `qwen3:8b` (job agent - parameter extraction)
  - `qwen2.5-coder:7b` (SQL agent - SQL generation)
- API access for job execution and metadatavelopment
    auth.py              # Token-based authentication
db_config.json           # Database hierarchy (connections/schemas/tables)
docs/                    # Detailed documentation
```

## Setup

### Prerequisites

2. **Install dependencies:**
   ```sh
   pip install -r requirements_app.txt
   ```

3. **Install Ollama and pull models:**
   ```sh
   # Install Ollama from https://ollama.ai
   ollama pull qwen3:8b
   ollama pull qwen2.5-coder:7b
   ```

4. **Configure environment variables:**
   
   Create a `.env` file with:
   ```env
   # LLM Configuration
   MODEL_NAME=qwen3:8b              # Job agent model
   SQL_MODEL_NAME=qwen2.5-coder:7b  # SQL agent model
   OLLAMA_BASE_URL=http://localhost:11434
   
   # API Configuration
   BASE_URL=https://your-api-endpoint.com
   TOKEN_ENDPOINT=https://your-auth-endpoint.com/token
   AUTH_USERPASS=base64_encoded_username:password
   
   # Table API (for schema fetching)
   TABLE_API_BASE_URL=https://your-table-api.com
   TABLE_API_MOCK=false  # Set to true for mock mode
   ```
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

## Usage

### Start the Application

```sh
python app.py
```

Open browser to: **http://localhost:8050**

### Example Conversations

**ReadSQL → WriteData Flow:**
```
User: "Get all customers from USA"
Agent: "Would you like me to generate SQL or provide your own? (generate/provide)"
User: "generate"
Agent: [Generates SQL with table schema context]
      "Here's the SQL: SELECT * FROM customers WHERE country = 'USA'
       Shall I execute? (yes/no)"
User: "yes"
Agent: [Executes via API] "✅ Query completed! Found 150 rows.
       What would you like to do? (write/email/done)"
User: "write"
Agent: "Which schema? (dropdown appears)"
User: [Selects schema]
Agent: "Table name?"
User: "usa_customers"
Agent: [Writes data] "✅ Data written to usa_customers!"
```

**Natural Language → Full Workflow:**
```
User: "Pull customer orders and email them to sales team"
Agent: [Guides through ReadSQL → confirms parameters → executes]
Agent: "What would you like to do? (write/email/done)"
User: "email"
Agent: [Auto-generates email query from result table]
      "Query: SELECT * FROM schema.temp_table
       Should I send email with this data? (yes/no)"
User: "yes"
Agent: [Collects email parameters → sends] "✅ Email sent!"
```

**CompareSQL (Two Queries):**
```
User: "compare sales"
Agent: [Guides through first SQL → second SQL → column mapping → reporting type]
Agent: "✅ Comparison complete! Results saved to comparison_table."
```

### Configuration

**LLM Models:**
- Job Agent: `qwen3:8b` (temperature=0.1, num_predict=4096, timeout=30s)
- SQL Agent: `qwen2.5-coder:7b` (temperature=0.1, num_predict=2048)
- Both use `keep_alive="3600s"` for fast responses (~0.5-2s)

**Connection Management:**
- Connections fetched dynamically from API via `connection_api_client.py`
- Dropdowns populated on-demand (FETCH optimization)
- Connection selection triggers schema dropdown

**Mock Mode (Development):**
Set `TABLE_API_MOCK=true` to use built-in mock table schemas without API:
```env
TABLE_API_MOCK=true
```folder:

- **[SQL Agent Guide](docs/SQL_AGENT.md)** - Natural language to SQL conversion
- **[Job Agent Guide](docs/JOB_AGENT.md)** - Parameter extraction and job creation
## Documentation

Comprehensive documentation in the `docs/` folder:

### Main Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture overview with diagrams
- **[TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)** - Deep dive into implementation details
- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** - Development guide with code examples
- **[ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md)** - Why semi-static router over agentic systems

### Additional Documentation

- [SQL_AGENT.md](docs/SQL_AGENT.md) - SQL generation from natural language
- [JOB_AGENT.md](docs/JOB_AGENT.md) - Parameter extraction logic
- [ROUTER_ARCHITECTURE.md](docs/ROUTER_ARCHITECTURE.md) - Router orchestrator patterns
## Development

### Architecture Principles

**Handler-Based Design:**
- Each job type has a dedicated handler (ReadSQL, WriteData, SendEmail, CompareSQL)
- Handlers manage their own stages independently
- Router orchestrator dispatches based on current stage
- Clean separation of concerns following SOLID principles

**Singleton Pattern for Performance:**
- Single LLM instances shared across all requests
- `keep_alive="3600s"` keeps models loaded in Ollama
- Response times: ~0.5-2s (vs 5-10s without singleton)
- Check with `ollama ps` - timer resets but model stays loaded

**Optimized for Small LLMs (7B-8B):**
- Temperature=0.1 for deterministic, consistent outputs
- Specialized agents (SQL generation vs parameter extraction)
- No complex reasoning loops - handlers manage flow logic
- Context-aware prompts with table schemas and current parameters

### Adding a New Handler

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for step-by-step instructions on:
1. Creating a new stage handler class
2. Defining managed stages
3. Implementing stage transition logic
4. Registering with router orchestrator
5. Writing tests

### Testing

```sh
# Run all tests
pytest

# Run specific test file
pytest tests/test_router.py

# Run with coverage
pytest --cov=src
```

## Performance

**Response Times:**
- With singleton + keep_alive: **0.5-2 seconds** per request
- Without singleton: 5-10 seconds (model reload overhead)

**LLM Configuration:**
- Both agents use `temperature=0.1` for consistency
- `num_predict`: 4096 (job agent), 2048 (SQL agent)
- `keep_alive="3600s"` prevents model unload
- `timeout=30.0` for job agent operations

**Monitoring:**
```sh
# Check loaded models
ollama ps

# Expected output (singleton working):
# NAME              ID          SIZE    GPU    EXPIRES
# qwen3:8b          abc123...   5.5 GB  100%   59 minutes from now
# qwen2.5-coder:7b  def456...   4.7 GB  100%   59 minutes from now
```

## Troubleshooting

**Slow responses?**
- Check `ollama ps` - models should stay loaded between requests
- Verify singleton pattern: Look for "🏗️ Creating singleton" logs only once
- Ensure `keep_alive="3600s"` is configured

**SQL generation errors?**
- Check table API connectivity or enable mock mode
- Verify schema/table names in user input
- Review SQL agent logs for API errors

**Parameter extraction issues?**
- Check job agent is filtering confirmation words correctly
- Verify dropdown optimization (FETCH vs ASK) is working
- Review parameter validator logic

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for detailed debugging steps.

## Contributing

Contributions welcome! Please:
1. Review architecture documentation before major changes
2. Follow existing code patterns (handlers, singleton, validators)
3. Add tests for new functionality
4. Update documentation for significant changes

## License

See the `LICENSE` file for details.

