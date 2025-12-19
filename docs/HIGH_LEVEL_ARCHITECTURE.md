# High-Level Architecture - ICC Agent

## System Overview

The ICC Agent is a conversational AI system that translates natural language into database operations. It uses a finite state machine (FSM) architecture with a staged conversation flow, providing predictable and reliable user interactions.

### Key Characteristics

- **Architecture Style**: Layered + FSM (Finite State Machine)
- **Design Pattern**: Strategy Pattern for stage handling
- **LLM Integration**: Semi-static routing (deterministic flow with AI assistance)
- **Deployment**: Web application (Dash framework)
- **Communication**: REST API calls to ICC API backend

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Dash Web UI (app.py)                        │  │
│  │  • Connection/Schema/Folder Dropdowns                     │  │
│  │  • Chat Interface                                        │  │
│  │  • Table Selection                                       │  │
│  │  • Column Mapping UI (CompareSQL)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ User Events / Callbacks
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                         SERVICE LAYER                            │
│                                                                  │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ SessionManager │  │ ConnectionService│  │  AuthService   │  │
│  │ • Session CRUD │  │ • Fetch metadata │  │ • ICC Auth     │  │
│  │ • Memory state │  │ • Cache schemas  │  │ • Token mgmt   │  │
│  └────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           DropdownHandler (Generic UI Logic)               │ │
│  │  • Parse selections                                        │ │
│  │  • Update memory                                           │ │
│  │  • Bypass LLM for UI interactions                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Invoke Router
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                           CORE LAYER                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         Router Orchestrator (Singleton FSM)                │ │
│  │                                                            │ │
│  │  ┌──────────────┐      ┌──────────────┐                  │ │
│  │  │ Stage Context│      │ Job Context  │                  │ │
│  │  │ • Current    │      │ • Gathered   │                  │ │
│  │  │   Stage      │      │   Params     │                  │ │
│  │  │ • History    │      │ • SQL State  │                  │ │
│  │  └──────────────┘      └──────────────┘                  │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │            Handler Registry                          │ │ │
│  │  │  • ReadSQL Handler (8 strategies)                   │ │ │
│  │  │  • WriteData Handler (1 strategy)                   │ │ │
│  │  │  • SendEmail Handler (2 strategies)                 │ │ │
│  │  │  • CompareSQL Handler (14 strategies)               │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Each Handler uses Strategy Pattern:                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Stage → Strategy Mapping                                  │ │
│  │  • ASK_SQL_METHOD → AskSqlMethodStrategy                  │ │
│  │  • NEED_USER_SQL → NeedUserSqlStrategy                    │ │
│  │  • EXECUTE_SQL → ExecuteSqlStrategy                       │ │
│  │  • CONFIRM_JOB → ConfirmJobStrategy                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────┬─────────────────────────────────┬───────────────────┘
           │                                 │
           │ LLM Calls                       │ ICC API Calls
           │                                 │
┌──────────▼─────────┐           ┌───────────▼──────────────────┐
│   AI AGENT LAYER   │           │   DATA ACCESS LAYER          │
│                    │           │                              │
│ ┌────────────────┐ │           │ ┌──────────────────────────┐ │
│ │  SQL Agent     │ │           │ │  ICCAPIClient            │ │
│ │  (Singleton)   │ │           │ │  • Connection API        │ │
│ │  qwen2.5-coder │ │           │ │  • Job Execution API     │ │
│ └────────────────┘ │           │ │  • Schema/Table API      │ │
│                    │           │ │  • Folder API            │ │
│ ┌────────────────┐ │           │ └──────────────────────────┘ │
│ │  Job Agent     │ │           │                              │
│ │  (Singleton)   │ │           │ ┌──────────────────────────┐ │
│ │  qwen3:8b      │ │           │ │  Repositories            │ │
│ └────────────────┘ │           │ │  • ConnectionRepository  │ │
│                    │           │ │  • FolderRepository      │ │
│ Ollama Service     │           │ └──────────────────────────┘ │
│ localhost:11434    │           │                              │
└────────────────────┘           │ ┌──────────────────────────┐ │
                                 │ │  Payload Builders        │ │
                                 │ │  • Factory Pattern       │ │
                                 │ │  • Job-specific builders │ │
                                 │ └──────────────────────────┘ │
                                 └──────────────────────────────┘
                                           │
                                           │ HTTPS
                                           │
                                 ┌─────────▼─────────────────────┐
                                 │      ICC API Backend          │
                                 │      172.16.22.13:8084        │
                                 │  • Job Execution              │
                                 │  • Database Operations        │
                                 │  • Metadata Management        │
                                 └───────────────────────────────┘
