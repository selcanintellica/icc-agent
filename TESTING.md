# ICC Agent Backend - Testing Guide

## 🧪 Testing the Backend

This guide helps you verify that the backend is working correctly.

---

## Quick Health Check

### 1. Check if Backend is Running

```bash
# Test the health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "...",
#   "services": {
#     "router": "ok",
#     "session_manager": "ok",
#     "connection_service": "ok"
#   }
# }
```

### 2. Open API Documentation

Open in your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You should see interactive API documentation.

---

## Automated Test Script

### Run the Test Suite

```bash
# Install requests if needed
pip install requests

# Run all tests
python test_backend.py

# Test a different URL
python test_backend.py --url http://localhost:8001
```

The test script will:
- ✓ Check health endpoint
- ✓ Create a session
- ✓ Get database connections
- ✓ Send a message
- ✓ Retrieve session info
- ✓ Delete session
- ✓ Verify API documentation

**Expected Output:**
```
============================================================
ICC AGENT BACKEND - API TEST SUITE
============================================================
Testing backend at: http://localhost:8000

============================================================
TEST 1: Health Check
============================================================
Status: healthy
Version: 1.0.0
Services: {'router': 'ok', 'session_manager': 'ok', 'connection_service': 'ok'}
✓ Health Check
  Backend is healthy

... (more tests)

============================================================
TEST SUMMARY
============================================================
Tests Passed: 7
Tests Failed: 0
Total Tests: 7

✓ ALL TESTS PASSED! Backend is working correctly.
```

---

## Manual Testing with curl

### Test 1: Health Check

```bash
curl http://localhost:8000/api/health
```

### Test 2: Create Session

```bash
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{}'
```

Save the `session_id` from the response.

### Test 3: Send Message

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID_HERE",
    "message": "help"
  }'
```

### Test 4: Get Connections

```bash
curl http://localhost:8000/api/connections
```

### Test 5: Get Session Info

```bash
curl http://localhost:8000/api/chat/sessions/YOUR_SESSION_ID_HERE
```

### Test 6: Delete Session

```bash
curl -X DELETE http://localhost:8000/api/chat/sessions/YOUR_SESSION_ID_HERE
```

---

## Testing with PowerShell (Windows)

### Test Health Check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
```

### Create Session

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/chat/sessions" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{}'

