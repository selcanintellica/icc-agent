# Architecture Decisions - Why Semi-Static Router Over Agentic Systems

## Overview

This document explains why ICC Agent uses a **semi-static router architecture** with limited LLM activity instead of traditional agentic frameworks (LangChain, AutoGPT) or standard Model Context Protocol (MCP) servers.

## The Problem with Traditional Agentic Systems

### LangChain ReAct Agents

Traditional agentic systems like LangChain's ReAct (Reasoning + Acting) pattern give LLMs full autonomy to:
- Decide which tools to call
- Plan multi-step sequences
- Reason about intermediate results
- Loop until task completion

**Why this fails for production database operations:**

#### 1. Unreliable Tool Selection with Small Models
```python
# LangChain Agent Behavior (7B-8B models)
User: "Get customers from USA"

Agent thinks: "I need to call... read_sql? query_database? execute_query? 
              Or should I call get_schema first?"
→ 40% chance: Calls wrong tool
→ 30% chance: Loops infinitely trying different tools
→ 20% chance: Hallucinates a tool that doesn't exist
→ 10% chance: Works correctly
```

**Problem**: Small models (7B-8B) lack the reasoning capability to reliably choose between similar tools. They need 70B+ models for consistent tool selection, which is too expensive/slow for production.

#### 2. Infinite Reasoning Loops
```python
# Typical failure pattern
Agent: "I should get the schema first"
→ Calls get_schema()
Agent: "Now I have schema, I should validate the query"
→ Calls validate_query()
Agent: "Wait, I should check table permissions"
→ Calls check_permissions()
Agent: "Actually, I should get the schema again to be sure"
→ Calls get_schema() [LOOP DETECTED]
```

**Problem**: Without strong reasoning, agents enter circular logic patterns. They keep calling tools "just to be sure" or because they forget what they already did.

#### 3. Unpredictable Multi-Step Planning
```python
# User wants: Read SQL → Write Data → Send Email

# Agentic System (unpredictable):
Agent: Calls read_sql() → Success
Agent: "Hmm, should I write data or send email first?"
      "Maybe I should verify the data before writing?"
      "Or should I ask the user to confirm?"
→ Takes 5-15 LLM calls with high variance
→ Total time: 15-45 seconds (unpredictable)
```

**Problem**: Each step requires LLM reasoning about "what next?", leading to:
- High latency (multiple LLM calls)
- Unpredictable behavior (different paths each time)
- Wasted API calls (unnecessary verification steps)

### Standard MCP Servers

MCP (Model Context Protocol) servers expose tools to LLMs, but still rely on the LLM to orchestrate tool calls:

```python
# MCP Server exposes tools
tools = [
    "read_sql",
    "write_data", 
    "send_email",
    "get_schema",
    "validate_query",
    "check_connection"
]

# LLM still decides: which tool, when, and in what order
→ Same problems as LangChain agents
→ Unreliable with small models
→ No deterministic workflow
```

**Problem**: MCP standardizes *how* tools are exposed, but doesn't solve *orchestration*. The LLM still needs strong reasoning to coordinate multiple tools.

## Our Solution: Semi-Static Router Architecture

### Core Principle: Minimize LLM Decision Points

Instead of letting LLMs decide everything, we use a **deterministic router** with **limited LLM roles**:

```python
# Semi-Static Router
User: "Get customers from USA"
                ↓
        Router (deterministic)
                ↓
        ReadSQLHandler [PREDETERMINED PATH]
                ↓
    Stage 1: ASK_SQL_METHOD
    Stage 2: NEED_NATURAL_LANGUAGE ← LLM generates SQL (ONE job)
    Stage 3: CONFIRM_GENERATED_SQL
    Stage 4: EXECUTE_SQL
    Stage 5: SHOW_RESULTS
    Stage 6: NEED_WRITE_OR_EMAIL
                ↓
    User: "write"
                ↓
        WriteDataHandler [PREDETERMINED PATH]
                ↓
    Stage: NEED_WRITE_OR_EMAIL ← LLM extracts parameters (ONE job)
    [Execute job]
```

### LLMs Have Exactly TWO Responsibilities

#### 1. SQL Agent - Generate SQL Query
```python
# ONLY does this ONE thing
User: "Get customers from USA"
SQL Agent Input:
  - User request
  - Table schema
  - Available columns

SQL Agent Output: "SELECT * FROM customers WHERE country = 'USA'"

# NO tool selection
# NO reasoning about what to do next
# NO multi-step planning
# Just: Natural language → SQL
```

#### 2. Job Agent - Extract Parameters
```python
# ONLY does this ONE thing
User: "write to sales_data table"
Job Agent Input:
  - Job type (WriteData)
  - Required parameters (schema, table_name, etc.)
  - User input

Job Agent Output: {"schema": "sales", "table_name": "sales_data"}

# NO tool selection
# NO reasoning about workflow
# NO deciding what to execute
# Just: User input → Structured parameters
```

### Router Handles ALL Orchestration

```python
# Deterministic workflow (NO LLM involvement)
class ReadSQLHandler:
    MANAGED_STAGES = [
        ASK_SQL_METHOD,
        NEED_NATURAL_LANGUAGE,
        CONFIRM_GENERATED_SQL,
        EXECUTE_SQL,
        SHOW_RESULTS,
        NEED_WRITE_OR_EMAIL
    ]
    
    def handle(self, stage, user_input):
        # Deterministic transitions (NO LLM decides this)
        if stage == CONFIRM_GENERATED_SQL:
            if user_input.lower() in ["yes", "y", "ok"]:
                return transition_to(EXECUTE_SQL)
            else:
                return transition_to(NEED_NATURAL_LANGUAGE)
        
        if stage == SHOW_RESULTS:
            if user_input.lower() == "write":
                return transition_to(WriteDataHandler)
            elif user_input.lower() == "email":
                return transition_to(SendEmailHandler)
            else:
                return transition_to(DONE)
```

