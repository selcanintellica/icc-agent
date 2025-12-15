# Global Edit & Confirmation Implementation Status

## ✅ COMPLETED (Phase 1 & 2 Foundation)

### 1. Global Command Handler ✅
**File:** `src/ai/router/global_command_handler.py`

**Features:**
- `check_global_command()` - Detects back, reset, edit, review commands
- `handle_reset()` - Clears all data and returns to START
- `handle_back()` - Uses stage history to go back
- `handle_review()` - Shows current state summary
- `handle_edit()` - Delegates to edit resolver

**Usage:**
```python
from src.ai.router.global_command_handler import GlobalCommandHandler

command = GlobalCommandHandler.check_global_command(memory, user_input)
if command == "reset":
    result = GlobalCommandHandler.handle_reset(memory)
elif command == "back":
    result = GlobalCommandHandler.handle_back(memory)
elif command == "review":
    result = GlobalCommandHandler.handle_review(memory)
elif command == "edit":
    result = GlobalCommandHandler.handle_edit(memory, user_input, edit_resolver)
```

### 2. Memory Structure Updates ✅
**File:** `src/ai/router/memory.py`

**Added:**
- `get_editable_summary()` - Returns all editable parameters organized by category

**Benefits:**
- Easy to generate confirmation summaries
- Centralized access to all editable data
- Used by review command and confirmation stages

### 3. Stage History Tracking ✅
**File:** `src/ai/router/context/stage_context.py`

**Added:**
- `_stage_history: list` - Tracks visited stages
- `go_back()` - Navigate to previous stage
- `reset_history()` - Clear history
- Updated `transition_to()` - Automatically tracks history
- Updated `reset()` - Clears history on reset

**Benefits:**
- Users can go back through conversation
- Supports undo functionality
- Foundation for navigation

### 4. Edit Target Resolver ✅
**File:** `src/ai/router/utils/edit_target_resolver.py`

**Features:**
- Maps natural language to stage transitions
- Direct matches: "edit sql", "change first query"
- Fuzzy matches: "fix the sql", "update mapping"
- Partial matches: "edit first" → "edit first sql"
- `get_available_edit_targets()` - Shows what can be edited

**Supported Edit Targets:**
- ReadSQL: sql, query, connection
- CompareSQL: first sql, second sql, mapping, columns, reporting
- All jobs: job name, name, schema, table

### 5. Confirmation Stage Enums ✅
**File:** `src/ai/router/context/stage_context.py`

**Added Stages:**
- `Stage.CONFIRM_READ_SQL_JOB`
- `Stage.CONFIRM_WRITE_DATA_JOB`
- `Stage.CONFIRM_SEND_EMAIL_JOB`
- `Stage.CONFIRM_COMPARE_SQL_JOB`

---

## 🚧 IN PROGRESS / TODO

### Priority 1: Final Confirmation Strategy
**Status:** NEEDS IMPLEMENTATION
**File to Create:** `src/ai/router/stage_handlers/strategies/common/confirm_job.py`

**What it needs:**
- Reusable confirmation strategy for all jobs
- Format job summaries (ReadSQL, CompareSQL, WriteData, SendEmail)
- Handle: yes/confirm → execute, edit <param> → edit, cancel → abort
- Show all parameters before execution

**Integration Points:**
1. Update `gather_params.py` for CompareSQL - transition to CONFIRM_COMPARE_SQL_JOB instead of executing
2. Update `execute_sql.py` for ReadSQL - transition to CONFIRM_READ_SQL_JOB
3. Update WriteData and SendEmail similarly

### Priority 2: Global Handler Integration
**Status:** NEEDS IMPLEMENTATION
**Files to Modify:**
- `src/ai/router/stage_handlers/readsql_handler.py`
- `src/ai/router/stage_handlers/comparesql_handler.py`
- `src/ai/router/stage_handlers/writedata_handler.py`
- `src/ai/router/stage_handlers/sendemail_handler.py`