```

## Component Responsibilities

### Presentation Layer

#### Dash Web UI (app.py)
**Purpose**: User interface and interaction handling

**Responsibilities**:
- Render chat interface
- Display dropdown selectors (connection, schema, folder, tables)
- Handle user input and button clicks
- Show column mapping interface (CompareSQL)
- Display job summaries and results

**Technologies**:
- Dash (Python web framework)
- Dash Bootstrap Components
- Plotly (for visualizations)

**Key Callbacks**:
- `send_message`: Process user chat input
- `connection_dropdown_submit`: Handle connection selection
- `schema_dropdown_submit`: Handle schema selection
- `folder_dropdown_submit`: Handle folder selection
- `submit_mapping`: Handle column mapping submission

### Service Layer

#### SessionManager
**Purpose**: Manage conversation sessions and memory state

**Responsibilities**:
- Create/retrieve/delete sessions
- Store session memory (in-memory dictionary)
- Track active sessions
- Session cleanup

**Key Methods**:
```python
get_or_create_session(session_id) -> Memory
delete_session(session_id) -> bool
get_all_sessions() -> Dict[str, Memory]
```

#### ConnectionService
**Purpose**: Fetch and cache database metadata

**Responsibilities**:
- Fetch connections from ICC API
- Fetch schemas for a connection
- Fetch tables for a schema
- Cache metadata to reduce API calls

**Key Methods**:
```python
fetch_connections(auth_headers) -> Dict[str, Any]
fetch_schemas(connection_id, auth_headers) -> List[str]
fetch_tables(connection_id, schema, auth_headers) -> List[str]
```

#### AuthService
**Purpose**: Handle ICC API authentication

**Responsibilities**:
- Authenticate with ICC API
- Manage auth tokens
- Cache credentials
- Refresh tokens when needed

**Key Methods**:
```python
authenticate() -> Tuple[str, str]  # (userpass, token)
populate_connections_on_load(memory) -> Dict[str, Any]
```

#### DropdownHandler
**Purpose**: Generic handler for UI dropdown selections

**Responsibilities**:
- Parse dropdown selection events
- Update memory state directly (bypass LLM)
- Invoke router with selection flag
- Format response for UI

**Key Methods**:
```python
parse_selection(...) -> Dict[str, str]
process_selection(...) -> Dict[str, Any]
format_response(response) -> Dict[str, Any]
```

**Design Pattern**: Eliminates code duplication between connection/schema/folder dropdowns

### Core Layer

#### Router Orchestrator
**Purpose**: Central FSM that manages conversation flow

**Responsibilities**:
- Route user input to appropriate handler
- Manage conversation state (Memory object)
- Coordinate between handlers
- Track stage transitions

**Key Methods**:
```python
async handle_turn(memory, user_input) -> StageHandlerResult
register_handler(handler) -> None
```

**Architecture**: Singleton pattern (stays loaded in memory)

**FSM Stages**: Defined in `Stage` enum (25+ stages across all job types)

#### Memory (Composition Pattern)
**Purpose**: Store conversation state

**Components**:
- **ConnectionManager**: Connection/schema state
- **JobContext**: Job parameters and execution state
- **StageContext**: Current stage and conversation history

**Benefits of Composition**:
- Clear separation of concerns
- Easy to extend
- Testable in isolation

#### Stage Handlers
**Purpose**: Handle specific job types

**Types**:
1. **ReadSQLHandler**: 8 strategies for SQL query workflow
2. **WriteDataHandler**: 1 strategy for data loading
3. **SendEmailHandler**: 2 strategies for email workflow
4. **CompareSQLHandler**: 14 strategies for data comparison

**Pattern**: Strategy Pattern
- Each stage has a dedicated strategy class
- Handler delegates to strategy based on current stage
- Strategies are registered in handler's strategy registry

**Example Flow (ReadSQL)**:
```
ASK_JOB_TYPE → ASK_SQL_METHOD → NEED_USER_SQL →
EXECUTE_SQL → CONFIRM_READ_SQL_JOB → SHOW_RESULTS
```

Each stage is handled by its own strategy class.

### AI Agent Layer

#### SQL Agent (qwen2.5-coder:7b)
**Purpose**: Generate SQL queries from natural language

**Responsibilities**:
- Convert natural language descriptions to SQL
- Optimize queries
- Handle complex query logic

**Architecture**: Singleton (stays loaded in Ollama)

**Key Configuration**:
```python
keep_alive="3600s"  # Keep model loaded for 1 hour
temperature=0.1     # Low temperature for deterministic output
```

#### Job Agent (qwen3:8b)
**Purpose**: Extract parameters from user input

**Responsibilities**:
- Parse natural language for job parameters
- Understand user intent
- Extract entities (names, emails, etc.)

**Architecture**: Singleton (stays loaded in Ollama)

**Example**:
```
Input: "name it customer_report, save to db"
Output: {
  "name": "customer_report",
  "execute_query": true
}
```

### Data Access Layer

#### ICCAPIClient
**Purpose**: Communicate with ICC API backend

**Responsibilities**:
- Execute HTTP requests to ICC API
- Handle authentication headers
- Manage retries and error handling
- Parse API responses

**Key Endpoints**:
- `/connection/list`: Fetch connections
- `/connection/{id}/schemas`: Fetch schemas
- `/connection/{id}/schemas/{name}/tables`: Fetch tables
- `/jobs/execute`: Execute jobs
- `/folders/list`: Fetch folders

#### Repositories
**Purpose**: Abstract data access with Repository Pattern

**Types**:
- **BaseRepository**: Generic HTTP client with error handling
- **ConnectionRepository**: Connection-specific data access
- **FolderRepository**: Folder-specific data access

**Benefits**:
- Centralized error handling
- Easy to mock for testing
- Consistent interface

#### Payload Builders
**Purpose**: Construct request payloads for ICC API

**Pattern**: Factory Pattern

**Types**:
- **ReadSqlBuilder**: Build ReadSQL job payloads
- **WriteDataBuilder**: Build WriteData job payloads
- **SendEmailBuilder**: Build SendEmail job payloads
- **CompareSqlBuilder**: Build CompareSQL job payloads

**Example**:
```python
payload = PayloadFactory.create_read_sql_payload(params)
# Returns properly formatted ReadSqlRequest
```

## Data Flow

### Example: ReadSQL Job Flow

```
1. User Input
   │
   ├─→ UI: User types "read customer data"
   │
