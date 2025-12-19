# Developer Guide - ICC Agent

## Overview

This guide provides detailed information for developers working on the ICC Agent system. It covers architecture patterns, coding standards, development workflows, and how to extend the system.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Design Patterns](#design-patterns)
- [Code Organization](#code-organization)
- [Development Workflow](#development-workflow)
- [Adding New Features](#adding-new-features)
- [Testing Strategy](#testing-strategy)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- Python 3.11+
- Ollama installed with models (qwen3:8b, qwen2.5-coder:7b)
- Git
- IDE (VS Code, PyCharm recommended)

### Setup Development Environment

#### Option A: Using uv (Recommended - Faster)

```bash
# Clone repository
git clone <repository-url>
cd icc-agent

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Sync dependencies (auto-creates .venv)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your configuration

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
# Edit .env with your configuration

# Run application
python app.py
```

### Development Tools

**Package Manager:**
- **uv** (Recommended): Fast Python package installer and resolver
  - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Usage: `uv sync`, `uv pip install package`, `uv run script.py`
  - Benefits: 10-100x faster than pip, automatic .venv management
- **pip** (Traditional): Standard Python package manager

**Recommended VS Code Extensions:**
- Python (Microsoft)
- Pylance
- Python Docstring Generator
- GitLens

**Recommended Settings:**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "basic"
}
```

## Architecture Overview

### Architectural Layers

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│                    (app.py - Dash UI)                    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                     Service Layer                        │
│              (src/services/ - Business Logic)            │
│  • SessionManager       • ConnectionService              │
│  • AuthService          • DropdownHandler                │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                      Core Layer                          │
│            (src/ai/router/ - Orchestration)              │
│  • Router Orchestrator (Singleton)                       │
│  • Stage Handlers (Strategy Pattern)                     │
│  • Memory Management (Composition)                       │
└────────┬────────────────────────────────┬───────────────┘
         │                                │
┌────────▼──────────┐         ┌──────────▼───────────────┐
│   LLM Agents      │         │   Data Access Layer      │
│   (src/ai/agents) │         │   (src/api_clients,      │
│                   │         │    src/repositories)     │
└───────────────────┘         └──────────────────────────┘
```

### Key Concepts

#### 1. Finite State Machine (FSM) Router

The router uses a stage-based FSM approach:

```python
# Each conversation is in a specific stage
Stage.ASK_JOB_TYPE → Stage.ASK_SQL_METHOD → Stage.NEED_USER_SQL →
  Stage.EXECUTE_SQL → Stage.CONFIRM_READ_SQL_JOB → Stage.SHOW_RESULTS
```

Advantages:
- **Predictable**: Always know what comes next
- **Testable**: Each stage can be tested independently
- **Maintainable**: Clear separation of concerns

#### 2. Strategy Pattern for Stage Handlers

Each stage has a dedicated strategy class:

```python
class AskSqlMethodStrategy(StageStrategy):
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        # Handle this specific stage
        pass
```

Benefits:
- Easy to add new stages
- Clear responsibility boundaries
- Testable in isolation

#### 3. Singleton Pattern for Performance

```python
# Router orchestrator is singleton - stays in memory
_router_instance = None

def get_router_instance():
    global _router_instance
    if _router_instance is None:
        _router_instance = RouterOrchestrator(sql_agent, job_agent)
    return _router_instance
```

Benefits:
- LLM agents stay loaded (~1-2s response vs 10s cold start)
- Consistent state management
- Resource efficiency

#### 4. Composition over Inheritance

Memory object uses composition:

```python
class Memory:
    connection_manager: ConnectionManager  # Handles connections/schemas
    job_context: JobContext                # Manages job state
    stage_context: StageContext            # Tracks conversation flow
```

Benefits:
- Flexible and extensible
- Clear separation of concerns
- Easier to test

## Design Patterns

### 1. Service Layer Pattern

**Purpose**: Separate business logic from UI

**Example**:
```python
# app.py (UI layer)
@app.callback(...)
def send_message(message):
    response = await invoke_router_async(message, session_id)
    return response

# src/services/session_manager.py (Service layer)
class SessionManager:
    def get_or_create_session(self, session_id: str) -> Memory:
        # Business logic for session management
```

**When to use**:
- Complex business logic
- Reusable functionality
- Need to test without UI

### 2. Repository Pattern

**Purpose**: Abstract data access

**Example**:
```python
# src/repositories/base_repository.py
class BaseRepository:
    async def execute_request(self, method, url, **kwargs):
        # Generic HTTP request handling

# src/repositories/connection_repository.py
class ConnectionRepository(BaseRepository):
    async def fetch_connections(self):
        return await self.execute_request("GET", "/connection/list")
```

**When to use**:
- Database access
- External API calls
- Need to mock data access in tests

### 3. Factory Pattern

**Purpose**: Create objects without specifying exact class

**Example**:
```python
# src/payload_builders/factory.py
class PayloadFactory:
    @staticmethod
    def create_read_sql_payload(params: Dict[str, Any]) -> ReadSqlRequest:
        # Build ReadSqlRequest from parameters
```

**When to use**:
- Complex object construction
- Multiple construction paths
- Hide construction details

### 4. Dependency Injection

**Purpose**: Invert dependencies for testability

**Example**:
```python
# src/container.py
class Container:
    def __init__(self):
        self.auth_service = AuthService()
        self.connection_service = ConnectionService(
            auth_service=self.auth_service
        )
```

**When to use**:
- Need to swap implementations
- Testing with mocks
- Reduce coupling

## Code Organization

### Directory Structure

```
src/
├── ai/
│   ├── agents/                    # LLM agent singletons
│   │   ├── sql_agent.py          # SQL generation agent
│   │   └── job_agent.py          # Parameter extraction agent
│   │
│   ├── router/                    # Core routing logic
│   │   ├── router_orchestrator.py  # Main FSM orchestrator
│   │   ├── memory.py              # Conversation memory (composition)
│   │   ├── job_agent.py           # LLM interaction for params
│   │   │
│   │   ├── context/               # Memory components
│   │   │   ├── connection_manager.py
│   │   │   ├── job_context.py
│   │   │   └── stage_context.py
│   │   │
│   │   ├── stage_handlers/        # Stage-specific logic
│   │   │   ├── base_handler.py
│   │   │   ├── readsql_handler.py
│   │   │   ├── writedata_handler.py
│   │   │   ├── sendemail_handler.py
│   │   │   ├── comparesql_handler.py
│   │   │   │
│   │   │   └── strategies/        # Strategy implementations
│   │   │       ├── readsql/       # ReadSQL strategies
│   │   │       ├── writedata/     # WriteData strategies
│   │   │       ├── sendemail/     # SendEmail strategies
│   │   │       ├── comparesql/    # CompareSQL strategies
│   │   │       └── common/        # Shared strategies
│   │   │
│   │   ├── utils/                 # Router utilities
│   │   │   ├── connection_fetcher.py
│   │   │   └── edit_target_resolver.py
│   │   │
│   │   └── validators/            # Parameter validation
│   │       └── parameter_validator.py
│   │
│   └── toolkits/                  # ICC API wrappers
│       └── icc_toolkit.py
│
├── api_clients/                   # External API clients
│   ├── connection_api_client.py   # ICC connection API
│   └── table_api_client.py        # ICC table API
│
├── services/                      # Service layer
│   ├── session_manager.py         # Session management
│   ├── connection_service.py      # Connection metadata
│   ├── auth_service.py            # Authentication
│   └── dropdown_handler.py        # UI dropdown logic
│
├── repositories/                  # Data access layer
│   ├── base_repository.py         # Base HTTP repository
│   ├── connection_repository.py   # Connection data access
│   └── folder_repository.py       # Folder data access
│
├── payload_builders/              # Request payload builders
│   ├── factory.py                 # Payload factory
│   ├── read_sql_builder.py        # ReadSQL payloads
│   ├── write_data_builder.py      # WriteData payloads
│   ├── send_email_builder.py      # SendEmail payloads
│   └── compare_sql_builder.py     # CompareSQL payloads
│
├── models/                        # Data models
│   ├── requests.py                # Request models
│   └── responses.py               # Response models
│
├── errors/                        # Error handling
│   ├── error_handler.py           # Global error handler
│   └── icc_error.py               # Custom error types
│
└── utils/                         # Utilities
    ├── auth.py                    # Authentication helpers
    └── cache.py                   # Caching utilities
```

### Naming Conventions

**Files**:
- Use snake_case: `connection_service.py`
- Group related files in directories

**Classes**:
- Use PascalCase: `ConnectionService`
- Suffix with purpose: `*Handler`, `*Strategy`, `*Repository`

**Functions/Methods**:
- Use snake_case: `get_or_create_session()`
- Use verbs for actions: `fetch`, `create`, `validate`

**Constants**:
- Use UPPER_SNAKE_CASE: `MAX_RETRIES`, `DEFAULT_TIMEOUT`

**Private members**:
- Prefix with underscore: `_internal_method()`, `_cache`

## Development Workflow

### Quick Reference: Common Commands

**Using uv:**
```bash
# Install dependencies
uv sync

# Add new dependency
uv pip install package-name

# Run application
uv run app.py

# Run tests
uv run pytest tests/

# Run specific script
uv run python scripts/migrate.py
```

**Using pip:**
```bash
# Install dependencies
pip install -r requirements.txt

# Add new dependency
pip install package-name

# Run application
export PYTHONPATH=$(pwd) && python app.py

# Run tests
pytest tests/
```

### 1. Feature Development Process

```bash
# 1. Create feature branch
git checkout -b feature/add-new-job-type

# 2. Implement feature (see "Adding New Features")

# 3. Test locally
uv run app.py  # or: python app.py
# Test in browser

# 4. Run tests (if available)
uv run pytest tests/  # or: pytest tests/

# 5. Commit changes
git add .
git commit -m "feat: add new job type for bulk operations"

# 6. Push and create PR
git push origin feature/add-new-job-type
```

### 2. Bug Fix Process

```bash
# 1. Create bugfix branch
git checkout -b fix/dropdown-selection-error

# 2. Reproduce bug locally

# 3. Add test case (if possible)

# 4. Fix bug

# 5. Verify fix

# 6. Commit and push
git commit -m "fix: resolve dropdown selection error in CompareSQL"
git push origin fix/dropdown-selection-error
```

### 3. Code Review Checklist

Before submitting PR:
- [ ] Code follows SOLID principles
- [ ] Proper error handling
- [ ] Logging added for debugging
- [ ] No hardcoded credentials
- [ ] Docstrings for public methods
- [ ] Type hints used
- [ ] Tested manually
- [ ] No console.log or debug prints

## Adding New Features

### Example: Adding a New Job Type

Let's add a "BulkDelete" job type step-by-step.

#### Step 1: Define Stages

```python
# src/ai/router/context/stage_context.py

class Stage(Enum):
    # ... existing stages ...
    ASK_BULK_DELETE_METHOD = "ask_bulk_delete_method"
    NEED_DELETE_CRITERIA = "need_delete_criteria"
    CONFIRM_BULK_DELETE_JOB = "confirm_bulk_delete_job"
    EXECUTE_BULK_DELETE = "execute_bulk_delete"
```

#### Step 2: Create Handler

```python
# src/ai/router/stage_handlers/bulkdelete_handler.py

from src.ai.router.stage_handlers.base_handler import BaseStageHandler
from src.ai.router.context.stage_context import Stage

class BulkDeleteHandler(BaseStageHandler):
    """Handler for BulkDelete job flow."""

    def __init__(self, job_agent=None):
        super().__init__()
        self.job_agent = job_agent

        # Register strategies
        from .strategies.bulkdelete import (
            AskDeleteMethodStrategy,
            NeedDeleteCriteriaStrategy,
            ConfirmDeleteStrategy,
            ExecuteDeleteStrategy
        )

        self.strategy_registry.register(
            Stage.ASK_BULK_DELETE_METHOD,
            AskDeleteMethodStrategy()
        )
        self.strategy_registry.register(
            Stage.NEED_DELETE_CRITERIA,
            NeedDeleteCriteriaStrategy()
        )
        self.strategy_registry.register(
            Stage.CONFIRM_BULK_DELETE_JOB,
            ConfirmDeleteStrategy(job_type="bulk_delete")
        )
        self.strategy_registry.register(
            Stage.EXECUTE_BULK_DELETE,
            ExecuteDeleteStrategy(self.job_agent)
        )

    def can_handle(self, stage: Stage) -> bool:
        return self.strategy_registry.has_strategy(stage)

    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        # Delegate to strategy
        strategy = self.strategy_registry.get_strategy(memory.stage)
        if strategy:
            return await strategy.execute(memory, user_input)

        return self._create_result(
            memory,
            f"No strategy for stage: {memory.stage.value}",
            is_error=True
        )
```

#### Step 3: Create Strategies

```python
# src/ai/router/stage_handlers/strategies/bulkdelete/ask_delete_method.py

from src.ai.router.stage_handlers.stage_strategy import (
    StageStrategy,
    StageHandlerResult
)
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage

class AskDeleteMethodStrategy(StageStrategy):
    """Ask user how they want to specify delete criteria."""

    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        user_lower = user_input.lower().strip()

        if "sql" in user_lower or "query" in user_lower:
            memory.current_tool = "bulk_delete"
            return self._create_result(
                memory,
                "Provide SQL WHERE clause for deletion (e.g., WHERE status='INACTIVE'):",
                Stage.NEED_DELETE_CRITERIA
            )
        elif "criteria" in user_lower or "condition" in user_lower:
            memory.current_tool = "bulk_delete"
            return self._create_result(
                memory,
                "Describe the deletion criteria in natural language:",
                Stage.NEED_DELETE_CRITERIA
            )
        else:
            return self._create_result(
                memory,
                "How would you like to specify what to delete?\n" +
                "- 'sql' - Provide SQL WHERE clause\n" +
                "- 'criteria' - Describe in natural language"
            )
```

#### Step 4: Add to Router Orchestrator

```python
# src/ai/router/router_orchestrator.py

class RouterOrchestrator:
    def __init__(self, sql_agent=None, job_agent=None):
        # ... existing code ...

        # Add BulkDelete handler
        from .stage_handlers.bulkdelete_handler import BulkDeleteHandler
        bulk_delete_handler = BulkDeleteHandler(job_agent)
        self.register_handler(bulk_delete_handler)
```

#### Step 5: Add Parameter Validation

```python
# src/ai/router/validators/parameter_validator.py

class ParameterValidator:
    @staticmethod
    def validate_bulk_delete_params(params: Dict[str, Any], memory: Memory):
        """Validate bulk_delete parameters."""

        if not params.get("name"):
            return {"action": "ASK", "question": "What should I name this job?"}

        if not params.get("table"):
            return {"action": "ASK", "question": "Which table to delete from?"}

        if not params.get("where_clause"):
            return {"action": "ASK", "question": "What deletion criteria?"}

        # All required params present
        return None
```

#### Step 6: Add ICC API Call

```python
# src/ai/toolkits/icc_toolkit.py

async def bulk_delete_job(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute bulk delete job via ICC API."""

    try:
        # Build payload
        payload = {
            "name": params["name"],
            "table": params["table"],
            "whereClause": params["where_clause"],
            "connectionId": params["connection_id"]
        }

        # Call ICC API
        response = await http_client.post(
            "/jobs/bulk-delete",
            json=payload
        )

        return {
            "success": True,
            "job_id": response["jobId"],
            "message": f"Deleted {response['rowsAffected']} rows"
        }

    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        return {"success": False, "error": str(e)}
```

#### Step 7: Update UI

```python
# app.py

# Add BulkDelete option to job type selection
@app.callback(
    Output('job-type-store', 'data'),
    Input('bulk-delete-button', 'n_clicks')
)
def select_bulk_delete(n_clicks):
    if n_clicks:
        return {'job_type': 'bulk_delete'}
```

### Adding a New Strategy to Existing Handler

If you just want to add a new stage to an existing job type:

```python
# 1. Add stage to Stage enum
class Stage(Enum):
    # ... existing ...
    NEW_VALIDATION_STAGE = "new_validation_stage"

# 2. Create strategy
class NewValidationStrategy(StageStrategy):
    async def execute(self, memory, user_input):
        # Implementation
        pass

# 3. Register in handler
handler.strategy_registry.register(
    Stage.NEW_VALIDATION_STAGE,
    NewValidationStrategy()
)
```

## Testing Strategy

### Unit Testing

```python
# tests/test_connection_manager.py

import pytest
from src.ai.router.context.connection_manager import ConnectionManager

def test_get_connection_id_exact_match():
    """Test exact connection name match."""
    manager = ConnectionManager()
    manager.connections = {
        "ORACLE_10": {"id": "conn-123", "db_type": "Oracle"}
    }

    assert manager.get_connection_id("ORACLE_10") == "conn-123"

def test_get_connection_id_fuzzy_match():
    """Test fuzzy matching with case insensitivity."""
    manager = ConnectionManager()
    manager.connections = {
        "ORACLE_10": {"id": "conn-123", "db_type": "Oracle"}
    }

    # Should match despite case difference
    assert manager.get_connection_id("oracle10") == "conn-123"

def test_get_connection_id_not_found():
    """Test return None for unknown connection."""
    manager = ConnectionManager()
    manager.connections = {}

    assert manager.get_connection_id("UNKNOWN") is None
```

### Integration Testing

```python
# tests/test_router_flow.py

import pytest
from src.ai.router.router_orchestrator import handle_turn
from src.ai.router.memory import create_memory

@pytest.mark.asyncio
async def test_readsql_flow():
    """Test complete ReadSQL flow."""
    memory = create_memory()

    # Step 1: Select job type
    result = await handle_turn(memory, "readsql")
    assert result.next_stage == Stage.ASK_SQL_METHOD

    # Step 2: Choose SQL method
    result = await handle_turn(memory, "provide")
    assert result.next_stage == Stage.NEED_USER_SQL

    # Step 3: Provide SQL
    result = await handle_turn(memory, "SELECT * FROM customers")
    assert result.next_stage == Stage.EXECUTE_SQL

    # Continue flow...
```

### Manual Testing Checklist

For each new feature:
- [ ] Test happy path
- [ ] Test error cases
- [ ] Test edge cases (empty input, special characters)
- [ ] Test back/reset commands
- [ ] Test edit functionality
- [ ] Test with different connections/schemas

## Best Practices

### 1. SOLID Principles

**Single Responsibility**:
```python
# BAD: Handler does too much
class Handler:
    def fetch_data(self):
        pass
    def validate_data(self):
        pass
    def save_data(self):
        pass

# GOOD: Separate concerns
class DataFetcher:
    def fetch(self):
        pass

class DataValidator:
    def validate(self, data):
        pass

class DataRepository:
    def save(self, data):
        pass
```

**Open/Closed**:
```python
# Extend behavior without modifying existing code
class BaseStrategy:
    async def execute(self):
        pass

# Add new strategy without changing BaseStrategy
class NewStrategy(BaseStrategy):
    async def execute(self):
        # New implementation
        pass
```

**Dependency Inversion**:
```python
# Depend on abstractions, not concrete implementations
class Service:
    def __init__(self, repository: BaseRepository):
        self.repository = repository  # Abstract
```

### 2. Error Handling

Always handle errors gracefully:

```python
# BAD: Unhandled exception crashes application
def fetch_data():
    return api_client.get("/data")

# GOOD: Proper error handling
async def fetch_data() -> Dict[str, Any]:
    try:
        return await api_client.get("/data")
    except httpx.HTTPError as e:
        logger.error(f"API request failed: {e}", exc_info=True)
        error = ErrorHandler.handle(e, {"context": "fetch_data"})
        return {"success": False, "error": error.user_message}
```

### 3. Logging

Use appropriate log levels:

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed flow information
logger.debug(f"Processing stage: {memory.stage.value}")

# INFO: Important milestones
logger.info(f"Job created: {job_id}")

# WARNING: Recoverable issues
logger.warning(f"Connection slow, retrying...")

# ERROR: Operation failures
logger.error(f"Failed to execute job: {e}", exc_info=True)

# CRITICAL: System-level failures
logger.critical(f"Database unavailable")
```

### 4. Type Hints

Always use type hints:

```python
from typing import Dict, List, Optional, Any

def process_params(
    params: Dict[str, Any],
    connection: str,
    schemas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Process parameters for job execution.

    Args:
        params: Job parameters
        connection: Connection name
        schemas: Optional list of schemas

    Returns:
        Processed parameters dict
    """
    pass
```

### 5. Docstrings

Document all public methods:

```python
def create_session(self, session_id: str) -> Memory:
    """
    Create or retrieve a conversation session.

    This method implements session management with the following behavior:
    - If session exists, returns existing memory
    - If session is new, creates fresh memory with defaults

    Args:
        session_id: Unique session identifier

    Returns:
        Memory object for the session

    Raises:
        SessionError: If session creation fails

    Example:
        >>> manager = SessionManager()
        >>> memory = manager.create_session("user-123")
        >>> print(memory.stage)
        Stage.ASK_JOB_TYPE
    """
    pass
```

### 6. Avoid Code Duplication (DRY)

```python
# BAD: Duplicated logic
def fetch_schemas_for_readsql(connection):
    # ... 10 lines of code ...

def fetch_schemas_for_writedata(connection):
    # ... same 10 lines of code ...

# GOOD: Reusable utility
class ConnectionFetcher:
    @staticmethod
    async def fetch_schemas(connection_name: str, memory: Memory):
        # Single implementation
        pass

# Use everywhere
result = await ConnectionFetcher.fetch_schemas(connection, memory)
```

### 7. Keep Functions Small

```python
# BAD: God function doing everything
async def process_request(request):
    # 200 lines of code
    pass

# GOOD: Break into smaller functions
async def process_request(request):
    validated = validate_request(request)
    data = await fetch_data(validated)
    result = transform_data(data)
    return format_response(result)
```

## Troubleshooting

### Common Development Issues

#### 1. Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'src'

# Solution: Set PYTHONPATH
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH="$(pwd)"  # Windows PowerShell
```

#### 2. Ollama Not Responding

```python
# Error: Connection refused to Ollama

# Check Ollama is running
ollama list

# Restart Ollama
ollama serve

# Check model is loaded
ollama pull qwen3:8b
```

#### 3. Memory State Issues

```python
# If memory state seems corrupted during development:

# Option 1: Clear session
session_manager.sessions.pop(session_id)

# Option 2: Create fresh memory
memory = create_memory()

# Option 3: Reset specific fields
memory.gathered_params = {}
memory.last_question = None
```

#### 4. Strategy Not Found

```python
# Error: No strategy for stage: execute_sql

# Check stage is registered in handler
handler.strategy_registry.register(Stage.EXECUTE_SQL, ExecuteSqlStrategy())

# Check stage name matches enum
Stage.EXECUTE_SQL == memory.stage  # Should be True
```

### Debugging Tips

**Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect Memory State**:
```python
def debug_memory(memory):
    print(f"Stage: {memory.stage}")
    print(f"Params: {memory.gathered_params}")
    print(f"Tool: {memory.current_tool}")
    print(f"Last Q: {memory.last_question}")
```

**Test LLM Directly**:
```python
from src.ai.agents.job_agent import call_job_agent

memory = create_memory()
memory.current_tool = "read_sql"
action = call_job_agent(memory, "name it test123", tool_name="read_sql")
print(action)
```

## Contributing Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Maximum line length: 100 characters
- Use f-strings for formatting

### Commit Messages

Follow conventional commits:

```
feat: add bulk delete job type
fix: resolve dropdown selection bug
refactor: extract connection fetching to utility
docs: update developer guide with examples
test: add unit tests for parameter validator
```

### Pull Request Process

1. Create feature branch from `main`
2. Implement feature with tests
3. Update documentation
4. Create PR with clear description
5. Address review comments
6. Merge after approval

## Resources

- **Project Documentation**: `docs/` folder
- **Architecture Decisions**: `docs/HIGH_LEVEL_ARCHITECTURE.md`
- **API Reference**: Code docstrings
- **Ollama Docs**: https://ollama.ai/docs

---

**Document Version**: 1.0
**Last Updated**: December 2025
