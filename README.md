# ICC Agent - Staged Router for Small LLMs

## Overview

ICC Agent is an AI-powered SQL query generator and executor optimized for small language models (1.5B-3B parameters). It uses a **staged conversation router** architecture that breaks down complex tasks into focused stages, allowing small LLMs to perform reliably without the complexity of traditional ReAct agents.

### Key Features

- 🎯 **Staged Router Architecture** - Purpose-built for small LLMs (qwen3:1.7b)
- 🔄 **Natural Language to SQL** - Convert natural language queries to SQL
- 🔌 **Database Operations** - Execute queries, write results, send email reports
- 🌐 **Web Interface** - Simple Dash-based chat interface
- 🔐 **OAuth Authentication** - Keycloak/OAuth integration for API access
- 📊 **Memory Management** - Persistent conversation state across turns

## Architecture

The system uses a **staged conversation flow** instead of traditional agent reasoning:

```
START → NEED_QUERY → HAVE_SQL → SHOW_RESULTS → NEED_WRITE_OR_EMAIL → DONE
```

Each stage has a specialized agent:
- **SQL Agent** (temp=0.1) - Generates SQL from natural language
- **Job Agent** (temp=0.3) - Extracts parameters and manages tool execution
- **Router** - Orchestrates conversation flow through stages

## Folder Structure

```
src/
  ai/
    router/            # Staged router components
      memory.py        # Conversation state management
      sql_agent.py     # Natural language to SQL
      job_agent.py     # Parameter extraction
      router.py        # Main orchestrator
    toolkits/          # Tool implementations
      icc_toolkit.py   # Database and email operations
  models/              # Pydantic models for API requests
  repositories/        # API communication layer
  payload_builders/    # Request builders
  utils/               # Configuration and authentication
docs/                  # Additional documentation
```

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) with qwen3:1.7b model
- Database API credentials (for production use)

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

3. **Install Ollama and pull the model:**
   ```sh
   # Install Ollama from https://ollama.ai
   ollama pull qwen3:1.7b
   ```

4. **Configure environment:**
   ```sh
   # Copy example env file
   cp .env.example .env
   
   # Edit .env with your credentials:
   # - API endpoints
   # - Authentication credentials
   # - Database connection (default: oracle_10)
   ```

## Usage

### Running the Chat Interface

```sh
python app.py
```

Then open your browser to: http://localhost:8050

### Example Queries

```
User: Get customers from USA
Agent: [Generates SQL] → SELECT * FROM customers WHERE country = 'USA'
Agent: Shall I execute it?
User: yes
Agent: [Executes query] ✅ Query executed successfully!
Agent: What would you like to do next? (write/email/done)
```

### Configuration

**Connection Management:**
- Default connection is set in `Memory.connection` (currently: "oracle_10")
- In production, set this from UI selection before conversation starts
- LLM does not ask for connection - it's provided externally

**Model Configuration:**
- All agents use `qwen3:1.7b` via Ollama (localhost:11434)
- SQL Agent: temperature=0.1 (more deterministic)
- Job Agent: temperature=0.3 (more flexible)

**Authentication:**
- Configure in `.env` file
- Supports Keycloak/OAuth token-based auth
- Tokens are automatically included in API requests

## Documentation

Additional documentation is available in the `docs/` folder:

- [Staged Router Architecture](docs/README_STAGED_ROUTER.md)
- [Router Implementation](docs/ROUTER_README.md)
- [Visual Guide](docs/VISUAL_GUIDE.md)
- [Chat Interface](docs/CHAT_INTERFACE_README.md)
- [Quick Start Guide](docs/QUICKSTART.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)

## Development

### Project Structure

The staged router approach was chosen specifically for small LLMs:
- **Why Not ReAct?** Complex reasoning loops are unreliable with small models
- **Staged Approach** Each stage has a clear, focused task
- **Memory-Driven** Context is maintained in a dataclass, not LLM reasoning

### Key Components

- `app.py` - Dash web interface
- `src/ai/router/router.py` - Main conversation orchestrator
- `src/ai/router/memory.py` - Conversation state
- `src/ai/toolkits/icc_toolkit.py` - Database operations
- `src/utils/auth.py` - Authentication utilities

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes.

## License

See the `LICENSE` file for details.

