# Quick Start - Staged Router

## 🚀 Run It Now

### Option 1: Test Script (Recommended First)
```bash
python test_router.py
```
This runs a simulated conversation to verify everything works.

### Option 2: Web Interface
```bash
python app.py
```
Then open: http://localhost:8050

## 💬 Example Conversation

**Try this in the web interface:**

1. **User:** `get all customers`
   - Agent generates SQL

2. **User:** `yes`
   - Agent asks for connection

3. **User:** `oracle_prod`
   - Agent executes query

4. **User:** `write to my_table`
   - Agent asks for connection

5. **User:** `postgres_db`
   - Agent asks drop/truncate

6. **User:** `truncate`
   - Agent writes data

7. **User:** `done`
   - Complete!

## 📋 What Changed

### Before (ReAct Agent):
- Single LLM tries to do everything
- Struggles with small models
- No conversation flow

### After (Staged Router):
- Step-by-step guided flow
- Optimized for small LLMs (1.5B+)
- Automatic tool chaining

## 🔍 Logs Location

All logs appear in the **terminal where you run app.py**, not in the browser.

Look for:
- 🎯 Router stage changes
- 🔮 SQL generation
- 🔍 Parameter extraction
- ⚡ Tool execution

## ✅ That's It!

Your agent now uses staged routing. Test it and see the difference! 🎉