2. Service Layer
   │
   ├─→ SessionManager: Get or create session memory
   │
3. Core Layer
   │
   ├─→ RouterOrchestrator: Route to ReadSQLHandler
   ├─→ ReadSQLHandler: Check current stage
   ├─→ Strategy: AskSqlMethodStrategy
   │   └─→ Ask: "create SQL or provide SQL?"
   │
4. User Response: "create"
   │
   ├─→ Strategy: NeedNaturalLanguageStrategy
   │   └─→ Ask: "Describe what data you want"
   │
5. User Response: "all customers from California"
   │
   ├─→ Strategy: GenerateSqlStrategy
   ├─→ LLM: SQL Agent (qwen2.5-coder)
   │   └─→ Generate: SELECT * FROM customers WHERE state='CA'
   ├─→ Store SQL in memory.last_sql
   │
6. Parameter Gathering
   │
   ├─→ Strategy: ExecuteSqlStrategy
   ├─→ LLM: Job Agent (qwen3:8b)
   │   └─→ Extract parameters (name, execute_query, etc.)
   ├─→ Validator: Check required parameters
   │
7. Confirmation
   │
   ├─→ Strategy: ConfirmJobStrategy
   │   └─→ Show summary and ask for confirmation
   │
8. User Confirms: "yes"
   │
   ├─→ Payload Builder: Create ReadSqlRequest
   ├─→ ICC API Client: POST /jobs/execute
   │
9. Job Execution
   │
   ├─→ ICC API: Execute SQL and return results
   │
10. Display Results
    │
    └─→ Strategy: ShowResultsStrategy
        └─→ Format and display job completion
```

## Communication Patterns

### 1. User → UI → Service
- **Pattern**: Event-driven callbacks
- **Protocol**: Dash callback functions
- **Data**: JSON-like dictionaries

### 2. Service → Core
- **Pattern**: Direct function calls
- **Protocol**: `async/await`
- **Data**: Memory objects, strings

### 3. Core → LLM Agents
- **Pattern**: Request/response
- **Protocol**: HTTP to Ollama API
- **Data**: JSON (prompt + params)
- **Optimization**: Singleton pattern keeps models loaded

### 4. Core → ICC API
- **Pattern**: REST API
- **Protocol**: HTTPS
- **Data**: JSON request/response
- **Authentication**: Basic Auth + Token headers

## State Management

### Session State (Memory)

**Storage**: In-memory dictionary (Python dict)
```python
sessions: Dict[str, Memory] = {}
```

**Lifetime**:
- Created on first user interaction
- Persists until explicit deletion or app restart
- No automatic expiration (could be added)

**Contents**:
- Current stage
- Gathered parameters
- SQL state (generated queries)
- Connection/schema context
- Column mappings (CompareSQL)
- Conversation history

**Scalability Concern**:
- Current: In-memory (single process)
- Future: Redis or database for multi-process deployment

### LLM Agent State

**Storage**: Ollama process memory

**Lifetime**:
- Models loaded on first use
- Stay in memory based on `keep_alive` setting (default: 3600s)
- Automatically unloaded after inactivity

**Optimization**:
- Singleton pattern prevents redundant model loading
- First request: ~10s (model loading)
- Subsequent requests: ~1-2s (model in memory)

## Error Handling

### Error Flow

```
Exception Raised
    ↓
