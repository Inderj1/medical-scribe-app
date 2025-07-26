"""Agent-based WebSocket API for real-time medical transcription"""
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.core.clerk_auth import get_clerk_user_ws
from app.agents.medical_scribe_runner import medical_scribe_runner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/agent")
async def websocket_endpoint(
    websocket: WebSocket,
    user: Dict[str, Any] = Depends(get_clerk_user_ws)
):
    """
    WebSocket endpoint for real-time medical transcription using agents.
    
    This endpoint:
    - Accepts continuous audio streaming (no buffering)
    - Provides real-time transcription using OpenAI Realtime API
    - Performs clinical analysis using agents
    - Returns structured clinical notes
    
    Message Types:
    
    Client -> Server:
    - encounter:start - Start new encounter
    - encounter:end - End current encounter
    - audio data (binary) - Raw PCM audio stream
    - format:preference - Update note format (soap/bullet/narrative)
    
    Server -> Client:
    - transcription:partial - Partial transcription update
    - transcription:complete - Complete transcription with analysis
    - encounter:started - Encounter started confirmation
    - encounter:ended - Encounter ended confirmation
    - error - Error message
    """
    
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return
        
    user_id = user.get("id")
    metadata = {
        "user_email": user.get("email"),
        "user_name": user.get("first_name", "") + " " + user.get("last_name", ""),
        "connection_time": None  # Will be set by runner
    }
    
    try:
        # Handle connection through the medical scribe runner
        await medical_scribe_runner.handle_websocket_connection(
            websocket,
            user_id,
            metadata
        )
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        await websocket.close(code=1011, reason="Internal server error")


@router.get("/agent/status")
async def get_agent_status():
    """Get the status of the agent system"""
    return medical_scribe_runner.get_system_status()


@router.post("/agent/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients (admin only)"""
    # TODO: Add admin authentication
    await medical_scribe_runner.broadcast_to_all(message)
    return {"status": "broadcast sent", "message": message}