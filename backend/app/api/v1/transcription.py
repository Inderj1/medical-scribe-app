"""Transcription API endpoints with agent processing"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import aiofiles
import os
import uuid
from typing import Optional

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.models.clinical_note import ClinicalNote
from app.services.agent_runner import run_agent_processing

router = APIRouter()


@router.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    encounter_id: str = Form(...),
    audio_file: UploadFile = File(...),
    format_preference: str = Form("soap"),
    language: str = Form("en"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload audio file for transcription using agent pipeline"""
    
    # Validate file
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(audio_file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {settings.ALLOWED_AUDIO_FORMATS}"
        )
    
    if audio_file.size and audio_file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Verify encounter exists and belongs to user
    try:
        encounter_uuid = uuid.UUID(encounter_id)
        encounter = db.query(Encounter).filter(
            Encounter.id == encounter_uuid,
            Encounter.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid encounter_id format")
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, "audio", f"{file_id}{file_ext}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Read and save file
    content = await audio_file.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Create transcription record
    transcription = Transcription(
        encounter_id=encounter.id,
        audio_file_path=file_path,
        file_size_bytes=len(content),
        status="pending"
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Start background agent processing
    background_tasks.add_task(
        run_agent_processing,
        str(transcription.id),
        file_path,
        format_preference
    )
    
    return {
        "transcription_id": str(transcription.id),
        "status": "processing",
        "message": "Audio file uploaded successfully. Agent processing started.",
        "sse_endpoint": f"/api/v1/sse/transcription/{transcription.id}"
    }


@router.get("/{transcription_id}")
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transcription status and results"""
    
    try:
        transcription_uuid = uuid.UUID(transcription_id)
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_uuid
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transcription_id format")
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Verify access through encounter
    encounter = transcription.encounter
    if encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get clinical notes if completed
    clinical_notes = None
    if transcription.status == "completed":
        clinical_note = db.query(ClinicalNote).filter(
            ClinicalNote.transcription_id == transcription.id
        ).first()
        
        if clinical_note:
            clinical_notes = {
                "id": str(clinical_note.id),
                "format_type": clinical_note.format_type,
                "subjective": clinical_note.subjective,
                "objective": clinical_note.objective,
                "assessment": clinical_note.assessment,
                "plan": clinical_note.plan,
                "chief_complaint": clinical_note.chief_complaint,
                "history_present_illness": clinical_note.history_present_illness,
                "medications": clinical_note.medications,
                "allergies": clinical_note.allergies,
                "quality_score": clinical_note.quality_score,
                "ehr_composition_id": clinical_note.ehr_composition_id
            }
    
    return {
        "id": str(transcription.id),
        "encounter_id": str(transcription.encounter_id),
        "status": transcription.status,
        "progress": transcription.progress,
        "transcript": transcription.transcript,
        "clinical_notes": clinical_notes,
        "error_message": transcription.error_message,
        "created_at": transcription.created_at.isoformat(),
        "completed_at": transcription.completed_at.isoformat() if transcription.completed_at else None,
        "audio_duration_seconds": transcription.audio_duration_seconds
    }


@router.get("/{transcription_id}/clinical-note")
async def get_clinical_note(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get clinical note for a transcription"""
    
    try:
        transcription_uuid = uuid.UUID(transcription_id)
        clinical_note = db.query(ClinicalNote).filter(
            ClinicalNote.transcription_id == transcription_uuid
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transcription_id format")
    
    if not clinical_note:
        raise HTTPException(status_code=404, detail="Clinical note not found")
    
    # Verify access
    encounter = clinical_note.encounter
    if encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Format based on type
    if clinical_note.format_type == "soap":
        formatted_content = f"""SUBJECTIVE:
{clinical_note.subjective or 'None documented'}

OBJECTIVE:
{clinical_note.objective or 'None documented'}

ASSESSMENT:
{clinical_note.assessment or 'None documented'}

PLAN:
{clinical_note.plan or 'None documented'}"""
    else:
        # Return structured data for other formats
        formatted_content = {
            "chief_complaint": clinical_note.chief_complaint,
            "hpi": clinical_note.history_present_illness,
            "ros": clinical_note.review_of_systems,
            "pmh": clinical_note.past_medical_history,
            "medications": clinical_note.medications,
            "allergies": clinical_note.allergies,
            "physical_exam": clinical_note.physical_exam,
            "assessment": clinical_note.assessment,
            "plan": clinical_note.plan
        }
    
    return {
        "id": str(clinical_note.id),
        "transcription_id": str(clinical_note.transcription_id),
        "encounter_id": str(clinical_note.encounter_id),
        "format_type": clinical_note.format_type,
        "content": formatted_content,
        "quality_score": clinical_note.quality_score,
        "ai_confidence_scores": clinical_note.ai_confidence_scores,
        "created_at": clinical_note.created_at.isoformat()
    }


@router.get("/")
async def list_transcriptions(
    encounter_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List transcriptions for current user"""
    
    # Build query through encounters
    query = db.query(Transcription).join(Encounter).filter(
        Encounter.user_id == current_user.id
    )
    
    if encounter_id:
        try:
            encounter_uuid = uuid.UUID(encounter_id)
            query = query.filter(Transcription.encounter_id == encounter_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid encounter_id format")
    
    if status:
        query = query.filter(Transcription.status == status)
    
    # Order by most recent first
    query = query.order_by(Transcription.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    transcriptions = query.offset(skip).limit(limit).all()
    
    results = []
    for trans in transcriptions:
        results.append({
            "id": str(trans.id),
            "encounter_id": str(trans.encounter_id),
            "status": trans.status,
            "progress": trans.progress,
            "created_at": trans.created_at.isoformat(),
            "completed_at": trans.completed_at.isoformat() if trans.completed_at else None,
            "audio_duration_seconds": trans.audio_duration_seconds,
            "has_clinical_note": bool(trans.clinical_notes)
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "transcriptions": results
    }