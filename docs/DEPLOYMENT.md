# ICC Agent Backend - Deployment Guide

## Overview

This guide provides instructions for deploying the ICC Agent FastAPI backend in different environments.

---

## 🐳 Docker Deployment (Recommended)

Docker provides the easiest way to deploy the backend with all dependencies.

### Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 1.29+)

### Quick Start

```bash
# 1. Clone/receive the repository
cd ICC_agent

# 2. Configure environment (optional)
cp .env.example .env
# Edit .env if needed

# 3. Build and start
docker-compose up -d

# 4. Verify
curl http://localhost:8000/api/health

# 5. View logs
docker-compose logs -f

# 6. Stop
docker-compose down
```

### Build Docker Image

```bash
# Build image
docker build -t icc-agent-backend:latest .

# Run container
docker run -d \
  --name icc-agent-backend \
  -p 8000:8000 \
  -e CORS_ORIGINS="*" \
  -e MODEL_NAME="qwen3:8b" \
  -v $(pwd)/db_config.json:/app/db_config.json:ro \
  icc-agent-backend:latest

# Check logs
docker logs -f icc-agent-backend

# Stop container
docker stop icc-agent-backend
docker rm icc-agent-backend
```

### Push to Docker Registry

For the other team to easily pull your image:

```bash
# Tag for your registry
docker tag icc-agent-backend:latest your-registry.com/icc-agent-backend:latest

# Push to registry
docker push your-registry.com/icc-agent-backend:latest
```

Then the other team can use:

```bash
docker pull your-registry.com/icc-agent-backend:latest
docker run -d -p 8000:8000 your-registry.com/icc-agent-backend:latest
```

---

## 🔧 Manual Deployment

### Linux/Mac

```bash
# 1. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
export PYTHONPATH=$(pwd)
export API_HOST=0.0.0.0
export API_PORT=8000

# 4. Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Or use the startup script
./scripts/start_backend.sh
```

### Windows

```powershell
# 1. Set up virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
.\scripts\start_backend.bat
```

---

## 🚀 Production Deployment

### Using Gunicorn (Linux/Mac)

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Using Systemd Service (Linux)

Create `/etc/systemd/system/icc-agent-backend.service`:

```ini
[Unit]
Description=ICC Agent FastAPI Backend
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/icc-agent
Environment="PATH=/opt/icc-agent/.venv/bin"
Environment="PYTHONPATH=/opt/icc-agent"
ExecStart=/opt/icc-agent/.venv/bin/gunicorn backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable icc-agent-backend
sudo systemctl start icc-agent-backend
sudo systemctl status icc-agent-backend
```

---

## 🌐 Reverse Proxy Setup

### Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

---

## ☁️ Cloud Deployment

### AWS ECS with Fargate

1. **Push image to ECR**:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
docker tag icc-agent-backend:latest your-account.dkr.ecr.us-east-1.amazonaws.com/icc-agent-backend:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/icc-agent-backend:latest
```

2. **Create ECS Task Definition**:
```json
{
  "family": "icc-agent-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [{
    "name": "icc-agent-backend",
    "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/icc-agent-backend:latest",
    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "CORS_ORIGINS", "value": "*"},
      {"name": "MODEL_NAME", "value": "qwen3:8b"}
    ],
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 40
    }
  }]
}
```

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name icc-agent-backend \
  --image your-registry.azurecr.io/icc-agent-backend:latest \
  --dns-name-label icc-agent \
  --ports 8000 \
  --environment-variables \
    'CORS_ORIGINS=*' \
    'MODEL_NAME=qwen3:8b'
```

### Google Cloud Run

```bash
gcloud run deploy icc-agent-backend \
  --image gcr.io/your-project/icc-agent-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars CORS_ORIGINS=*,MODEL_NAME=qwen3:8b
```

---

## 📊 Kubernetes Deployment

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: icc-agent-backend
  labels:
    app: icc-agent-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: icc-agent-backend
  template:
    metadata:
      labels:
        app: icc-agent-backend
    spec:
      containers:
      - name: icc-agent-backend
        image: your-registry.com/icc-agent-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: CORS_ORIGINS
          value: "*"
        - name: MODEL_NAME
          value: "qwen3:8b"
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8000"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: icc-agent-backend
spec:
  selector:
    app: icc-agent-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f deployment.yaml