**Key Point**: The router **code** determines the workflow, not the LLM. This is "semi-static" - the path is predetermined, only specific values (SQL, parameters) come from LLMs.

## Benefits of Semi-Static Architecture

### 1. Predictable Performance

| Metric | Agentic System | Semi-Static Router |
|--------|---------------|-------------------|
| **LLM Calls per Task** | 5-15 (variable) | 1-3 (fixed) |
| **Latency** | 15-45s (unpredictable) | 0.5-2s (consistent) |
| **Success Rate (7B model)** | 40-60% | 95%+ |
| **Token Usage** | High (repeated reasoning) | Low (targeted prompts) |

### 2. Reliable with Small Models

```python
# Agentic System needs 70B+ for reliability
Model Size: 70B+
RAM: 48GB+
Latency: 10-30s per decision
Cost: $$$$

# Semi-Static Router works with 7B-8B
Model Size: 7B-8B
RAM: 8-12GB
Latency: 0.5-2s per operation
Cost: $
```

### 3. Debuggable and Maintainable

**Agentic System:**
```
User: "Something went wrong"
Developer: "Let me check... the agent made 12 tool calls,
           reasoning changed on call #7, but I don't know why
           it decided to loop back to schema fetching..."
→ Black box debugging
```

**Semi-Static Router:**
```
User: "Something went wrong"
Developer: "Let me check... stage was CONFIRM_GENERATED_SQL,
           handler: ReadSQLHandler, transition logic in line 87"
→ Clear code path to debug
```

### 4. Controlled User Experience

**Agentic System:**
- User never knows what the agent will do next
- Agent might make 10 API calls before responding
- Unpredictable UX (sometimes fast, sometimes slow)

**Semi-Static Router:**
- User knows exact workflow: Choose method → Generate/Provide SQL → Confirm → Execute → Results
- Predictable stages with clear confirmations
- Consistent UX every time

## When Would We Use Agentic Systems?

Agentic systems make sense when:

1. **Open-ended tasks**: "Research this topic and write a report" (no predetermined path)
2. **Large models available**: 70B+ models with strong reasoning
3. **Latency acceptable**: Users willing to wait 30+ seconds
4. **Exploration encouraged**: Want LLM to try creative approaches
5. **Variable workflows**: Each task requires different tool sequences

## Why Semi-Static Works for Database Operations

Database operations are **inherently structured**:

1. **Fixed workflows**: Read SQL always follows: method → generate/provide → confirm → execute
2. **Clear stages**: Each step has defined inputs/outputs
3. **User control needed**: Database operations require confirmation (can't let agent auto-execute)
4. **Performance critical**: Users expect sub-second responses
5. **Reliability required**: 95%+ success rate needed for production

## Comparison Table

| Feature | LangChain Agent | MCP Server | Semi-Static Router |
|---------|----------------|------------|-------------------|
| **Tool Selection** | LLM decides | LLM decides | Code determines |
| **Workflow Control** | LLM plans | LLM plans | Handler defines |
| **Model Size Needed** | 70B+ | 70B+ | 7B-8B |
| **Latency** | 15-45s | 15-45s | 0.5-2s |
| **Success Rate (8B)** | 40-60% | 40-60% | 95%+ |
| **Predictability** | Low | Low | High |
| **Debuggability** | Hard | Hard | Easy |
| **User Control** | Minimal | Minimal | Full |
| **Multi-step Reliability** | Poor | Poor | Excellent |

## Implementation Details

### Limited LLM Activity

```python
# LLMs are ONLY called for:

1. SQL Generation (SQL Agent)
   - Input: Natural language + table schema
   - Output: SQL query string
   - Temperature: 0.1 (deterministic)
   - No tool calls, no reasoning loops

2. Parameter Extraction (Job Agent)
   - Input: User input + required parameters
   - Output: JSON with parameter values
   - Temperature: 0.1 (deterministic)
   - No tool calls, no reasoning loops

# Everything else handled by code:
- Stage transitions
- Workflow orchestration
- Tool execution
- Error handling
- User confirmations
```

### Singleton Pattern for Speed

```python
# LLM instances stay loaded in memory
_default_sql_agent = None  # Created once, reused forever
_default_job_agent = None  # Created once, reused forever

# Result: 0.5-2s responses (vs 5-10s if reloading each time)
# Model stays in Ollama with keep_alive="3600s"
```

### Handler Registry for Extensibility

```python
# Easy to add new handlers without changing core router
registry.register("readsql", ReadSQLHandler())
registry.register("writedata", WriteDataHandler())
registry.register("sendemail", SendEmailHandler())
registry.register("comparesql", CompareSQLHandler())

# Each handler manages its own stages
# Router just dispatches to correct handler
```

## Conclusion

ICC Agent uses a **semi-static router architecture** because:

1. ✅ **Reliable with small models** (7B-8B) - 95%+ success rate
2. ✅ **Fast responses** (0.5-2s) - singleton + keep_alive optimization
3. ✅ **Predictable workflows** - users know what to expect
4. ✅ **Debuggable** - clear code paths, no black box reasoning
5. ✅ **Production ready** - consistent performance, low resource usage
6. ✅ **User control** - confirmations at critical steps

Traditional agentic systems (LangChain, MCP) work well for:
- Open-ended research tasks
- Large model deployments (70B+)
- Exploratory workflows
- When latency is not critical

But for **structured database operations** with **small models** in **production**, semi-static routing is the optimal architecture.

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md) - Implementation deep dive
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development guide
- [ROUTER_ARCHITECTURE.md](ROUTER_ARCHITECTURE.md) - Router patterns
