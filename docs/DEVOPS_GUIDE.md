# DevOps Guide - ICC Agent

## Overview

This guide provides deployment, operations, and maintenance procedures for the ICC Agent system. The ICC Agent is a conversational AI system that translates natural language into database operations through a Dash web interface.

## System Requirements

### Hardware Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 20GB

**Recommended:**
- CPU: 8+ cores
- RAM: 16GB+
- Disk: 50GB SSD

### Software Requirements

- **Python**: 3.11+
- **Ollama**: Latest version (for LLM inference)
- **Docker** (optional): 20.10+
- **Docker Compose** (optional): 2.0+
- **Operating System**: Windows, Linux, or macOS

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (Port 8050)
┌───────────────────────────▼─────────────────────────────────┐
│                     Dash Web UI (app.py)                     │
│  • Connection/Schema/Folder Dropdowns                        │
│  • Chat Interface                                            │
│  • Column Mapping UI (CompareSQL)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Service Layer (src/services/)              │
│  • SessionManager: Maintains conversation state              │
│  • ConnectionService: Fetches DB metadata                    │
│  • AuthService: Manages ICC API authentication              │
│  • DropdownHandler: Processes UI selections                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              Router Orchestrator (Singleton)                 │
│  • Stateful conversation flow management                     │
│  • Stage-based routing (FSM pattern)                         │
│  • Handler delegation (Strategy pattern)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      Stage Handlers                          │
│  • ReadSQL: 8 stages                                         │
│  • WriteData: 1 stage                                        │
│  • SendEmail: 2 stages                                       │
│  • CompareSQL: 14 stages                                     │
└─────────┬────────────────────────────────┬──────────────────┘
          │                                │
┌─────────▼──────────┐          ┌─────────▼──────────────────┐
│   LLM Agents       │          │   ICC API Client           │
│  • SQL Agent       │          │  • Connection Management   │
│    (qwen2.5-coder) │          │  • Schema/Table Fetch      │
│  • Job Agent       │          │  • Job Execution           │
│    (qwen3:8b)      │          │  • Authentication          │
└────────────────────┘          └────────────────────────────┘
```

## Deployment Options

### Option 1: Direct Python Deployment (Recommended for Development)

#### 1. Clone Repository

```bash
git clone <repository-url>
cd icc-agent
```

#### 2. Set Up Python Environment

**Option A: Using uv (Recommended - Faster)**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Sync dependencies (creates .venv automatically)
uv sync

# Or install specific package
uv pip install package-name
```

**Option B: Using pip (Traditional)**

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Install and Configure Ollama

```bash
# Download and install from https://ollama.ai

# Pull required models
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b

# Verify installation
ollama list
```

#### 4. Configure Environment

Create `.env` file:

```bash
# ICC API Configuration
ICC_API_BASE_URL=https://172.16.22.13:8084
ICC_USERNAME=admin
ICC_PASSWORD=your_password

# LLM Models
MODEL_NAME=qwen3:8b
SQL_MODEL_NAME=qwen2.5-coder:7b

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8050

# Logging
LOG_LEVEL=INFO
ENABLE_PROMPT_LOGGING=false
```

#### 5. Start Application

**Using uv:**

```bash
# uv automatically handles PYTHONPATH
uv run app.py
```

**Using python directly:**

```bash
# Set PYTHONPATH
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH="$(pwd)"  # Windows PowerShell

# Run application
python app.py
```

Application will be available at `http://localhost:8050`

### Option 2: Docker Deployment (Recommended for Production)

#### 1. Build Docker Image

```bash
docker build -t icc-agent:latest .
```

#### 2. Run Container

```bash
docker run -d \
  --name icc-agent \
  -p 8050:8050 \
  --env-file .env \
  --restart unless-stopped \
  icc-agent:latest
```

#### 3. Monitor Logs

```bash
docker logs -f icc-agent
```

### Option 3: Docker Compose Deployment

#### 1. Configure docker-compose.yml

```yaml
version: '3.8'

services:
  icc-agent:
    build: .
    container_name: icc-agent
    ports:
      - "8050:8050"
    environment:
      - ICC_API_BASE_URL=${ICC_API_BASE_URL}
      - ICC_USERNAME=${ICC_USERNAME}
      - ICC_PASSWORD=${ICC_PASSWORD}
      - MODEL_NAME=qwen3:8b
      - SQL_MODEL_NAME=qwen2.5-coder:7b
    volumes:
      - ./prompt_logs:/app/prompt_logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 2. Deploy

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration Management

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ICC_API_BASE_URL` | ICC API endpoint | Yes | - |
| `ICC_USERNAME` | ICC username | Yes | - |
| `ICC_PASSWORD` | ICC password | Yes | - |
| `MODEL_NAME` | Job agent model | No | qwen3:8b |
| `SQL_MODEL_NAME` | SQL agent model | No | qwen2.5-coder:7b |
| `APP_HOST` | Application host | No | 0.0.0.0 |
| `APP_PORT` | Application port | No | 8050 |
| `LOG_LEVEL` | Logging level | No | INFO |
| `ENABLE_PROMPT_LOGGING` | Save LLM prompts | No | false |
| `PROMPT_LOG_DIR` | Prompt log directory | No | prompt_logs |