kubectl get services icc-agent-backend
```

---

## 🔐 Security Considerations

### 1. CORS Configuration
```bash
# Restrict to specific origins in production
export CORS_ORIGINS="https://your-frontend.com,https://app.your-domain.com"
```

### 2. Environment Variables
Never commit sensitive data. Use:
- Docker secrets
- Kubernetes secrets
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

### 3. HTTPS/TLS
Always use HTTPS in production:
- Use a reverse proxy (Nginx, Traefik)
- Use cloud load balancers with SSL certificates
- Let's Encrypt for free certificates

### 4. API Authentication
Consider adding API key authentication:
```python
# In backend/main.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        if api_key != os.getenv("API_KEY"):
            raise HTTPException(status_code=401, detail="Invalid API key")
    return await call_next(request)
```

---

## 📦 Sharing with Other Team

### Option 1: Docker Image (Recommended)

**Build and push:**
```bash
# Build
docker build -t icc-agent-backend:1.0.0 .

# Tag for registry
docker tag icc-agent-backend:1.0.0 your-registry.com/icc-agent-backend:1.0.0
docker tag icc-agent-backend:1.0.0 your-registry.com/icc-agent-backend:latest

# Push
docker push your-registry.com/icc-agent-backend:1.0.0
docker push your-registry.com/icc-agent-backend:latest
```

**Provide them with:**
```bash
# Quick start command
docker run -d -p 8000:8000 your-registry.com/icc-agent-backend:latest
```

### Option 2: Docker Compose File

Provide them with `docker-compose.yml`:
```bash
# They just need to run:
docker-compose up -d
```

### Option 3: Source Code + Instructions

Provide:
- Source code repository access
- Main `README.md` (integration guide with API documentation)
- `DEPLOYMENT.md` (this file)
- `requirements.txt`
- `db_config.json` (or template)

---

## 🔍 Monitoring

### Health Checks

```bash
# Manual check
curl http://localhost:8000/api/health

# Automated monitoring
watch -n 30 'curl -s http://localhost:8000/api/health | jq'
```

### Logs

```bash
# Docker
docker logs -f icc-agent-backend

# Docker Compose
docker-compose logs -f

# Systemd
journalctl -u icc-agent-backend -f

# Kubernetes
kubectl logs -f deployment/icc-agent-backend
```

### Metrics

Consider adding:
- Prometheus metrics
- Grafana dashboards
- Application Performance Monitoring (APM)
- Log aggregation (ELK stack, Splunk)

---

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker logs icc-agent-backend

# Check if port is in use
netstat -an | grep 8000

# Try different port
docker run -p 8001:8000 icc-agent-backend:latest
```

### Module not found errors

```bash
# Rebuild image (no cache)
docker build --no-cache -t icc-agent-backend:latest .
```

### Permission errors

```bash
# Run with specific user
docker run --user 1000:1000 -p 8000:8000 icc-agent-backend:latest
```

### Health check failing

```bash
# Check health manually
docker exec -it icc-agent-backend curl http://localhost:8000/api/health

# Check if backend is listening
docker exec -it icc-agent-backend netstat -tlnp
```

---

## 📞 Support

For deployment issues:
1. Check logs first
2. Verify environment variables
3. Test health endpoint
4. Check network connectivity
5. Review main [README.md](../README.md) for API details and integration examples

---

## 📝 Checklist for Other Team

- [ ] Docker installed and running
- [ ] Pull/build Docker image
- [ ] Configure environment variables (CORS_ORIGINS, etc.)
- [ ] Mount db_config.json (if needed)
- [ ] Start container
- [ ] Verify health endpoint: `http://localhost:8000/api/health`
- [ ] Test API documentation: `http://localhost:8000/docs`
- [ ] Test basic message endpoint
- [ ] Configure reverse proxy (if needed)
- [ ] Set up monitoring/logging
- [ ] Configure backups (if stateful)
