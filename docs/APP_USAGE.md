# ICC Agent Chat Interface

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_app.txt
```

Or install individually:
```bash
pip install dash dash-bootstrap-components plotly
```

### 2. Make Sure Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434

# If not, start Ollama
ollama serve

# Pull your model if not already downloaded
ollama pull qwen2.5:7b
```

### 3. Run the Chat Interface

```bash
python app.py
```

### 4. Open Browser

Navigate to: **http://localhost:8050**

---

## 🎯 Features

- **💬 Chat Interface**: Clean, modern web-based chat UI
- **🔧 Tool Visibility**: See what tools the agent calls in real-time
- **💡 Example Queries**: Pre-built example buttons for quick testing
- **📊 Real-time Updates**: Watch the agent think and execute tools
- **🎨 Color-coded Messages**: 
  - Blue: Your messages
  - Green: Agent responses
  - Orange: Tool calls
  - Red: Errors

---

## 📝 Example Queries to Try

### Simple Queries:
```
- Get customers from USA
- Show all orders
- Get active users
```

### Query and Save:
```
- Get customers from USA and save to usa_customers table
- Read orders where status is pending and write to pending_orders
```

### Email Queries:
```
- Email customer list to manager@example.com
- Send sales data to team@company.com with subject "Q1 Report"
```

### With Filters:
```
- Get customers where country is USA and status is active
- Show orders where status is pending
```

---

## 🛠️ Configuration

### Change Model

Edit `src/ai/configs/icc_config.py`:
```python
model = ChatOllama(
    model="qwen2.5:7b",  # Change model here
    temperature=0.1,
    ...
)
```

### Change Port

Edit `app.py`:
```python
app.run_server(debug=True, host="0.0.0.0", port=8050)  # Change port here
```

### Change Toolkit

To switch between toolkits, edit `src/ai/configs/icc_config.py`:
```python
# For 7B models (recommended)
from src.ai.toolkits.icc_toolkit_simple import SimplifiedICCToolkit
from src.ai.prompts.icc_prompt_simple import SimplifiedICCPrompt

# Or for larger models
from src.ai.toolkits.icc_toolkit_enhanced import EnhancedICCToolkit
from src.ai.prompts.icc_prompt_enhanced import EnhancedICCPrompt
```

---

## 🐛 Troubleshooting

### Issue: "Connection refused" to Ollama

**Solution:**
```bash
# Start Ollama
ollama serve

# Or check if running
ps aux | grep ollama
```

### Issue: Model not found

**Solution:**
```bash
# Pull the model
ollama pull qwen2.5:7b

# List available models
ollama list
```

### Issue: Agent not responding

**Solution:**
1. Check terminal for error messages
2. Verify database connections in `.env` file
3. Check if model is loaded: `ollama list`
4. Restart the app

### Issue: Tool calls failing

**Solution:**
1. Check `src/repositories/` for API endpoint configuration
2. Verify database connections are accessible
3. Check logs in terminal

---

## 🎨 Customization

### Change Theme

Edit `app.py`:
```python
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])  # Dark theme
# Other themes: BOOTSTRAP, CERULEAN, COSMO, CYBORG, DARKLY, FLATLY, etc.
```

### Modify Layout

The layout is in `app.py` using Dash Bootstrap Components. Key sections:
- **Chat history**: `id="chat-history"`
- **Input area**: `id="user-input"`
- **Example buttons**: `id="example-1"`, etc.

### Add Custom Examples

Edit the example queries in `app.py`:
```python
dbc.Button("Your custom query", id="example-4", ...),
```

Then add handler in callback:
```python
elif button_id == "example-4":
    user_input = "Your custom query text"
```

---

## 📊 Architecture

```
User Input
    ↓
Dash Callback
    ↓
ICC Agent (LangGraph)
    ↓
Tools (build_sql, read_sql_job, write_data_job, send_email_job)
    ↓
Response Display
```

---

## 🔍 Monitoring

### View Agent Logs

The terminal running `app.py` will show:
- User messages
- Tool calls
- Agent reasoning
- Errors

### Debug Mode

Debug mode is enabled by default:
```python
app.run_server(debug=True)  # Shows detailed errors
```

Disable for production:
```python
app.run_server(debug=False)
```

---

## 🚀 Deployment

### Run in Production

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn app:server -b 0.0.0.0:8050
```

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements_app.txt .
RUN pip install -r requirements_app.txt

COPY . .

CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t icc-agent-chat .
docker run -p 8050:8050 icc-agent-chat
```

---

## 💡 Tips

1. **Start Simple**: Test with basic queries first
2. **Check Examples**: Use the example buttons to see expected format
3. **Watch Tool Calls**: The orange boxes show what tools are being used
4. **Connection String**: Make sure database connections are configured in `.env`
5. **Model Selection**: Use 7B models with the simplified toolkit

---

## 📚 Additional Resources

- **Dash Documentation**: https://dash.plotly.com/
- **LangGraph Documentation**: https://python.langchain.com/docs/langgraph
- **Ollama Models**: https://ollama.com/library

---

## 🤝 Support

If you encounter issues:
1. Check the terminal for error logs
2. Verify all dependencies are installed
3. Ensure Ollama is running
4. Check database connections
5. Review the toolkit configuration

Happy chatting! 🎉