### Security Considerations

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use environment-specific configs** - Separate dev/staging/prod
3. **Rotate passwords regularly** - Update ICC credentials
4. **Enable HTTPS** - Use reverse proxy (nginx, Apache) for production
5. **Disable SSL verification carefully** - Only for trusted internal networks

## Monitoring and Observability

### Health Checks

The application doesn't expose a dedicated health endpoint, but you can check:

```bash
# Check if port is listening
netstat -an | grep 8050

# Check container health (Docker)
docker ps
docker inspect icc-agent | grep Health

# Check logs for errors
tail -f prompt_logs/agent.log
```

### Logging

Logs are written to:
- **Console**: Real-time application logs
- **prompt_logs/**: LLM prompt/response logs (if enabled)

Log levels:
- `DEBUG`: Detailed execution flow
- `INFO`: General operations
- `WARNING`: Non-critical issues
- `ERROR`: Operation failures
- `CRITICAL`: System failures

### Metrics to Monitor

1. **Application Metrics**
   - Response time per request
   - Active sessions count
   - LLM call latency
   - Error rates

2. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

3. **Ollama Metrics**
   - Model load time
   - Inference latency
   - GPU utilization (if applicable)

### Monitoring Tools Integration

#### Prometheus (Example)

```python
# Add to app.py
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('icc_requests_total', 'Total requests')
request_duration = Histogram('icc_request_duration_seconds', 'Request duration')

@app.server.route('/metrics')
def metrics():
    return generate_latest()
```

#### Grafana Dashboard

Create dashboard with panels for:
- Request rate over time
- Average response time
- Error rate
- Active sessions
- Memory/CPU usage

## Backup and Recovery

### Data to Back Up

1. **Configuration Files**
   - `.env` (encrypted)
   - `db_config.json` (if using local config)

2. **Session Data** (if persistence enabled)
   - Session state files
   - Conversation history

3. **Logs**
   - `prompt_logs/` directory
   - Application logs

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/icc-agent"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$TIMESTAMP.tar.gz \
  .env.example \
  docker-compose.yml \
  Dockerfile

# Backup logs (last 7 days)
find prompt_logs/ -name "*.log" -mtime -7 \
  -exec tar -czf $BACKUP_DIR/logs_$TIMESTAMP.tar.gz {} +

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Recovery Procedure

1. **Stop Application**
   ```bash
   docker-compose down
   # OR
   pkill -f app.py
   ```

2. **Restore Configuration**
   ```bash
   tar -xzf config_backup.tar.gz
   ```

3. **Restore Logs** (optional)
   ```bash
   tar -xzf logs_backup.tar.gz -C prompt_logs/
   ```

4. **Restart Application**
   ```bash
   docker-compose up -d
   # OR
   python app.py
   ```

## Scaling Considerations

### Horizontal Scaling

To scale horizontally:

1. **Add Load Balancer**
   ```nginx
   # nginx.conf
   upstream icc_agents {
       server icc-agent-1:8050;
       server icc-agent-2:8050;
       server icc-agent-3:8050;
   }

   server {
       listen 80;
       location / {
           proxy_pass http://icc_agents;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. **Session Persistence**
   - Implement Redis-based session storage
   - Use sticky sessions in load balancer

3. **Shared Ollama Instance**
   - Run Ollama as separate service
   - Configure `OLLAMA_HOST` environment variable

### Vertical Scaling

To scale vertically:
- Increase CPU/RAM for container
- Adjust Ollama model concurrency
- Optimize Python worker threads

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms**: Container exits immediately or Python crashes

**Diagnosis**:
```bash
# Check logs
docker logs icc-agent
# OR
python app.py

# Common errors:
# - ModuleNotFoundError: Check PYTHONPATH
# - Port already in use: Change APP_PORT
# - Ollama connection failed: Check Ollama service
```

**Solutions**:
```bash
# Fix PYTHONPATH
export PYTHONPATH=$(pwd)

# Kill process using port
lsof -ti:8050 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8050   # Windows

# Restart Ollama
ollama serve
```

#### 2. LLM Not Responding

**Symptoms**: Timeout errors, slow responses

**Diagnosis**:
```bash
# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b",
  "prompt": "Hello",
  "stream": false
}'

# Check Ollama logs
ollama logs
```

**Solutions**:
```bash
# Restart Ollama
ollama serve

# Pull models again
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b

# Increase keep_alive in src/ai/agents/
# Edit model initialization: keep_alive="3600s"
```

#### 3. ICC API Connection Failed

**Symptoms**: "Authentication failed", "Connection refused"

**Diagnosis**:
```bash
# Test API directly
curl -k -X GET https://172.16.22.13:8084/connection/list \
  -H "Authorization: Basic $(echo -n 'admin:password' | base64)" \
  -H "TokenKey: your-token"
```

**Solutions**:
- Verify ICC_API_BASE_URL is correct
- Check username/password in .env
- Ensure ICC API is accessible from container
- For SSL issues: Verify certificate or adjust SSL settings

#### 4. Memory Leak / High Memory Usage

**Symptoms**: Memory usage grows over time

**Diagnosis**:
```bash
# Monitor memory
docker stats icc-agent

# Check for lingering sessions
# Add debug endpoint to app.py
```

**Solutions**:
- Restart container periodically
- Implement session cleanup
- Reduce Ollama keep_alive time
- Add memory limits to docker-compose.yml:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 8G
  ```

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
ENABLE_PROMPT_LOGGING=true

# Restart application
docker-compose restart
```

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Review documentation: `docs/` folder
3. Check GitHub issues
4. Contact development team

## Maintenance Procedures

### Routine Maintenance (Weekly)

```bash
# 1. Check disk space
df -h

# 2. Review logs for errors
grep ERROR prompt_logs/*.log

# 3. Verify Ollama models
ollama list

# 4. Check container health
docker ps
docker inspect icc-agent
```

### Updates and Upgrades

#### Application Updates

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild container
docker-compose build

# 3. Stop old container
docker-compose down

# 4. Start new container
docker-compose up -d

# 5. Verify deployment
curl http://localhost:8050
docker logs icc-agent
```

#### Model Updates

```bash
# Pull updated models
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b

# Restart application to reload models
docker-compose restart
```

### Security Updates

```bash
# Update Python dependencies
pip install -r requirements.txt --upgrade

# Rebuild container with updates
docker-compose build --no-cache

# Deploy updated container
docker-compose up -d
```

## Performance Tuning

### Ollama Optimization

```bash
# Increase model keep_alive
# Edit src/ai/agents/sql_agent.py and job_agent.py
# Change: keep_alive="3600s" to keep_alive="7200s"

# Adjust Ollama concurrency
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=2
```

### Application Optimization

```python
# In src/ai/router/router_orchestrator.py
# Adjust router singleton settings

# In src/services/session_manager.py
# Configure session expiration
SESSION_TIMEOUT = 1800  # 30 minutes
```

### Database Connection Pooling

```python
# Add to src/api_clients/connection_api_client.py
import httpx

# Configure connection pooling
limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
client = httpx.AsyncClient(limits=limits)
```

## Disaster Recovery

### Recovery Time Objective (RTO): 30 minutes
### Recovery Point Objective (RPO): 24 hours

### DR Plan

1. **Critical Failure Detection** (< 5 min)
   - Monitor alerts trigger
   - Manual health check fails

2. **Assessment** (< 10 min)
   - Check application logs
   - Verify infrastructure status
   - Determine failure scope

3. **Recovery** (< 15 min)
   - Restore from backup
   - Deploy to failover environment
   - Verify functionality

4. **Post-Recovery** (ongoing)
   - Root cause analysis
   - Update runbooks
   - Implement preventive measures

### Failover Procedure

```bash
# 1. Stop failed instance
docker-compose -f docker-compose.yml down

# 2. Switch to backup configuration
cp .env.backup .env

# 3. Start failover instance
docker-compose -f docker-compose.failover.yml up -d

# 4. Update DNS/Load Balancer
# (depends on infrastructure)

# 5. Verify failover
curl http://failover-host:8050
```

## Compliance and Auditing

### Logging Requirements

- All API calls to ICC API are logged
- User interactions are tracked (session-level)
- LLM prompts/responses can be logged (when enabled)

### Audit Trail

Enable prompt logging for audit trail:

```bash
# In .env
ENABLE_PROMPT_LOGGING=true
PROMPT_LOG_DIR=prompt_logs
```

Logs include:
- Timestamp
- Session ID
- User input
- LLM response
- Tool calls
- Errors

### Data Retention

Configure log retention based on compliance requirements:

```bash
# In backup.sh or logrotate config
# Keep logs for 90 days
find prompt_logs/ -name "*.log" -mtime +90 -delete
```

## Contact and Support

- **DevOps Lead**: [Your contact info]
- **Development Team**: [Team contact]
- **Emergency Contact**: [On-call rotation]

---

**Document Version**: 1.0
**Last Updated**: December 2025
**Next Review**: March 2026
