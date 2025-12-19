# ICC Agent - Conversational Database Operations

> Transform natural language into database operations through an intelligent conversational interface

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Required-green.svg)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What is ICC Agent?

ICC Agent is a conversational AI system that enables users to perform complex database operations using natural language. Instead of writing SQL queries or navigating multiple database tools, users simply describe what they want, and the system handles the technical details.

### Key Features

- **Natural Language to SQL**: Generate SQL queries from plain English descriptions
- **Data Operations**: Read, write, compare, and email database data
- **Visual Interface**: Web-based UI with dropdowns and column mapping
- **Safety First**: Review and confirm operations before execution
- **Job Management**: Organize jobs into folders with full audit trail

### Perfect For

- **Business Analysts**: Access data without SQL knowledge
- **Data Engineers**: Automate repetitive data operations
- **QA Engineers**: Validate data transformations quickly
- **Anyone**: Who needs to work with databases efficiently

## Quick Demo

```
You: "Read customer data from the sales database"
  ↓
Agent: Generates SQL query automatically
  ↓
You: Review and name the job
  ↓
Agent: Executes and saves results
```

**Time Savings**: Traditional SQL queries (30-60 min) → ICC Agent (5 min)

## Table of Contents

- [Quick Start](#quick-start)
- [Core Capabilities](#core-capabilities)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Quick Start

### Prerequisites

1. **Ollama** (Required for AI models)
   ```bash
   # Install from https://ollama.ai

   # Pull required models
   ollama pull qwen3:8b
   ollama pull qwen2.5-coder:7b

   # Verify installation
   ollama list
   ```

2. **Python 3.11+**

3. **ICC API Access** (Backend for job execution)

### Installation

#### Option A: Using uv (Recommended - Faster)

```bash
# Clone repository
git clone <repository-url>
cd icc-agent

# Install uv if not already installed
# https://github.com/astral-sh/uv
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Sync dependencies (creates .venv automatically)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your ICC API credentials

# Run application
uv run app.py
```

#### Option B: Using pip (Traditional)

```bash
# Clone repository
git clone <repository-url>
cd icc-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH="$(pwd)"  # Windows PowerShell

# Configure environment
cp .env.example .env
# Edit .env with your ICC API credentials

# Run application
python app.py
```

Application will be available at `http://localhost:8050`

## Core Capabilities

### 1. ReadSQL - Query Database

Generate and execute SQL SELECT queries from natural language.

**Use Case**: "Get all customers from California who made purchases in Q4 2024"

**Features**:
- Natural language to SQL conversion
- Query preview before execution
- Option to save results to new table
- Row count tracking

**Time Savings**: 30 minutes → 5 minutes

### 2. WriteData - Load Data

Write data to database tables with flexible load strategies.

**Use Case**: Load CSV data into staging table with truncate strategy

**Features**:
- Schema and table selection via dropdown
- Drop, truncate, or append modes
- Validation before execution
- Optional row count tracking

**Time Savings**: 30 minutes → 5 minutes

### 3. SendEmail - Automated Notifications

Send emails with query results as attachments.

**Use Case**: Daily sales summary report to stakeholders

**Features**:
- Attach query results
- Multiple recipients (To, CC)
- Custom subject and body
- Email format validation

**Time Savings**: Eliminates manual reporting tasks

### 4. CompareSQL - Data Validation

Compare results of two SQL queries with detailed diff reporting.

**Use Case**: Validate data migration from source to target

**Features**:
- Visual column mapping interface
- Multiple comparison modes (identical, difference, unique records)
- Detailed difference reporting
- Saves comparison results to database

**Time Savings**: 2 hours → 15 minutes

## Architecture

### High-Level Overview

```
┌─────────────────────┐
│   User Browser      │
└──────────┬──────────┘
           │ HTTP (Port 8050)
┌──────────▼──────────┐
│  Dash Web UI        │
│  • Chat Interface   │
│  • Dropdowns        │
│  • Column Mapping   │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Service Layer      │
│  • SessionManager   │
│  • AuthService      │
│  • DropdownHandler  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Router FSM         │
│  • Stage Handlers   │
│  • Memory Manager   │
│  • Strategy Pattern │
└─────┬────────┬──────┘
      │        │
┌─────▼──┐  ┌─▼────────┐
│ LLM    │  │ ICC API  │
│ Agents │  │ Client   │
│ (Ollama)│  │          │
└────────┘  └──────────┘
```

### Key Design Patterns

- **Finite State Machine (FSM)**: Deterministic conversation flow
- **Strategy Pattern**: Stage-specific handling
- **Singleton Pattern**: LLM agents stay loaded for fast responses
- **Service Layer**: Separation of business logic from UI
- **Repository Pattern**: Abstract data access

### Why This Architecture?

Traditional agentic systems (LangChain, AutoGPT) give LLMs full autonomy, leading to:
- ❌ Unpredictable behavior with small models
- ❌ Expensive operations (5-15 LLM calls per task)
- ❌ Hard to debug and test

Our **FSM-based approach**:
- ✅ Predictable and reliable (95%+ success rate)
- ✅ Fast responses (1-2s with warm models)
- ✅ Works with 7B-8B models (cost-effective)
- ✅ Easy to test and extend

See [docs/HIGH_LEVEL_ARCHITECTURE.md](docs/HIGH_LEVEL_ARCHITECTURE.md) for details.

## Installation

### Option 1: Direct Python (Development)

See [Quick Start](#quick-start) section above.

### Option 2: Docker (Production)

```bash
# Build image
docker build -t icc-agent:latest .

# Run container
docker run -d \
  --name icc-agent \
  -p 8050:8050 \
  --env-file .env \
  --restart unless-stopped \
  icc-agent:latest

# Check logs
docker logs -f icc-agent
```

### Option 3: Docker Compose

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

See [docs/DEVOPS_GUIDE.md](docs/DEVOPS_GUIDE.md) for detailed deployment instructions.

## Configuration

### Environment Variables

Create `.env` file with the following:

```bash
# ICC API Configuration
ICC_API_BASE_URL=https://your-icc-api.com
ICC_USERNAME=your_username
ICC_PASSWORD=your_password

# LLM Models (optional, defaults shown)
MODEL_NAME=qwen3:8b              # Job agent
SQL_MODEL_NAME=qwen2.5-coder:7b  # SQL agent

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8050

# Logging (optional)
LOG_LEVEL=INFO
ENABLE_PROMPT_LOGGING=false
PROMPT_LOG_DIR=prompt_logs
```

See `.env.example` for full configuration options.

## Usage Examples

### Example 1: Ad-Hoc Query

```
1. Open http://localhost:8050
2. Select connection: "ORACLE_PROD"
3. Select schema: "SALES"
4. Type: "Get all customers who bought laptops in 2024"
5. Agent generates SQL
6. Review query
7. Name job: "laptop_customers_2024"
8. Choose to save results: Yes
9. Confirm execution
10. View results in saved table
```

### Example 2: Data Comparison

```
1. Select job type: "CompareSQL"
2. Provide first SQL (source system)
3. Provide second SQL (target system)
4. Map columns visually
5. Select reporting type: "onlyDifference"
6. Name job: "migration_validation"
7. Confirm and execute
8. Review differences in results table
```

### Example 3: Automated Email Report

```
1. Select job type: "SendEmail"
2. Describe report: "Daily sales summary"
3. Agent generates SQL
4. Enter recipient: "manager@company.com"
5. Subject: "Daily Sales Report - Dec 19"
6. Body: "Please find attached..."
7. Confirm and send
8. Recipients receive automated email with results
```

## Documentation

Comprehensive documentation in `docs/` folder:

| Document | Audience | Description |
|----------|----------|-------------|
| [DEVOPS_GUIDE.md](docs/DEVOPS_GUIDE.md) | DevOps | Deployment, monitoring, maintenance |
| [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Developers | Architecture, patterns, development |
| [PRODUCT_OWNER_GUIDE.md](docs/PRODUCT_OWNER_GUIDE.md) | Product Owners | Features, roadmap, business value |
| [HIGH_LEVEL_ARCHITECTURE.md](docs/HIGH_LEVEL_ARCHITECTURE.md) | Technical | System design and components |
| [LOW_LEVEL_ARCHITECTURE.md](docs/LOW_LEVEL_ARCHITECTURE.md) | Technical | Implementation details |

## Troubleshooting

### Application Won't Start

```bash
# Check Ollama is running
ollama list

# Check port availability
netstat -an | grep 8050  # Linux/Mac
netstat -an | findstr 8050  # Windows

# Check Python version
python --version  # Should be 3.11+

# If using uv
uv sync  # Re-sync dependencies
uv run app.py

# If using pip
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH="$(pwd)"  # Windows
python app.py
```

### LLM Not Responding

```bash
# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b",
  "prompt": "Hello",
  "stream": false
}'

# Restart Ollama
ollama serve

# Re-pull models
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
```

### ICC API Connection Failed

```bash
# Test API directly
curl -k -X GET https://your-icc-api.com/connection/list \
  -H "Authorization: Basic base64(username:password)" \
  -H "TokenKey: your-token"

# Check credentials in .env
cat .env | grep ICC_

# Verify network access
ping your-icc-api.com
```

See [docs/DEVOPS_GUIDE.md](docs/DEVOPS_GUIDE.md) for more troubleshooting.

## Performance

- **Response Time**: 1-2s (with warm models)
- **Cold Start**: ~10s (first request)
- **Memory Usage**: ~8GB (both models loaded)
- **Success Rate**: 95%+ for common queries

### Optimization

Models stay in memory using singleton pattern:
- First request: ~10s (model loading)
- Subsequent: ~1-2s (model cached)

## Project Structure

```
icc-agent/
├── src/
│   ├── ai/
│   │   ├── agents/              # LLM agents (SQL, Job)
│   │   └── router/              # FSM orchestrator & handlers
│   ├── services/                # Service layer
│   ├── repositories/            # Data access
│   ├── payload_builders/        # Request builders
│   ├── api_clients/             # ICC API clients
│   ├── models/                  # Data models
│   ├── errors/                  # Error handling
│   └── utils/                   # Utilities
│
├── docs/                        # Documentation
├── tests/                       # Test suite
├── app.py                       # Dash web application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── docker-compose.yml           # Docker orchestration
└── .env.example                 # Configuration template
```

## Contributing

### Development Setup

```bash
# Fork and clone repository
git clone <your-fork-url>
cd icc-agent

# Install dependencies
uv sync  # or: pip install -r requirements.txt

# Create feature branch
git checkout -b feature/your-feature

# Make changes

# Test locally
uv run app.py  # or: python app.py

# Commit and push
git commit -m "feat: add your feature"
git push origin feature/your-feature

# Create pull request
```

### Coding Standards

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for public methods
- Add tests for new features
- Update documentation

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for details.

## Roadmap

### Current (v1.0)
- ✅ ReadSQL with natural language
- ✅ WriteData with dropdown selectors
- ✅ SendEmail with attachments
- ✅ CompareSQL with column mapping
- ✅ Job confirmation workflow
- ✅ Folder organization

### Near-Term (Q1 2026)
- 🔄 Query templates and history
- 🔄 Scheduled recurring jobs
- 🔄 Usage analytics dashboard
- 🔄 Team collaboration features

### Long-Term (2026+)
- 📋 API access for programmatic use
- 📋 Slack/Teams integration
- 📋 Multi-step workflows
- 📋 Predictive analytics

See [docs/PRODUCT_OWNER_GUIDE.md](docs/PRODUCT_OWNER_GUIDE.md) for detailed roadmap.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: Open an issue in the repository
- **Questions**: Check documentation or contact development team

## Key Highlights

✅ **User-Friendly**: Natural language interface, no SQL required
✅ **Fast**: 1-2s responses with singleton LLM agents
✅ **Reliable**: 95%+ success rate with 7B-8B models
✅ **Safe**: Review and confirm before execution
✅ **Well-Documented**: Comprehensive guides for all audiences
✅ **Production-Ready**: Docker deployment with monitoring
✅ **Extensible**: Clean architecture, easy to add features

**Built for teams who need reliable database operations without the complexity of traditional tools.**

---

**Version**: 1.0
**Last Updated**: December 2025
**Maintainers**: Development Team

For detailed technical documentation, deployment guides, and architecture decisions, see the [docs/](docs/) folder.
