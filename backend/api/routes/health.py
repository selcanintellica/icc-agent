"""
Health check endpoint for ICC Agent API.

Provides service health and readiness information.
"""

import logging
from datetime import datetime
from fastapi import APIRouter

from backend.api.models import HealthResponse

from src.services import (
    get_router_service,
    get_session_manager,
    get_connection_service
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Verifies that the service and its dependencies are operational.
    
    **Returns:**
    - Service status and version
    - Status of dependent services
    """
    try:
        # Check service initialization
        services_status = {}
        
        # Check router service
        try:
            router_service = get_router_service()
            services_status["router"] = "ok"
        except Exception as e:
            logger.error(f"Router service check failed: {e}")
            services_status["router"] = "error"
        
        # Check session manager
        try:
            session_manager = get_session_manager()
            services_status["session_manager"] = "ok"
        except Exception as e:
            logger.error(f"Session manager check failed: {e}")
            services_status["session_manager"] = "error"
        
        # Check connection service
        try:
            connection_service = get_connection_service()
            services_status["connection_service"] = "ok"
        except Exception as e:
            logger.error(f"Connection service check failed: {e}")
            services_status["connection_service"] = "error"
        
        # Overall status
        overall_status = "healthy" if all(
            status == "ok" for status in services_status.values()
        ) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            version="1.0.0",
            timestamp=datetime.now(),
            services=services_status
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.now(),
            services={"error": str(e)}
        )
