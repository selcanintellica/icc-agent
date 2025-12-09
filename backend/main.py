"""
FastAPI Backend for ICC Agent

A REST API backend that exposes ICC Agent functionality for integration
with external frontends. Keeps Dash UI (app.py) for testing.

Run this file to start the API server:
    uvicorn backend.main:app --reload --port 8000

API Documentation available at:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

from dotenv import load_dotenv
load_dotenv(override=True)

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[logging.StreamHandler()]
)

# Suppress verbose logs
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Import API routes
from backend.api.routes import chat, connections, health

# Import services for lifecycle management
from src.services import (
    get_router_service,
    get_session_manager,
    get_connection_service
)

# Enable prompt logging if configured
from src.utils.prompt_logger import enable_prompt_logging
if os.getenv("ENABLE_PROMPT_LOGGING", "false").lower() in ["true", "1", "yes"]:
    log_dir = os.getenv("PROMPT_LOG_DIR", "prompt_logs")
    enable_prompt_logging(log_dir)
    logger.info(f"Prompt logging enabled - saving to {log_dir}/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown events.
    """
    # Startup
    logger.info("="*60)
    logger.info("Starting ICC Agent FastAPI Backend")
    logger.info("="*60)
    
    # Initialize services (singletons)
    router_service = get_router_service()
    session_manager = get_session_manager()
    connection_service = get_connection_service()
    
    logger.info("✓ Router service initialized")
    logger.info("✓ Session manager initialized")
    logger.info("✓ Connection service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ICC Agent Backend")


# Create FastAPI application
app = FastAPI(
    title="ICC Agent API",
    description="Natural language interface for database operations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Configuration - allow frontend from different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions and return structured error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    from src.errors import ErrorHandler
    error_info = ErrorHandler.handle_error(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": error_info.code.value,
                "message": error_info.message,
                "details": error_info.details,
                "category": error_info.category.value
            }
        }
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(connections.router, prefix="/api/connections", tags=["Connections"])


@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "ICC Agent API",
        "version": "1.0.0",
        "description": "Natural language interface for database operations",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
