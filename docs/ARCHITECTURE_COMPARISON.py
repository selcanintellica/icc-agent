"""
Quick comparison: ReAct vs Staged Router

This file demonstrates the key architectural differences.
"""

# ============================================================
# OLD APPROACH: ReAct Agent
# ============================================================

"""
Single LLM decides everything in one shot:

User: "read SQL and save to table"
  ↓
LLM thinks: "I need to:
  1. Call read_sql_job with parameters
  2. Wait for response
  3. Extract job_id and columns
  4. Call write_data_job with those
  5. Format nice response"
  ↓
LLM calls: read_sql_job(query=..., connection=...)
  ↓
LLM calls: write_data_job(data_set=job_id, columns=...)
  ↓
Done

PROBLEM: Small LLMs struggle with:
- Understanding all 3 tools at once
- Planning multi-step workflows
- Remembering to use job_id from step 1 in step 2
- Extracting complex parameters
- Long context with full tool history
"""


# ============================================================
# NEW APPROACH: Staged Router
# ============================================================

"""
Conversation broken into simple stages:

Stage 1 - NEED_QUERY:
  User: "get customers"
  SQL Agent: Generates "SELECT * FROM customers"
  → Simple task: NL to SQL only

Stage 2 - HAVE_SQL:
  Router: "What's the connection?"
  User: "oracle_prod"
  Job Agent: Extracts {"connection": "oracle_prod"}
  → Simple task: Extract one parameter

Stage 3 - Execute:
  Router: Calls read_sql_job(query, connection)
  Saves job_id and columns
  → No LLM needed, just execute

Stage 4 - SHOW_RESULTS:
  Router: "Write, email, or done?"
  User: "write to analytics"
  → Simple routing decision

Stage 5 - NEED_WRITE:
  Job Agent: Extracts {"table": "analytics"}
  Router: "What connection?"
  User: "postgres"
  Job Agent: Extracts {"connection": "postgres"}
  → Simple task: Extract parameters one by one

Stage 6 - Execute Write:
  Router: Calls write_data_job(
    data_set=saved_job_id,
    columns=saved_columns,
    table="analytics",
    connection="postgres"
  )
  → Automatic chaining, no LLM needed

BENEFITS:
✅ Each LLM call is simple
✅ No need to understand full workflow
✅ Parameters gathered gradually
✅ Small context (only current stage)
✅ Easy to debug (know exact stage)
✅ Guided user experience
"""


# ============================================================
# Code Comparison
# ============================================================

# ReAct: One complex agent
"""
agent = create_react_agent(
    model=big_llm,
    tools=[read_sql, write_data, send_email],
    prompt=long_complex_prompt
)
response = agent.invoke(user_message)
"""

# Staged Router: Multiple focused agents
"""
# Agent 1: SQL generation only
sql_agent.generate_sql(user_message) 
  → Returns: SQL string

# Agent 2: Parameter extraction only  
job_agent.gather_params(memory, user_message, tool_name)
  → Returns: {"action": "ASK"/"TOOL", "params": {...}}

# Router: State machine (no LLM)
router.handle_turn(memory, user_message)
  → Calls appropriate agent based on stage
  → Executes tools when ready
  → Manages state transitions
"""


# ============================================================
# LLM Requirements Comparison
# ============================================================

# ReAct Agent needs:
"""
- Large context window (all tool history)
- Strong reasoning (plan multi-step workflows)
- Good memory (remember job_id for next step)
- Tool understanding (know when to use each)
- Parameter extraction from complex prompts

Minimum recommended: 7B+ parameters
Works well with: 13B+ parameters
"""

# Staged Router needs:
"""
- Small context (current stage only)
- Simple reasoning (one task at a time)
- No long-term memory (router handles it)
- No tool knowledge (router decides)
- Parameter extraction from focused prompts

Works with: 1.5B+ parameters
Optimal: 3B parameters
"""


# ============================================================
# Example: Small LLM Performance
# ============================================================

# ReAct with qwen2.5:1.5b:
"""
User: "read SQL and save to table"

Agent: "I'll help you read SQL. [calls read_sql]"
  ❌ Forgets to pass connection
  ❌ Doesn't call write_data after
  ❌ Loses track of job_id
  
Result: Incomplete task
"""

# Router with qwen2.5:1.5b:
"""
User: "get customers"

SQL Agent: "SELECT * FROM customers" ✅
  (Simple SQL generation)

Router: "What connection?"
User: "oracle"

Job Agent: {"connection": "oracle"} ✅
  (Simple parameter extraction)

Router: Executes read_sql ✅
  (Automatic, no LLM)

Router: "Write or email?"
User: "write to table1"

Job Agent: {"table": "table1"} ✅
  (Simple extraction)

Router: Executes write_data ✅
  (Automatic chaining)

Result: Complete task ✅
"""
