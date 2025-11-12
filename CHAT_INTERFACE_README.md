# 🚀 ICC Agent Chat Interface - Quick Start

A beautiful web-based chat interface to test your ICC Agent with visual feedback!

![Chat Interface](https://img.shields.io/badge/Framework-Dash-blue)
![LLM](https://img.shields.io/badge/LLM-7B_Local-green)
![Status](https://img.shields.io/badge/Status-Ready-success)

---

## ⚡ Quick Start (3 Steps)

### Step 1: Install Dependencies
```powershell
# Run the setup script
.\setup_chat.ps1

# Or install manually
pip install dash dash-bootstrap-components plotly
```

### Step 2: Start Ollama (if not running)
```powershell
ollama serve
```

### Step 3: Run the Chat App
```powershell
python app.py
```

### Step 4: Open Browser
Navigate to: **http://localhost:8050**

---

## 🎯 What You Get

✨ **Beautiful Chat UI**
- Clean, modern interface
- Real-time message updates
- Color-coded messages

🔧 **Tool Visibility**
- See what tools the agent calls
- View tool arguments
- Monitor execution flow

💡 **Quick Examples**
- Pre-built query buttons
- Learn by example
- Fast testing

📊 **Visual Feedback**
- User messages (blue)
- Agent responses (green)
- Tool calls (orange)
- Errors (red)

---

## 💬 Example Conversations

**You:** Get customers from USA

**Agent:** I'll create a job to get USA customers.
```json
Tool: build_simple_sql_query
Args: {
  "table_name": "customers",
  "filters": {"country": "USA"}
}
```
```json
Tool: read_sql_job
Args: {
  "query": "SELECT * FROM customers WHERE country = 'USA'",
  "connection": "prod"
}
```
**Agent:** Job created successfully! Job ID: 12345

---

## 🎨 Features

| Feature | Description |
|---------|-------------|
| **Real-time Chat** | Instant message updates |
| **Tool Tracking** | See all tool calls and arguments |
| **Error Handling** | Clear error messages |
| **Example Queries** | Click-to-try examples |
| **Responsive Design** | Works on all screen sizes |
| **Dark/Light Theme** | Customizable themes |

---

## 📝 Try These Queries

### Basic Queries
```
Get customers from USA
Show all orders
Get active users
```

### Query and Save
```
Get customers from USA and save to usa_customers table
Read orders where status is pending and write to pending_orders
```

### Email Queries
```
Email customer list to manager@example.com
Send sales data to team@company.com
```

---

## 🛠️ Configuration

### Change Model
Edit `src/ai/configs/icc_config.py`:
```python
model="qwen2.5:7b"  # Change to your model
```

### Change Port
Edit `app.py`:
```python
app.run_server(port=8050)  # Change port
```

### Change Theme
Edit `app.py`:
```python
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
# Try: DARKLY, CYBORG, SOLAR, etc.
```

---

## 🐛 Troubleshooting

### Ollama Not Running?
```powershell
ollama serve
```

### Model Not Found?
```powershell
ollama pull qwen2.5:7b
```

### Port Already in Use?
Change port in `app.py` or kill the process:
```powershell
netstat -ano | findstr :8050
taskkill /PID <PID> /F
```

### Dependencies Missing?
```powershell
pip install -r requirements_app.txt
```

---

## 📁 Files Created

```
ICC_try/
├── app.py                      # Main chat application
├── requirements_app.txt        # Dash dependencies
├── setup_chat.ps1             # Setup script
├── APP_USAGE.md               # Detailed usage guide
└── CHAT_INTERFACE_README.md   # This file
```

---

## 🎯 Architecture

```
Browser (localhost:8050)
    ↓
Dash Web Interface
    ↓
ICC Agent (LangGraph + 7B LLM)
    ↓
Tools (SQL generation, Job creation)
    ↓
Database / Email Services
```

---

## 💡 Tips

1. ✅ **Start with examples** - Click the example buttons first
2. ✅ **Watch tool calls** - See what the agent does step-by-step
3. ✅ **Check terminal** - Logs show detailed execution
4. ✅ **Use simple queries** - 7B models work best with clear requests
5. ✅ **Be specific** - Include table names and connections

---

## 🌟 Next Steps

1. Test with simple queries
2. Try chaining operations (read → write)
3. Experiment with filters
4. Monitor tool execution
5. Check logs for debugging

---

## 📚 Documentation

- **Detailed Usage**: See `APP_USAGE.md`
- **Toolkit Guide**: See `7B_LLM_OPTIMIZATION_GUIDE.md`
- **Tool Comparison**: See `TOOLKIT_COMPARISON.md`

---

## 🤝 Support

Having issues? Check:
1. Terminal logs
2. Ollama status: `curl http://localhost:11434`
3. Model availability: `ollama list`
4. Dependencies: `pip list | grep dash`

---

## 🎉 Enjoy Testing!

Your ICC Agent is ready to chat! Open http://localhost:8050 and start asking questions!

**Happy testing! 🚀**
