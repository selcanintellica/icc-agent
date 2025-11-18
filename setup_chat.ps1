# Quick Setup Script for ICC Agent Chat Interface

Write-Host "=" -NoNewline
Write-Host ("=" * 58)
Write-Host "🚀 ICC Agent Chat Interface Setup" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 58)
Write-Host ""

# Check Python
Write-Host "📦 Checking Python installation..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python not found! Please install Python 3.9+" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Python found" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "📦 Installing Dash dependencies..." -ForegroundColor Yellow
pip install dash dash-bootstrap-components plotly

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Check Ollama
Write-Host "🤖 Checking Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434" -Method Get -ErrorAction SilentlyContinue
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama is not running. Please start it with 'ollama serve'" -ForegroundColor Yellow
}
Write-Host ""

# Check model
Write-Host "🔍 Checking for qwen2.5:7b model..." -ForegroundColor Yellow
$models = ollama list 2>&1 | Out-String
if ($models -like "*qwen*") {
    Write-Host "✅ Model found" -ForegroundColor Green
} else {
    Write-Host "⚠️  Model not found. Run: ollama pull qwen2.5:7b" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=" -NoNewline
Write-Host ("=" * 58)
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "=" -NoNewline
Write-Host ("=" * 58)
Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Make sure Ollama is running: ollama serve"
Write-Host "   2. Start the chat interface: python app.py"
Write-Host "   3. Open browser to: http://localhost:8050"
Write-Host ""
Write-Host "💡 Example queries to try:" -ForegroundColor Cyan
Write-Host "   - Get customers from USA"
Write-Host "   - Show active orders"
Write-Host "   - Email data to test@example.com"
Write-Host ""
