# Low-Level Architecture - ICC Agent

## Overview

This document provides detailed technical specifications for key components in the ICC Agent system. For high-level architecture, see [HIGH_LEVEL_ARCHITECTURE.md](HIGH_LEVEL_ARCHITECTURE.md).

## Table of Contents

- [Router Orchestrator](#router-orchestrator)
- [Memory Management](#memory-management)
- [Stage Handlers and Strategies](#stage-handlers-and-strategies)
- [LLM Agent Integration](#llm-agent-integration)
- [Service Layer](#service-layer)
- [Data Access Layer](#data-access-layer)
- [Error Handling](#error-handling)

## Router Orchestrator

### Class: `RouterOrchestrator`

**Location**: `src/ai/router/router_orchestrator.py`

**Purpose**: Central FSM that manages conversation flow

### Implementation Details

```python
class RouterOrchestrator:
    def __init__(self, sql_agent=None, job_agent=None):
        """
        Initialize router with LLM agents.

        Args:
            sql_agent: Singleton SQL generation agent
            job_agent: Singleton parameter extraction agent
        """
        self.handlers: List[BaseStageHandler] = []
        self.sql_agent = sql_agent
        self.job_agent = job_agent

        # Register all handlers
        self._register_handlers()
```

### Handler Registration

```python
def _register_handlers(self):
    """Register all job type handlers."""
    from .stage_handlers import (
        ReadSQLHandler,
        WriteDataHandler,
        SendEmailHandler,
        CompareSQLHandler
    )

    # Create handlers with agent dependencies
    read_sql_handler = ReadSQLHandler(
        sql_agent=self.sql_agent,
        job_agent=self.job_agent
    )

    # Register handlers
    self.register_handler(read_sql_handler)
    self.register_handler(WriteDataHandler(self.job_agent))
    self.register_handler(SendEmailHandler(self.job_agent))
    self.register_handler(CompareSQLHandler(self.sql_agent, self.job_agent))
```

### Main Routing Logic

```python
async def handle_turn(
    memory: Memory,
    user_input: str
) -> StageHandlerResult:
    """
    Process one conversation turn.

    Flow:
    1. Find handler that can handle current stage
    2. Delegate to handler
    3. Return result (response + next stage)

    Args:
        memory: Conversation memory
        user_input: User's message

    Returns:
        StageHandlerResult with response and next_stage
    """
    logger.info(f"ROUTER: Processing stage={memory.stage.value}, input='{user_input[:50]}...'")

    # Find appropriate handler
    for handler in self.handlers:
        if handler.can_handle(memory.stage):
            logger.debug(f"Delegating to handler: {handler.__class__.__name__}")

            # Log memory state
            logger.debug(f"Memory state before handler: stage={memory.stage.value}, " +
                        f"current_tool={memory.current_tool}, " +
                        f"gathered_params={list(memory.gathered_params.keys())}")

            # Delegate to handler
            result = await handler.handle(memory, user_input)

            logger.debug(f"Handler result: next_stage={result.next_stage}, is_error={result.is_error}")

            return result

    # No handler found
    logger.error(f"No handler for stage: {memory.stage.value}")
    return StageHandlerResult(
        memory=memory,
        response=f"System error: No handler for stage {memory.stage.value}",
        is_error=True
    )
```

### Singleton Pattern

```python
# Global singleton instance
_router_instance: Optional[RouterOrchestrator] = None

def get_router_instance() -> RouterOrchestrator:
    """
    Get or create singleton router instance.

    Benefits:
    - LLM agents stay loaded in memory
    - Consistent state across requests
    - Fast response times (~1-2s vs ~10s cold start)
    """
    global _router_instance

    if _router_instance is None:
        logger.info("Initializing router orchestrator singleton")

        # Import and initialize agents
        from src.ai.agents.sql_agent import get_sql_agent
        from src.ai.agents.job_agent import get_job_agent

        sql_agent = get_sql_agent()
        job_agent = get_job_agent()

        _router_instance = RouterOrchestrator(sql_agent, job_agent)
        logger.info(f"Router orchestrator initialized (id: {id(_router_instance)})")

    return _router_instance
```

## Memory Management

### Composition Architecture

The Memory class uses composition to separate concerns:

```python
@dataclass
class Memory:
    """
    Conversation memory using composition pattern.

    Components:
    - connection_manager: Handles connections/schemas
    - job_context: Manages job state
    - stage_context: Tracks conversation flow
    """
    connection_manager: ConnectionManager
    job_context: JobContext
    stage_context: StageContext
```

### ConnectionManager

**Location**: `src/ai/router/context/connection_manager.py`

**Purpose**: Manage database connections and schemas

```python
class ConnectionManager:
    """Manages database connections and schema information."""

    def __init__(self, default_connection="ORACLE_10", default_schema="SALES"):
        self._connection: str = default_connection
        self._schema: str = default_schema
        self._connections: Dict[str, Dict[str, Any]] = {}  # {name: {id, db_type}}
        self._available_schemas: List[str] = []

    def get_connection_id(self, connection_name: str) -> Optional[str]:
        """
        Get connection ID with fuzzy matching.

        Handles:
        - Exact match: "ORACLE_10" → "ORACLE_10"
        - With db_type: "ORACLE_10 (Oracle)" → "ORACLE_10"
        - Case insensitive: "oracle10" → "ORACLE_10"
        - Underscore variations: "oracle_10" → "ORACLE_10"
        """
        # Exact match
        if connection_name in self._connections:
            return self._connections[connection_name].get("id")

        # Remove (db_type) suffix
        clean_name = connection_name.split("(")[0].strip()
        if clean_name in self._connections:
            return self._connections[clean_name].get("id")

        # Fuzzy match (case-insensitive, ignore underscores)
        normalized_input = clean_name.lower().replace("_", "").replace("-", "")

        for stored_name, conn_info in self._connections.items():
            normalized_stored = stored_name.lower().replace("_", "").replace("-", "")
            if normalized_input == normalized_stored:
                return conn_info.get("id")

        return None
```

### JobContext

**Location**: `src/ai/router/context/job_context.py`

**Purpose**: Store job execution state

```python
@dataclass
class JobContext:
    """Job execution state."""

    # Job type and parameters
    job_type: str = ""
    current_tool: Optional[str] = None
    gathered_params: Dict[str, Any] = field(default_factory=dict)

    # SQL state
    last_sql: Optional[str] = None
    first_sql: Optional[str] = None  # CompareSQL
    second_sql: Optional[str] = None  # CompareSQL

    # Column mappings (CompareSQL)
    first_columns: Optional[List[str]] = None
    second_columns: Optional[List[str]] = None
    column_mappings: Optional[List[Dict[str, str]]] = None
    key_mappings: Optional[List[Dict[str, str]]] = None

    # Job results
    last_job_id: Optional[str] = None
    last_job_name: Optional[str] = None
    last_job_folder: Optional[str] = None
    last_columns: Optional[List[str]] = None
    last_preview: Optional[Dict[str, Any]] = None

    # Feature flags
    execute_query_enabled: bool = False
    email_query_confirmed: bool = False

    # Output tracking
    output_table_info: Optional[Dict[str, str]] = None

    # Created jobs history
    created_jobs: List[Dict[str, str]] = field(default_factory=list)

    # Session-level folder
    job_folder: str = ""

    # Selected tables (from UI)
    selected_tables: List[str] = field(default_factory=list)

    # Pending email params (for confirmation flow)
    pending_email_params: Optional[Dict[str, Any]] = None
```

### StageContext

**Location**: `src/ai/router/context/stage_context.py`

**Purpose**: Track conversation flow

```python
@dataclass
class StageContext:
    """Conversation stage tracking."""

    stage: Stage = Stage.ASK_JOB_TYPE
    last_question: Optional[str] = None
    confirmation_substate: Optional[str] = None  # For edit handling
```

### Memory Serialization

```python
def to_dict(self) -> Dict[str, Any]:
    """
    Convert Memory to dictionary for serialization.

    Used for:
    - Session persistence
    - Debugging
    - API responses
    """
    return {
        "connection_manager": self.connection_manager.to_dict(),
        "job_context": asdict(self.job_context),
        "stage_context": asdict(self.stage_context)
    }

@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "Memory":
    """
    Create Memory from dictionary.

    Used for:
    - Session restoration
    - Testing
    """
    connection_manager = ConnectionManager.from_dict(data["connection_manager"])
    job_context = JobContext(**data["job_context"])
    stage_context = StageContext(**data["stage_context"])

    return cls(connection_manager, job_context, stage_context)
```

## Stage Handlers and Strategies

### Base Handler

**Location**: `src/ai/router/stage_handlers/base_handler.py`

```python
class BaseStageHandler(ABC):
    """
    Base class for all stage handlers.

    Uses Strategy Pattern:
    - Handlers register strategies for each stage
    - Handler delegates to appropriate strategy
    """

    def __init__(self):
        self.strategy_registry = StrategyRegistry()

    @abstractmethod
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        pass

    @abstractmethod
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Handle the stage."""
        pass

    def _create_result(
        self,
        memory: Memory,
        response: str,
        next_stage: Optional[Stage] = None,
        is_error: bool = False
    ) -> StageHandlerResult:
        """Helper to create result."""
        return StageHandlerResult(
            memory=memory,
            response=response,
            next_stage=next_stage,
            is_error=is_error
        )
```

### Strategy Registry

```python
class StrategyRegistry:
    """Registry for stage strategies."""

    def __init__(self):
        self._strategies: Dict[Stage, StageStrategy] = {}

    def register(self, stage: Stage, strategy: StageStrategy):
        """Register a strategy for a stage."""
        self._strategies[stage] = strategy

    def get_strategy(self, stage: Stage) -> Optional[StageStrategy]:
        """Get strategy for a stage."""
        return self._strategies.get(stage)

    def has_strategy(self, stage: Stage) -> bool:
        """Check if strategy exists for stage."""
        return stage in self._strategies
```

### Strategy Interface

```python
class StageStrategy(ABC):
    """Base class for stage strategies."""

    @abstractmethod
    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute strategy logic."""
        pass

    def _create_result(
        self,
        memory: Memory,
        response: str,
        next_stage: Optional[Stage] = None,
        is_error: bool = False
    ) -> StageHandlerResult:
        """Helper to create result."""
        return StageHandlerResult(
            memory=memory,
            response=response,
            next_stage=next_stage,
            is_error=is_error
        )
```

### Example Strategy: ExecuteSqlStrategy

**Location**: `src/ai/router/stage_handlers/strategies/readsql/execute_sql.py`

```python
class ExecuteSqlStrategy(StageStrategy):
    """
    Handle SQL execution with parameter gathering.

    Responsibilities:
    - Call job agent to extract parameters from user input
    - Validate parameters using ParameterValidator
    - Handle FETCH_SCHEMAS/FETCH_CONNECTIONS actions
    - Transition to confirmation when all params gathered
    """

    def __init__(self, job_agent=None):
        self.job_agent = job_agent

    async def execute(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Execute parameter gathering."""

        # Handle confirmation messages
        if user_input.lower() in ["yes", "y", "confirm", "ok"]:
            logger.debug(f"Ignoring confirmation message - starting fresh")
            user_input = ""

        # Call job agent to extract parameters
        action = call_job_agent(memory, user_input, tool_name="read_sql")

        # Handle actions
        if action.get("action") == "ASK":
            # Need more information from user
            memory.last_question = action["question"]
            return self._create_result(memory, action["question"])

        elif action.get("action") == "FETCH_SCHEMAS":
            # Need to fetch schemas and show dropdown
            from src.ai.router.utils.connection_fetcher import ConnectionFetcher

            connection_name = action.get("connection")
            result = await ConnectionFetcher.fetch_schemas(connection_name, memory)

            if not result["success"]:
                return self._create_result(
                    memory,
                    f"Unable to fetch schemas: {result['message']}",
                    is_error=True
                )

            # Return special response for UI to show dropdown
            import json
            dropdown_data = {
                "question": "Which schema should I use?",
                "schemas": result["schemas"],
                "param_name": "result_schema"
            }

            return self._create_result(
                memory,
                f"SCHEMA_DROPDOWN:{json.dumps(dropdown_data)}"
            )

        elif action.get("action") == "EXECUTE":
            # All parameters gathered, transition to confirmation
            return self._create_result(
                memory,
                "Parameters gathered. Preparing job summary...",
                Stage.CONFIRM_READ_SQL_JOB
            )

        else:
            return self._create_result(
                memory,
                f"Unexpected action: {action.get('action')}",
                is_error=True
            )
```

## LLM Agent Integration

### SQL Agent

**Location**: `src/ai/agents/sql_agent.py`

```python
# Singleton instance
_sql_agent = None

def get_sql_agent():
    """Get or create SQL agent singleton."""
    global _sql_agent

    if _sql_agent is None:
        _sql_agent = SQLAgent()
        logger.info("SQL agent initialized")

    return _sql_agent

class SQLAgent:
    """SQL generation agent using Ollama."""

    def __init__(self):
        self.model_name = os.getenv("SQL_MODEL_NAME", "qwen2.5-coder:7b")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate_sql(
        self,
        natural_language: str,
        connection: str,
        schema: str,
        tables: List[str]
    ) -> str:
        """
        Generate SQL from natural language.

        Args:
            natural_language: User's description
            connection: Database connection
            schema: Schema name
            tables: Available tables

        Returns:
            Generated SQL query
        """
        # Build prompt
        prompt = self._build_prompt(natural_language, connection, schema, tables)

        # Call Ollama
        response = await self.client.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for deterministic output
                    "top_p": 0.9,
                    "top_k": 40
                },
                "keep_alive": "3600s"  # Keep model loaded for 1 hour
            }
        )

        result = response.json()
        sql = self._extract_sql(result["response"])

        return sql

    def _build_prompt(self, nl, connection, schema, tables):
        """Build prompt for SQL generation."""
        return f"""You are an expert SQL generator. Generate a SQL query based on the user's request.

Database: {connection}
Schema: {schema}
Available tables: {', '.join(tables)}

User request: {nl}

Generate ONLY the SQL query, no explanations. The query should be valid SQL for the specified database."""

    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response."""
        # Remove markdown code blocks if present
        if "```sql" in response:
            sql = response.split("```sql")[1].split("```")[0].strip()
        elif "```" in response:
            sql = response.split("```")[1].split("```")[0].strip()
        else:
            sql = response.strip()

        return sql
```

### Job Agent

**Location**: `src/ai/router/job_agent.py`

```python
def call_job_agent(
    memory: Memory,
    user_input: str,
    tool_name: str
) -> Dict[str, Any]:
    """
    Call job agent to extract parameters.

    Flow:
    1. Build prompt with current parameters and last question
    2. Call LLM to extract parameters from user input
    3. Parse LLM response
    4. Update memory.gathered_params
    5. Validate parameters
    6. Return action (ASK, FETCH_SCHEMAS, EXECUTE)

    Args:
        memory: Conversation memory
        user_input: User's message
        tool_name: Job type (read_sql, write_data, etc.)

    Returns:
        Action dict with type and details
    """
    # Build prompt
    prompt = _build_job_agent_prompt(memory, user_input, tool_name)

    # Call LLM
    from src.ai.agents.job_agent import get_job_agent
    job_agent = get_job_agent()

    response = job_agent.extract_parameters(prompt)

    # Parse response
    extracted_params = _parse_agent_response(response)

    # Update memory
    memory.gathered_params.update(extracted_params)

    # Validate parameters
    from src.ai.router.validators.parameter_validator import ParameterValidator

    if tool_name == "read_sql":
        validation_result = ParameterValidator.validate_read_sql_params(
            memory.gathered_params,
            memory
        )
    elif tool_name == "write_data":
        validation_result = ParameterValidator.validate_write_data_params(
            memory.gathered_params,
            memory
        )
    # ... other job types

    if validation_result:
        # More parameters needed
        return validation_result
    else:
        # All parameters gathered
        return {"action": "EXECUTE"}
```

## Service Layer

### SessionManager

**Location**: `src/services/session_manager.py`

```python
class SessionManager:
    """Manage conversation sessions."""

    def __init__(self):
        self.sessions: Dict[str, Memory] = {}
        logger.info("SessionManager initialized")

    def get_or_create_session(self, session_id: str) -> Memory:
        """
        Get existing session or create new one.

        Args:
            session_id: Unique session identifier

        Returns:
            Memory object for the session
        """
        if session_id not in self.sessions:
            logger.info(f"Creating new session: {session_id}")
            self.sessions[session_id] = create_memory()
        else:
            logger.debug(f"Retrieved existing session: {session_id}")

        return self.sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    def get_all_sessions(self) -> Dict[str, Memory]:
        """Get all active sessions."""
        return self.sessions
```

### DropdownHandler

**Location**: `src/services/dropdown_handler.py`

```python
class DropdownHandler:
    """
    Generic handler for dropdown selections.

    Eliminates code duplication between connection/schema/folder dropdowns.

    Flow:
    1. Parse which dropdown was clicked
    2. Extract selected value
    3. Update memory directly (bypass LLM)
    4. Invoke router with selection flag
    5. Format response
    """

    def __init__(self, session_manager, invoke_router_async):
        self.session_manager = session_manager
        self.invoke_router_async = invoke_router_async

    async def process_selection(
        self,
        selection_type: str,  # "SCHEMA", "CONNECTION", "FOLDER"
        selected_value: str,
        param_name: str,
        session_id: str,
        config: Dict[str, Any],
        memory_update_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process dropdown selection.

        Args:
            selection_type: Type of selection (SCHEMA, CONNECTION, FOLDER)
            selected_value: Value user selected
            param_name: Parameter name in memory
            session_id: Session ID
            config: Configuration with connection/schema/tables
            memory_update_fn: Optional function to update memory

        Returns:
            Router response dict
        """
        # Get memory
        memory = self.session_manager.get_or_create_session(session_id)

        # Update memory directly (bypass LLM)
        memory.gathered_params[param_name] = selected_value
        logger.info(f"Directly assigned {param_name}={selected_value} (bypassed LLM)")

        # Apply custom memory update if provided
        if memory_update_fn:
            memory_update_fn(memory)

        # Invoke router with selection flag
        selection_flag = f"__{selection_type}_SELECTED__:{selected_value}"
        response = await self.invoke_router_async(
            selection_flag,
            session_id=session_id,
            connection=config.get("connection"),
            schema=config.get("schema"),
            selected_tables=config.get("tables", []),
            folder_id=config.get("folder_id")
        )

        return response
```

## Data Access Layer

### Base Repository

**Location**: `src/repositories/base_repository.py`

```python
class BaseRepository:
    """
    Base repository with common HTTP operations.

    Responsibilities:
    - HTTP request execution
    - Error handling
    - Retry logic
    - Logging
    """

    def __init__(self, base_url: str, auth_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.auth_headers = auth_headers or {}
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=False  # Disable SSL verification (internal network)
        )

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """
        Execute HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response data

        Raises:
            ICCAPIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Merge auth headers
        headers = {**self.auth_headers, **kwargs.pop("headers", {})}

        try:
            logger.debug(f"{method} {url}")

            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )

            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {url}")
            raise ICCAPIError(
                message=f"API request failed: {e.response.status_code}",
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ICCAPIError(
                message=f"Connection failed: {str(e)}",
                status_code=0
            )
```

## Error Handling

### Error Handler

**Location**: `src/errors/error_handler.py`

```python
class ErrorHandler:
    """
    Centralized error handling.

    Flow:
    1. Catch exception
    2. Categorize error type
    3. Create ICCError with user-friendly message
    4. Log technical details
    5. Return error to caller
    """

    @staticmethod
    def handle(
        exception: Exception,
        context: Dict[str, Any]
    ) -> ICCError:
        """
        Handle exception and return user-friendly error.

        Args:
            exception: The exception that occurred
            context: Additional context (user input, stage, etc.)

        Returns:
            ICCError with user_message and technical_details
        """
        # Log exception
        logger.error(
            f"Error in {context.get('context', 'unknown')}: {str(exception)}",
            exc_info=True
        )

        # Categorize and create error
        if isinstance(exception, httpx.HTTPStatusError):
            return ICCError(
                category=ErrorCategory.API_ERROR,
                user_message="Failed to connect to ICC API. Please try again.",
                technical_details=str(exception),
                context=context
            )

        elif isinstance(exception, DuplicateJobNameError):
            return ICCError(
                category=ErrorCategory.VALIDATION_ERROR,
                user_message=f"Job name '{exception.job_name}' already exists. Please use a different name.",
                technical_details=str(exception),
                context=context
            )

        elif isinstance(exception, ValidationError):
            return ICCError(
                category=ErrorCategory.VALIDATION_ERROR,
                user_message=exception.message,
                technical_details=str(exception),
                context=context
            )

        else:
            # Generic error
            return ICCError(
                category=ErrorCategory.SYSTEM_ERROR,
                user_message="An unexpected error occurred. Please try again.",
                technical_details=str(exception),
                context=context
            )
```

### Custom Exceptions

```python
class ICCError(Exception):
    """Base error class."""

    def __init__(
        self,
        category: ErrorCategory,
        user_message: str,
        technical_details: str,
        context: Dict[str, Any]
    ):
        self.category = category
        self.user_message = user_message
        self.technical_details = technical_details
        self.context = context
        super().__init__(user_message)

class DuplicateJobNameError(Exception):
    """Raised when job name already exists."""

    def __init__(self, job_name: str):
        self.job_name = job_name
        super().__init__(f"Job name already exists: {job_name}")

class ValidationError(Exception):
    """Raised for parameter validation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

## Performance Optimizations

### 1. Singleton LLM Agents

**Problem**: Loading models takes ~10s per request

**Solution**: Keep models in memory

```python
_sql_agent = None  # Global singleton

def get_sql_agent():
    global _sql_agent
    if _sql_agent is None:
        _sql_agent = SQLAgent()
    return _sql_agent
```

**Result**: First request ~10s, subsequent ~1-2s

### 2. Connection Caching

**Problem**: Fetching connections on every request

**Solution**: Cache in memory

```python
class ConnectionService:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    async def fetch_connections(self):
        if "connections" in self._cache:
            return self._cache["connections"]

        connections = await api_client.get("/connection/list")
        self._cache["connections"] = connections
        return connections
```

### 3. Async I/O

**Problem**: Sequential API calls block

**Solution**: Use async/await

```python
# Sequential (slow)
schemas1 = await fetch_schemas(conn1)
schemas2 = await fetch_schemas(conn2)

# Concurrent (fast)
schemas1, schemas2 = await asyncio.gather(
    fetch_schemas(conn1),
    fetch_schemas(conn2)
)
```

## Testing Strategies

### Unit Tests

```python
# Test connection manager
def test_get_connection_id_exact_match():
    manager = ConnectionManager()
    manager.connections = {"ORACLE_10": {"id": "conn-123"}}

    assert manager.get_connection_id("ORACLE_10") == "conn-123"

# Test fuzzy matching
def test_get_connection_id_case_insensitive():
    manager = ConnectionManager()
    manager.connections = {"ORACLE_10": {"id": "conn-123"}}

    assert manager.get_connection_id("oracle10") == "conn-123"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_readsql_flow():
    memory = create_memory()

    # Step 1
    result = await handle_turn(memory, "readsql")
    assert result.next_stage == Stage.ASK_SQL_METHOD

    # Step 2
    result = await handle_turn(memory, "provide")
    assert result.next_stage == Stage.NEED_USER_SQL

    # Continue...
```

## Conclusion

This low-level architecture document provides detailed implementation specifications for the ICC Agent system. Key technical decisions include:

- **Singleton pattern** for LLM agents (performance)
- **Strategy pattern** for stage handling (maintainability)
- **Composition** for memory (flexibility)
- **Repository pattern** for data access (testability)
- **Centralized error handling** (consistency)

For high-level overview, see [HIGH_LEVEL_ARCHITECTURE.md](HIGH_LEVEL_ARCHITECTURE.md).

---

**Document Version**: 1.0
**Last Updated**: December 2025
