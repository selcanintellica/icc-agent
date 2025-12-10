#!/bin/bash
# Start ICC Agent FastAPI Backend
# This script starts the FastAPI backend server on port 8000

echo ""
echo "============================================================"
echo "Starting ICC Agent FastAPI Backend"
echo "============================================================"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Add current directory to PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