ErrorHandler.handle()
    ↓
Categorize Error (API, LLM, Validation, etc.)
    ↓
Create ICCError with user-friendly message
    ↓
Log technical details
    ↓
Return error to user
```

### Error Types

1. **API Errors** (ICCAPIError)
   - Connection timeout
   - Authentication failure
   - Invalid request

2. **LLM Errors** (LLMError)
   - Model not available
   - Timeout
   - Invalid response

3. **Validation Errors** (ValidationError)
   - Missing parameters
   - Invalid email format
   - Duplicate job name

4. **User Errors** (DuplicateJobNameError, etc.)
   - Business logic violations

## Scalability Considerations

### Current Limitations

1. **Single Process**: In-memory session storage
2. **LLM Bottleneck**: One Ollama instance
3. **No Load Balancing**: Single app.py instance

### Scaling Strategies

#### Horizontal Scaling

**Challenge**: Shared session state

**Solution 1**: Sticky Sessions (Load Balancer)
```
Load Balancer (sticky sessions)
    ↓
    ├─→ App Instance 1 (users A, B)
    ├─→ App Instance 2 (users C, D)
    └─→ App Instance 3 (users E, F)
```

**Solution 2**: Redis Session Store
```
App Instances (stateless)
    ↓
Shared Redis (session storage)
```

#### Vertical Scaling

- Increase CPU/RAM for larger models
- Use GPU for faster inference
- Increase Ollama concurrency settings

#### LLM Scaling

**Option 1**: Separate Ollama Service
```
Multiple App Instances
    ↓
    └─→ Shared Ollama Service (powerful machine with GPU)
```

**Option 2**: Model Serving (vLLM, TensorRT)
```
Multiple App Instances
    ↓
    └─→ Model Serving Layer (vLLM cluster)
```

## Security Architecture

### Authentication & Authorization

**Current**:
- ICC API credentials in `.env`
- Basic Auth + Token headers
- SSL verification disabled (for internal network)

**Recommendations**:
- Add user authentication to Dash UI
- Role-based access control
- Enable SSL verification for production
- Rotate credentials regularly

### Data Security

**In Transit**:
- HTTPS to ICC API
- HTTP to Ollama (localhost only)

**At Rest**:
- Session data in memory (not persisted)
- Logs may contain sensitive data (consider encryption)

**Recommendations**:
- Encrypt prompt logs
- Sanitize sensitive data from logs
- Add data retention policies

### Network Security

**Current Topology**:
```
User Browser → Dash App → ICC API
             → Ollama (localhost)
```

**Recommendations**:
- Firewall rules (restrict ICC API access)
- VPN for remote access
- Rate limiting
- DDoS protection

## Performance Characteristics

### Response Times

| Operation | Cold Start | Warm (Cached) |
|-----------|------------|---------------|
| SQL Generation | ~10s | ~1-2s |
| Parameter Extraction | ~10s | ~1-2s |
| Connection Fetch | ~500ms | ~100ms (cached) |
| Schema Fetch | ~500ms | ~50ms (cached) |

### Resource Usage

| Component | CPU | Memory |
|-----------|-----|--------|
| Dash App | 10-20% | ~500MB |
| Ollama (qwen3:8b) | 50-100% | ~4GB |
| Ollama (qwen2.5-coder:7b) | 50-100% | ~3.5GB |
| **Total** | **Variable** | **~8GB** |

### Bottlenecks

1. **LLM Inference**: Slowest component (1-2s per call)
2. **ICC API Calls**: Network latency (~500ms)
3. **Model Loading**: Cold start penalty (~10s)

### Optimization Strategies

1. **Keep models warm**: `keep_alive=3600s`
2. **Cache metadata**: Connection/schema lists
3. **Singleton agents**: Prevent redundant loading
4. **Async I/O**: Concurrent ICC API calls

## Design Decisions

### Why FSM over Agentic?

**Agentic Approach** (LangChain, AutoGPT):
- ❌ Unpredictable (LLM decides tool calls)
- ❌ Expensive (5-15 LLM calls per task)
- ❌ Unreliable with small models
- ❌ Hard to debug

**FSM Approach** (ICC Agent):
- ✅ Predictable (deterministic flow)
- ✅ Efficient (1-3 LLM calls per task)
- ✅ Works with 7B-8B models
- ✅ Easy to test and debug

### Why Singleton LLM Agents?

**Alternative**: Load model per request
- ❌ 10s cold start per request
- ❌ High memory churn
- ❌ Poor user experience

**Singleton Pattern**:
- ✅ Models stay loaded
- ✅ Fast responses (1-2s)
- ✅ Consistent performance
- ✅ Resource efficient

### Why Strategy Pattern?

**Alternative**: Big switch statement
```python
if stage == "ASK_SQL_METHOD":
    # 50 lines
