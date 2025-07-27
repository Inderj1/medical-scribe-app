"""Streaming Transcription API endpoints for chunk-based audio processing"""
import os
import logging
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import base64

from app.db.session import get_db
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.core.auth import get_current_user
from app.models.user import User
from app.agents.streaming_medical_scribe_supervisor import get_streaming_supervisor

logger = logging.getLogger(__name__)

router = APIRouter()


# Request models
class StartSessionRequest(BaseModel):
    encounter_id: str
    audio_config: Optional[Dict[str, Any]] = {
        "sample_rate": 16000,
        "channels": 1,
        "format": "pcm16"
    }


class AudioChunkRequest(BaseModel):
    session_id: str
    audio_data: str  # Base64 encoded audio
    duration_ms: int
    sequence_number: Optional[int] = None


class EndSessionRequest(BaseModel):
    session_id: str


# Response models
class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: Optional[str] = None


class TranscriptionSegmentResponse(BaseModel):
    session_id: str
    segment_number: int
    text_segment: str
    total_text: str
    is_partial: bool
    timestamp: str


@router.post("/session/start", response_model=SessionResponse)
async def start_transcription_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """
    Start a new streaming transcription session
    
    Args:
        request: Session configuration including encounter_id and audio settings
        
    Returns:
        Session ID and status
    """
    try:
        # Validate encounter exists and belongs to user
        encounter = db.query(Encounter).filter(
            Encounter.id == request.encounter_id,
            Encounter.user_id == current_user.id
        ).first()
        
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
            
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create transcription record in database
        transcription = Transcription(
            encounter_id=request.encounter_id,
            status="active",
            format_preference="soap"  # Default, can be changed later
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Get supervisor and start session
        supervisor = get_streaming_supervisor()
        result = await supervisor.start_session(
            session_id=session_id,
            encounter_id=request.encounter_id,
            transcription_id=str(transcription.id),
            audio_config=request.audio_config,
            user_id=str(current_user.id)
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
            
        return SessionResponse(
            session_id=session_id,
            status="active",
            message="Transcription session started successfully"
        )
        
    except Exception as e:
        logger.error(f"Error starting transcription session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/audio-chunk")
async def upload_audio_chunk(
    request: AudioChunkRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload an audio chunk for transcription
    
    Args:
        request: Audio chunk data including session_id and base64 encoded audio
        
    Returns:
        Acknowledgment and any partial transcription results
    """
    try:
        # Validate session exists and belongs to user
        supervisor = get_streaming_supervisor()
        
        if not supervisor.validate_session(request.session_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
            
        # Process audio chunk
        result = await supervisor.process_audio_chunk(
            session_id=request.session_id,
            audio_data=request.audio_data,
            duration_ms=request.duration_ms,
            sequence_number=request.sequence_number
        )
        
        # Return result which may include partial transcription
        return result
        
    except Exception as e:
        logger.error(f"Error processing audio chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end", response_model=SessionResponse)
async def end_transcription_session(
    request: EndSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SessionResponse:
    """
    End a transcription session and get final results
    
    Args:
        request: Session ID to end
        
    Returns:
        Final transcription and clinical note
    """
    try:
        # Get supervisor
        supervisor = get_streaming_supervisor()
        
        if not supervisor.validate_session(request.session_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
            
        # End session and get final results
        result = await supervisor.end_session(request.session_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
            
        # Update database
        transcription_id = result.get("transcription_id")
        if transcription_id:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()
            
            if transcription:
                transcription.status = "completed"
                transcription.transcription_text = result.get("final_transcription", "")
                transcription.clinical_note = result.get("clinical_note", "")
                db.commit()
                
        return SessionResponse(
            session_id=request.session_id,
            status="completed",
            message="Session ended successfully"
        )
        
    except Exception as e:
        logger.error(f"Error ending transcription session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current status of a transcription session
    
    Args:
        session_id: The session ID to check
        
    Returns:
        Current session status and statistics
    """
    supervisor = get_streaming_supervisor()
    
    if not supervisor.validate_session(session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    status = await supervisor.get_session_status(session_id)
    return status


@router.get("/session/{session_id}/transcript")
async def get_current_transcript(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current accumulated transcript for a session
    
    Args:
        session_id: The session ID
        
    Returns:
        Current transcript and clinical sections
    """
    supervisor = get_streaming_supervisor()
    
    if not supervisor.validate_session(session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    transcript = await supervisor.get_current_transcript(session_id)
    return transcript


@router.post("/session/{session_id}/clinical-update")
async def trigger_clinical_update(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually trigger clinical analysis on current transcript
    
    Args:
        session_id: The session ID
        
    Returns:
        Updated clinical sections
    """
    supervisor = get_streaming_supervisor()
    
    if not supervisor.validate_session(session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    result = await supervisor.trigger_clinical_analysis(session_id)
    return result


# Utility endpoints
@router.get("/audio-config")
async def get_recommended_audio_config() -> Dict[str, Any]:
    """
    Get recommended audio configuration for streaming
    
    Returns:
        Recommended audio settings
    """
    return {
        "sample_rate": 16000,
        "channels": 1,
        "format": "pcm16",
        "chunk_duration_ms": 1000,  # 1 second chunks
        "min_chunk_size_bytes": 32000,  # ~1 second of 16kHz mono PCM16
        "max_chunk_size_bytes": 320000  # ~10 seconds
    }


@router.get("/session/active")
async def get_active_sessions(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get all active sessions for the current user
    
    Returns:
        List of active session summaries
    """
    supervisor = get_streaming_supervisor()
    sessions = await supervisor.get_user_sessions(str(current_user.id))
    return sessions