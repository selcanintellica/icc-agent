# Staged Router Architecture

## Overview

The ICC Agent now uses a **staged conversation router** instead of a ReAct agent. This architecture is better suited for small LLMs (like qwen2.5:1.5b) because it breaks down complex tasks into simple, focused stages.

## Architecture

### Components

1. **Memory** (`src/ai/router/memory.py`)
   - Stores conversation state across turns
   - Tracks current stage, last SQL, job results, and gathered parameters

2. **SQL Agent** (`src/ai/router/sql_agent.py`)
   - Specialized LLM that converts natural language to SQL
   - Single focused task: generate SQL queries
   - Low temperature for consistent output

3. **Job Agent** (`src/ai/router/job_agent.py`)
   - Extracts parameters from user input
   - Asks clarifying questions for missing parameters
   - Determines when all parameters are ready

4. **Router** (`src/ai/router/router.py`)
   - State machine that orchestrates the conversation flow
   - Routes between stages based on current state
   - Invokes tools when ready

### Conversation Flow

```
START
  ↓
NEED_QUERY
  ↓ (SQL Agent generates SQL)
HAVE_SQL
  ↓ (Job Agent gathers params, executes read_sql)
SHOW_RESULTS
  ↓
NEED_WRITE_OR_EMAIL
  ↓ (Job Agent handles write_data or send_email)
DONE
```

## Why This Works Better for Small LLMs

### 1. **Simplified Decisions**
- ReAct: "Given all tools and context, what should I do next?"
- Router: "Are we at stage X or Y?" (much simpler)

### 2. **Focused Agents**
- Each agent handles ONE task
- SQL Agent: Only generates SQL
- Job Agent: Only extracts parameters
- No need to understand the entire workflow

### 3. **Reduced Context**
- ReAct: Keeps entire tool history in context
- Router: Only current stage + essential data
- Much smaller context window requirements

### 4. **Explicit Chaining**
- Workflow is hardcoded: read → write → email
- Small LLM doesn't need to figure out tool dependencies
- Parameters automatically passed between stages

### 5. **Guided Conversation**
- User is walked through each step
- Less ambiguity = fewer errors
- Small LLM only needs to understand current step

## Usage

### Running the Web Interface

```bash
python app.py
```

Then open http://localhost:8050

### Testing the Router

```bash
python test_router.py
```

### Example Conversation

```
User: get customers from USA
Agent: I prepared this SQL:
       ```sql
       SELECT * FROM customers WHERE country = 'USA'
       ```
       Shall I execute it?

User: yes
Agent: To execute, I need the database connection name. What connection should I use?

User: oracle_prod
Agent: ✅ Query executed successfully!
       📊 Columns: customer_id, name, email, country...
       🆔 Job ID: abc-123-def

Agent: What would you like to do next?
       • 'write' - Save results to a table
       • 'email' - Send results via email
       • 'done' - Finish

User: write to analytics_table
Agent: What database connection should I use for writing?

User: postgres_warehouse
Agent: Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?

User: truncate
Agent: ✅ Data written successfully to table 'analytics_table'!
       Anything else? (email / done)

User: done
Agent: ✅ All done! Say 'new query' to start again.
```

## Configuration

The router uses the same model configuration from `.env`:

```env
MODEL_NAME=qwen2.5:1.5b
```

Both SQL Agent and Job Agent use this model, but with different temperatures:
- SQL Agent: 0.1 (consistent SQL generation)
- Job Agent: 0.3 (more flexible parameter extraction)

## Extending

### Adding New Stages

1. Add stage to `Stage` enum in `memory.py`
2. Add stage handler in `router.py`
3. Update transitions in existing stages

### Adding New Tools

1. Create tool function in `icc_toolkit.py`
2. Add parameter requirements to Job Agent prompt
3. Add tool invocation logic in router

### Customizing Prompts

- SQL Agent prompt: `src/ai/router/sql_agent.py`
- Job Agent prompt: `src/ai/router/job_agent.py`

## Benefits Over ReAct

| Aspect | ReAct Agent | Staged Router |
|--------|-------------|---------------|
| Decision Complexity | High (all tools) | Low (current stage) |
| Context Size | Large | Small |
| Tool Chaining | LLM figures out | Hardcoded workflow |
| Error Recovery | Difficult | Easy (know exact stage) |
| Small LLM Performance | Poor | Good |
| Debugging | Hard | Easy (stage-based) |
| User Guidance | Minimal | Step-by-step |

## Troubleshooting

### Router not progressing
- Check logs for current stage
- Verify parameters are being extracted
- Ensure user input matches expected format

### SQL generation issues
- Check SQL Agent prompt
- Verify model is responding
- Look for JSON parsing errors

### Parameter extraction issues
- Check Job Agent prompt
- Verify parameter requirements
- Look for missing fallback logic

## Logs

Comprehensive logging shows:
- Current stage at each turn
- SQL generation process
- Parameter gathering
- Tool invocations
- Stage transitions

Look for emoji markers in logs:
- 🎯 Router entry
- 🔮 SQL generation
- 🔍 Parameter gathering
- ⚡ Tool execution
- ✅ Success
- ❌ Error