elif stage == "NEED_USER_SQL":
    # 50 lines
# ... 25 stages
```

**Strategy Pattern**:
- ✅ Each stage is a separate class
- ✅ Easy to add new stages
- ✅ Testable in isolation
- ✅ Clear responsibilities

## Integration Points

### Ollama Integration
- **Endpoint**: http://localhost:11434
- **Models**: qwen3:8b, qwen2.5-coder:7b
- **Format**: JSON requests with streaming support

### ICC API Integration
- **Endpoint**: https://172.16.22.13:8084
- **Auth**: Basic Auth + TokenKey header
- **Format**: JSON REST API
- **SSL**: Verification disabled (internal network)

### Future Integrations

Potential integration points:
- **BI Tools**: Tableau, Power BI connectors
- **Slack/Teams**: Chat-based job execution
- **Scheduling**: Cron/Airflow for recurring jobs
- **Monitoring**: Prometheus, Grafana

## Deployment Architecture

### Current Deployment

```
Single Server
    ├─→ Dash App (Python process)
    ├─→ Ollama Service (localhost:11434)
    └─→ Outbound HTTPS to ICC API
```

### Recommended Production

```
Load Balancer
    ↓
    ├─→ App Server 1 (Docker)
    ├─→ App Server 2 (Docker)
    └─→ App Server 3 (Docker)
          ↓
    Shared Ollama Server (GPU)
          ↓
    Redis (Session Storage)
          ↓
    ICC API Backend
```

## Monitoring and Observability

### Current Logging

- **Console logs**: Real-time application logs
- **Prompt logs**: LLM requests/responses (optional)
- **Level**: INFO (configurable)

### Recommended Metrics

**Application Metrics**:
- Request count per minute
- Response time distribution
- Error rate by type
- Active sessions

**LLM Metrics**:
- Model inference time
- Model load time
- Cache hit rate

**Infrastructure Metrics**:
- CPU/Memory usage
- Network latency
- Disk I/O

### Observability Stack

**Logs**:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk

**Metrics**:
- Prometheus + Grafana
- Datadog

**Tracing**:
- OpenTelemetry
- Jaeger

## Disaster Recovery

### Failure Scenarios

1. **Ollama Down**
   - Impact: LLM calls fail
   - Recovery: Restart Ollama service
   - Mitigation: Health checks, auto-restart

2. **ICC API Down**
   - Impact: Job execution fails
   - Recovery: Wait for ICC API recovery
   - Mitigation: Retry logic, queue jobs

3. **App Crash**
   - Impact: All sessions lost (in-memory)
   - Recovery: Restart app
   - Mitigation: Persistent session storage (Redis)

### Backup Strategy

**Configuration**:
- Backup `.env`, `docker-compose.yml`
- Version control for code

**Data**:
- Sessions are ephemeral (no backup needed)
- Logs can be archived (optional)

## Conclusion

The ICC Agent uses a layered architecture with FSM-based routing to provide a predictable and reliable conversational interface for database operations. Key design decisions (Singleton agents, Strategy pattern, semi-static routing) prioritize performance, reliability, and maintainability over pure flexibility.

**Strengths**:
- Predictable behavior
- Fast response times
- Works with smaller models
- Easy to extend

**Areas for Improvement**:
- Session persistence
- Horizontal scalability
- Advanced monitoring

---

**Document Version**: 1.0
**Last Updated**: December 2025
**Next Review**: March 2026
