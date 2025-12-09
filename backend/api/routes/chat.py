"""
Chat endpoints for ICC Agent API.

Handles conversational interactions with the agent.
"""

import logging
import uuid
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from backend.api.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    CreateSessionRequest,
    SessionResponse,
    ErrorDetail
)

from src.services import (
    get_router_service,
    get_session_manager
)

from src.errors import ICCBaseError, ErrorHandler

logger = logging.getLogger(__name__)

router = APIRouter()


def get_session_manager_dependency():
    """Dependency for session manager"""
    return get_session_manager()


def get_router_service_dependency():
    """Dependency for router service"""
    return get_router_service()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    session_manager = Depends(get_session_manager_dependency),
    router_service = Depends(get_router_service_dependency)
) -> ChatMessageResponse:
    """
    Send a message to the agent and get a response.
    
    The agent maintains conversation context using the session_id.
    Subsequent messages with the same session_id continue the conversation.
    
    **Parameters:**
    - **session_id**: UUID for session tracking
    - **message**: User's query or response
    - **connection**: (Optional) Database connection ID
    - **schema**: (Optional) Database schema name
    - **tables**: (Optional) List of table names
    
    **Returns:**
    - Agent's response with current stage and context
    - Error details if request fails
    """
    try:
        logger.info(f"Processing message for session {request.session_id}: {request.message[:50]}...")
        
        # Get or create session memory
        memory = session_manager.get_or_create_session(request.session_id)
        
        # Invoke router with user input
        result = await router_service.invoke_router(
            user_input=request.message,
            memory=memory,
            connection=request.connection,
            schema=request.schema_name,  # Use schema_name instead of schema
            selected_tables=request.tables
        )
        
        if not result.get("success", False):
            # Handle error
            error_info = result.get("error_info", {})
            logger.error(f"Router error: {result.get('error')}")
            
            return ChatMessageResponse(
                session_id=request.session_id,
                response=error_info.get("message", "An error occurred"),
                stage=memory.stage.value if hasattr(memory, 'stage') else None,
                error=ErrorDetail(
                    code=error_info.get("code", "UNKNOWN"),
                    message=error_info.get("message", "Unknown error"),
                    details=error_info.get("details"),
                    category=error_info.get("category", "unknown")
                )
            )
        
        # Parse response for dropdown indicators
        response_text = result["response"]
        requires_dropdown = False
        dropdown_type = None
        dropdown_options = None
        
        # Check for dropdown indicators in response
        if "CONNECTION_DROPDOWN:" in response_text:
            requires_dropdown = True
            dropdown_type = "connection"
            # Extract JSON after prefix
            json_str = response_text.split("CONNECTION_DROPDOWN:", 1)[1]
            dropdown_options = json.loads(json_str)
            response_text = "Please select a database connection:"
        
        elif "SCHEMA_DROPDOWN:" in response_text:
            requires_dropdown = True
            dropdown_type = "schema"
            json_str = response_text.split("SCHEMA_DROPDOWN:", 1)[1]
            dropdown_options = json.loads(json_str)
            response_text = "Please select a schema:"
        
        elif "TABLE_DROPDOWN:" in response_text:
            requires_dropdown = True
            dropdown_type = "table"
            json_str = response_text.split("TABLE_DROPDOWN:", 1)[1]
            dropdown_options = json.loads(json_str)
            response_text = "Please select tables:"
        
        # Build response
        return ChatMessageResponse(
            session_id=request.session_id,
            response=response_text,
            stage=memory.stage.value if hasattr(memory, 'stage') else None,
            gathered_params=memory.gathered_params if hasattr(memory, 'gathered_params') else {},
            job_context=memory.job_context.to_dict() if hasattr(memory, 'job_context') else {},
            requires_dropdown=requires_dropdown,
            dropdown_type=dropdown_type,
            dropdown_options=dropdown_options
        )
    
    except ICCBaseError as e:
        logger.error(f"ICC error in send_message: {e}", exc_info=True)
        
        return ChatMessageResponse(
            session_id=request.session_id,
            response=str(e),
            error=ErrorDetail(
                code=e.code.value,
                message=str(e),
                details=e.details,
                category=e.category.value
            )
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in send_message: {e}", exc_info=True)
        
        return ChatMessageResponse(
            session_id=request.session_id,
            response="An unexpected error occurred. Please try again.",
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message=str(e),
                details={"error_type": type(e).__name__},
                category="internal"
            )
        )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest = None,
    session_manager = Depends(get_session_manager_dependency)
) -> SessionResponse:
    """
    Create a new conversation session.
    
    Sessions maintain conversation context across multiple messages.
    If no session_id provided, a new UUID will be generated.
    
    **Parameters:**
    - **session_id**: (Optional) Custom session ID
    
    **Returns:**
    - New session information
    """
    try:
        # Generate or use provided session ID
        session_id = request.session_id if request and request.session_id else str(uuid.uuid4())
        
        logger.info(f"Creating new session: {session_id}")
        
        # Create session memory
        memory = session_manager.get_or_create_session(session_id)
        
        return SessionResponse(
            session_id=session_id,
            created_at=datetime.now(),
            stage=memory.stage.value if hasattr(memory, 'stage') else "router",
            message="Session created successfully"
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_manager = Depends(get_session_manager_dependency)
) -> SessionResponse:
    """
    Get information about an existing session.
    
    **Parameters:**
    - **session_id**: Session ID to retrieve
    
    **Returns:**
    - Session information including current stage
    """
    try:
        logger.info(f"Retrieving session: {session_id}")
        
        # Get session memory
        memory = session_manager.get_or_create_session(session_id)
        
        return SessionResponse(
            session_id=session_id,
            created_at=None,  # Could track creation time in memory if needed
            stage=memory.stage.value if hasattr(memory, 'stage') else "router",
            message="Session retrieved successfully"
        )
    
    except Exception as e:
        logger.error(f"Error retrieving session: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_manager = Depends(get_session_manager_dependency)
) -> Dict[str, Any]:
    """
    Delete a session and its associated memory.
    
    **Parameters:**
    - **session_id**: Session ID to delete
    
    **Returns:**
    - Confirmation message
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        # Delete session from manager
        if hasattr(session_manager, 'delete_session'):
            session_manager.delete_session(session_id)
        
        return {
            "message": f"Session {session_id} deleted successfully",
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