**What to add to each handler's `handle()` method:**
```python
async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
    # NEW: Check global commands first
    from src.ai.router.global_command_handler import GlobalCommandHandler
    from src.ai.router.utils.edit_target_resolver import EditTargetResolver

    global_cmd = GlobalCommandHandler.check_global_command(memory, user_input)

    if global_cmd == "reset":
        result = GlobalCommandHandler.handle_reset(memory)
        memory.stage = result["transition_to"]
        return StageHandlerResult(
            response=result["message"],
            next_stage=result["transition_to"]
        )

    elif global_cmd == "back":
        result = GlobalCommandHandler.handle_back(memory)
        if result["transition_to"]:
            memory.stage = result["transition_to"]
        return StageHandlerResult(
            response=result["message"],
            next_stage=result.get("transition_to")
        )

    elif global_cmd == "review":
        result = GlobalCommandHandler.handle_review(memory)
        return StageHandlerResult(
            response=result["message"],
            next_stage=None  # Stay in current stage
        )

    elif global_cmd == "edit":
        edit_resolver = EditTargetResolver()
        result = GlobalCommandHandler.handle_edit(memory, user_input, edit_resolver)
        if result["transition_to"]:
            memory.stage = result["transition_to"]
        return StageHandlerResult(
            response=result["message"],
            next_stage=result.get("transition_to")
        )

    # Existing stage-specific logic...
    strategy = self._registry.get_strategy(memory.stage)
    return await strategy.execute(memory, user_input)
```

### Priority 3: SQL Confirmation Edit Support
**Status:** NEEDS IMPLEMENTATION
**Files to Modify:**
- `src/ai/router/stage_handlers/strategies/readsql/confirm_sql.py`
- `src/ai/router/stage_handlers/strategies/comparesql/confirm_first_sql.py`
- `src/ai/router/stage_handlers/strategies/comparesql/confirm_second_sql.py`

**What to add:**
Detect "edit", "change", "back" commands during SQL confirmation and allow users to go back to SQL generation.

---

## 📊 Summary

### ✅ Done (Foundation - 60% complete)
1. Global command handler with reset/back/review/edit
2. Memory get_editable_summary() method
3. Stage history tracking (go_back, reset_history)
4. Edit target resolver with fuzzy matching
5. Confirmation stage enums

### 🚧 TODO (User-Facing Features - 40% remaining)
6. Create confirmation strategy (shows summary before execution)
7. Integrate global handler into all 4 handlers (ReadSQL, CompareSQL, WriteData, SendEmail)
8. Add edit support to SQL confirmation stages
9. Update validators to transition to confirmation instead of executing
10. Test end-to-end flows

---

## 🎯 What Works Now

### Commands Available (Once integrated):
- `reset` - Clear everything and start over ✅ (handler ready)
- `back` - Go to previous stage ✅ (handler ready)
- `review` / `summary` - See current state ✅ (handler ready)
- `edit <param>` - Edit any parameter ✅ (resolver ready)

### What Still Needs Integration:
- Handlers need to call global command handler ❌
- Confirmation stages need strategy implementation ❌
- SQL confirmation stages need edit detection ❌

---

## 🚀 Next Steps to Complete

### Step 1: Create Confirmation Strategy (1-2 hours)
Create `src/ai/router/stage_handlers/strategies/common/confirm_job.py` with:
- Job summary formatting for all 4 job types
- Handle yes/confirm/edit/cancel commands
- Integration with edit resolver

### Step 2: Integrate Global Handler (30 min per handler = 2 hours)
Add global command checking to:
- ReadSQL handler
- CompareSQL handler
- WriteData handler
- SendEmail handler

### Step 3: Update Execution Paths (1-2 hours)
Modify execution strategies to go to confirmation instead of executing directly:
- `gather_params.py` (CompareSQL)
- `execute_sql.py` (ReadSQL)
- WriteData execution
- SendEmail execution

### Step 4: Testing (2-3 hours)
Test all commands and flows:
- Reset at every stage
- Back through conversation
- Edit from confirmation
- Edit SQL after confirmation
- Review command

**Total Time: ~8-10 hours of focused development**

---

## 💡 Recommendation

The foundation is solid! What remains is primarily "wiring" - integrating the components we've built.

**Quick Win Option:** If you want to see immediate results, I can focus on just **Priority 1** (Final Confirmation) for CompareSQL. This alone will add significant value by letting users review before executing.

**Full Implementation:** Continue with all priorities for complete global edit/confirmation across all jobs.

What would you like me to focus on next?
