@echo off
REM Start ICC Agent FastAPI Backend
REM This script starts the FastAPI backend server on port 8000

echo.
echo ============================================================
echo Starting ICC Agent FastAPI Backend
echo ============================================================
echo.
echo API will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Ensure we're in the project root
cd /d %~dp0

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Add current directory to PYTHONPATH
set PYTHONPATH=%CD%;%PYTHONPATH%

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