$sessionId = $response.session_id
Write-Host "Session ID: $sessionId"
```

### Send Message

```powershell
$body = @{
    session_id = $sessionId
    message = "help"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/chat/message" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

---

## 🐳 Testing Docker Deployment

### 1. Build Docker Image

```bash
# Build the image
docker build -t icc-agent-backend:test .

# Verify the image was created
docker images | grep icc-agent-backend
```

### 2. Run Docker Container

```bash
# Run the container
docker run -d -p 8000:8000 --name icc-test icc-agent-backend:test

# Check if container is running
docker ps | grep icc-test
```

### 3. Check Logs

```bash
# View container logs
docker logs icc-test

# Follow logs in real-time
docker logs -f icc-test
```

Expected log output:
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2025-12-09 10:43:44,123 - backend.main - INFO - Starting ICC Agent FastAPI Backend
2025-12-09 10:43:44,124 - backend.main - INFO - ✓ Router service initialized
2025-12-09 10:43:44,124 - backend.main - INFO - ✓ Session manager initialized
2025-12-09 10:43:44,124 - backend.main - INFO - ✓ Connection service initialized
INFO:     Application startup complete.
```

### 4. Test the Containerized Backend

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Or run the test script
python test_backend.py

# Or open in browser
start http://localhost:8000/docs  # Windows
open http://localhost:8000/docs   # Mac
xdg-open http://localhost:8000/docs  # Linux
```

### 5. Test Docker Compose

```bash
# Start with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test the API
curl http://localhost:8000/api/health

# Stop
docker-compose down
```

### 6. Verify Container Health

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' icc-test

# Should return: healthy

# View detailed health check logs
docker inspect --format='{{json .State.Health}}' icc-test | python -m json.tool
```

### 7. Test Container Restart

```bash
# Restart container
docker restart icc-test

# Wait a few seconds
sleep 5

# Verify it's still healthy
curl http://localhost:8000/api/health
```

### 8. Clean Up

```bash
# Stop container
docker stop icc-test

# Remove container
docker rm icc-test

# Remove image (optional)
docker rmi icc-agent-backend:test
```

---

## Testing Checklist

### Local Backend Testing

- [ ] Backend starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] Can create a session
- [ ] Can send messages
- [ ] Can get connections
- [ ] API documentation accessible at /docs
- [ ] Logs show no errors

### Docker Testing

- [ ] Docker image builds successfully
- [ ] Container starts without errors
- [ ] Container health check passes
- [ ] Health endpoint returns 200 OK
- [ ] All API endpoints work
- [ ] Container logs look normal
- [ ] Container survives restart
- [ ] Can stop and remove cleanly

### Integration Testing

- [ ] Can send multiple messages in sequence
- [ ] Session state persists across messages
- [ ] Dropdowns work correctly
- [ ] Error handling works
- [ ] CORS works (if testing from frontend)
- [ ] Long-running requests don't timeout

---

## Common Issues & Solutions

### Issue: "Connection refused"

```bash
# Check if backend is running
docker ps  # for Docker
netstat -an | grep 8000  # for local

# Solution: Start the backend
docker-compose up -d
# or
.\start_backend.bat
```

### Issue: "Port 8000 already in use"

```bash
# Find what's using the port
# Windows PowerShell:
Get-NetTCPConnection -LocalPort 8000

# Linux/Mac:
lsof -i :8000

# Solution: Stop the conflicting process or use a different port
docker run -p 8001:8000 icc-agent-backend:test
```

### Issue: "Module not found" in Docker

```bash
# Rebuild without cache
docker build --no-cache -t icc-agent-backend:test .
```

### Issue: Health check failing

```bash
# Check backend logs
docker logs icc-test

# Test manually inside container
docker exec -it icc-test curl http://localhost:8000/api/health

# Check if services initialized
docker logs icc-test | grep "initialized"
```

### Issue: Slow response times

```bash
# Check container resources
docker stats icc-test

# Check if LLM service (Ollama) is running
curl http://localhost:11434/api/tags
```

---

## Performance Testing

### Basic Load Test

```bash
# Install Apache Bench (if needed)
# Ubuntu: sudo apt-get install apache2-utils
# Mac: brew install httpd

# Run load test
ab -n 100 -c 10 http://localhost:8000/api/health

# 100 requests, 10 concurrent
```

### Using Python

```python
import concurrent.futures
import requests
import time

def test_endpoint():
    start = time.time()
    response = requests.get("http://localhost:8000/api/health")
    duration = time.time() - start
    return response.status_code, duration

# Run 50 concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(test_endpoint) for _ in range(50)]
    results = [f.result() for f in futures]

# Analyze results
success_count = sum(1 for code, _ in results if code == 200)
avg_duration = sum(d for _, d in results) / len(results)

print(f"Success: {success_count}/50")
print(f"Average response time: {avg_duration:.3f}s")
```

---

## Monitoring During Tests

### Watch Logs in Real-Time

```bash
# Docker
docker logs -f icc-test

# Docker Compose
docker-compose logs -f

# Local (if using systemd)
journalctl -u icc-agent-backend -f
```

### Monitor Resource Usage

```bash
# Docker container stats
docker stats icc-test

# System resources
htop  # Linux/Mac
# or Windows Task Manager
```

---

## Next Steps After Testing

If all tests pass:

1. ✅ **Local Backend**: Ready for development
2. ✅ **Docker**: Ready to share with other team
3. ✅ **Production**: Ready for deployment

If tests fail:
1. Check logs for errors
2. Verify all dependencies installed
3. Check configuration files
4. Review [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section

---

## Getting Help

If tests continue to fail:
1. Check the logs: `docker logs icc-test`
2. Verify environment variables
3. Test health endpoint manually
4. Review [README_BACKEND.md](README_BACKEND.md)
5. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting
