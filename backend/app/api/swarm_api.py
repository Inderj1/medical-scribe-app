"""API endpoints using Swarm and OpenAI Agents SDK"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.core.auth import get_current_user
from app.models.user import User
from app.agents.swarm_supervisor import get_swarm_supervisor

logger = logging.getLogger(__name__)

router = APIRouter()


class StartSessionRequest(BaseModel):
    encounter_id: str


class AudioChunkRequest(BaseModel):
    session_id: str
    audio_data: str  # Base64 encoded
    duration_ms: int


class EndSessionRequest(BaseModel):
    session_id: str


class QualityCheckRequest(BaseModel):
    clinical_note: str


@router.post("/session/start")
async def start_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start a new transcription session using Swarm agents"""
    try:
        # Validate encounter
        encounter = db.query(Encounter).filter(
            Encounter.id == request.encounter_id,
            Encounter.user_id == current_user.id
        ).first()
        
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
            
        # Create transcription record
        transcription = Transcription(
            encounter_id=request.encounter_id,
            status="active"
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Start session with supervisor
        supervisor = get_swarm_supervisor()
        session_id = str(transcription.id)
        
        result = await supervisor.start_session(
            session_id=session_id,
            encounter_id=request.encounter_id,
            user_id=str(current_user.id)
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
            
        return {
            "session_id": session_id,
            "status": "active",
            "message": "Session started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/audio-chunk")
async def process_audio_chunk(
    request: AudioChunkRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Process an audio chunk through the Swarm agent pipeline"""
    supervisor = get_swarm_supervisor()
    
    # Validate session
    if not supervisor.validate_session(request.session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    # Process chunk
    result = await supervisor.process_audio_chunk(
        session_id=request.session_id,
        audio_data=request.audio_data,
        duration_ms=request.duration_ms
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    return result


@router.post("/session/end")
async def end_session(
    request: EndSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """End session and get final clinical note"""
    supervisor = get_swarm_supervisor()
    
    # Validate session
    if not supervisor.validate_session(request.session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    # End session
    result = await supervisor.end_session(request.session_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    # Update database
    transcription = db.query(Transcription).filter(
        Transcription.id == request.session_id
    ).first()
    
    if transcription:
        transcription.status = "completed"
        transcription.clinical_note = result.get("clinical_note", "")
        db.commit()
        
    return {
        "session_id": request.session_id,
        "status": "completed",
        "clinical_note": result.get("clinical_note"),
        "final_agent": result.get("final_agent"),
        "duration_seconds": result.get("duration_seconds")
    }


@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current session status"""
    supervisor = get_swarm_supervisor()
    
    if not supervisor.validate_session(session_id, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    return await supervisor.get_session_status(session_id)


@router.post("/quality-check")
async def check_note_quality(
    request: QualityCheckRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Run quality assurance on a clinical note"""
    supervisor = get_swarm_supervisor()
    
    result = await supervisor.run_quality_check(request.clinical_note)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    return result


@router.get("/agents")
async def get_available_agents(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get information about available agents"""
    return {
        "agents": [
            {
                "name": "TranscriptionAgent",
                "description": "Handles audio transcription using Whisper API",
                "functions": ["start_transcription_session", "process_audio_chunk", "end_transcription_session"]
            },
            {
                "name": "ClinicalAnalysisAgent",
                "description": "Analyzes transcripts for medical content",
                "functions": ["analyze_transcript"]
            },
            {
                "name": "NoteStructuringAgent",
                "description": "Formats clinical data into structured notes",
                "functions": ["format_clinical_note"]
            },
            {
                "name": "QualityAssuranceAgent",
                "description": "Checks clinical notes for quality and completeness",
                "functions": ["check_note_quality"]
            }
        ],
        "supervisor": "MedicalScribeSupervisor",
        "orchestration": "Swarm"
    }