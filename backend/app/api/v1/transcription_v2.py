"""Transcription API v2 using OpenAI Agents SDK"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import aiofiles
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.models.clinical_note import ClinicalNote
from app.services.agent_runner_v2 import run_agent_workflow
from app.schemas.transcription import TranscriptionResponse, TranscriptionListResponse
from app.schemas.clinical_note import ClinicalNoteResponse

router = APIRouter()


@router.post("/upload", response_model=TranscriptionResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    encounter_id: str = Form(...),
    audio_file: UploadFile = File(...),
    format_preference: str = Form("soap"),
    language: str = Form("en"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload audio file for transcription using OpenAI Agents SDK pipeline"""
    
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
    encounter = db.query(Encounter).filter_by(
        id=encounter_id,
        user_id=current_user.id
    ).first()
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await audio_file.read()
        await f.write(content)
    
    # Create transcription record
    transcription = Transcription(
        id=file_id,
        encounter_id=encounter_id,
        user_id=current_user.id,
        file_name=audio_file.filename,
        file_path=file_path,
        file_size=len(content),
        format_preference=format_preference,
        language=language,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Start agent processing in background
    background_tasks.add_task(
        run_agent_workflow,
        transcription_id=transcription.id,
        audio_path=file_path,
        patient_id=encounter.patient_id,
        encounter_id=encounter_id,
        format_preference=format_preference,
        language=language
    )
    
    return TranscriptionResponse(
        id=transcription.id,
        encounter_id=transcription.encounter_id,
        status=transcription.status,
        created_at=transcription.created_at,
        file_name=transcription.file_name,
        progress_percentage=0,
        language=transcription.language,
        format_preference=transcription.format_preference
    )


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transcription status and results"""
    
    transcription = db.query(Transcription).filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    response = TranscriptionResponse(
        id=transcription.id,
        encounter_id=transcription.encounter_id,
        status=transcription.status,
        created_at=transcription.created_at,
        completed_at=transcription.completed_at,
        file_name=transcription.file_name,
        progress_percentage=transcription.progress_percentage or 0,
        language=transcription.language,
        format_preference=transcription.format_preference,
        error_message=transcription.error_message
    )
    
    # Include transcript if available
    if transcription.transcript:
        response.transcript = transcription.transcript
        response.word_count = transcription.word_count
        response.duration_seconds = transcription.duration_seconds
    
    # Include speaker info if available
    if transcription.speaker_segments:
        response.speaker_segments = transcription.speaker_segments
        response.speaker_count = transcription.speaker_count
    
    return response


@router.get("/{transcription_id}/clinical-note", response_model=ClinicalNoteResponse)
async def get_clinical_note(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get formatted clinical note for a transcription"""
    
    # Verify transcription belongs to user
    transcription = db.query(Transcription).filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Get clinical note
    clinical_note = db.query(ClinicalNote).filter_by(
        transcription_id=transcription_id
    ).first()
    
    if not clinical_note:
        raise HTTPException(status_code=404, detail="Clinical note not generated yet")
    
    return ClinicalNoteResponse(
        id=clinical_note.id,
        transcription_id=clinical_note.transcription_id,
        format_type=clinical_note.format_type,
        content=clinical_note.content,
        sections=clinical_note.sections or {},
        metadata=clinical_note.metadata or {},
        quality_score=clinical_note.quality_score,
        created_at=clinical_note.created_at,
        updated_at=clinical_note.updated_at
    )


@router.get("/{transcription_id}/qa", response_model=Dict[str, Any])
async def get_qa_report(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get quality assurance report for a transcription"""
    
    # Verify transcription belongs to user
    transcription = db.query(Transcription).filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Get QA data from clinical note metadata
    clinical_note = db.query(ClinicalNote).filter_by(
        transcription_id=transcription_id
    ).first()
    
    if not clinical_note or not clinical_note.metadata:
        raise HTTPException(status_code=404, detail="QA report not available")
    
    qa_report = clinical_note.metadata.get("qa_report", {})
    
    return {
        "transcription_id": transcription_id,
        "overall_score": qa_report.get("overall_score", 0),
        "completeness_score": qa_report.get("completeness_score", 0),
        "accuracy_score": qa_report.get("accuracy_score", 0),
        "clarity_score": qa_report.get("clarity_score", 0),
        "missing_sections": qa_report.get("missing_sections", []),
        "suggestions": qa_report.get("suggestions", []),
        "warnings": qa_report.get("warnings", []),
        "approved": qa_report.get("approved", False)
    }


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    encounter_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List transcriptions for current user"""
    
    query = db.query(Transcription).filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if encounter_id:
        query = query.filter_by(encounter_id=encounter_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    transcriptions = query.order_by(Transcription.created_at.desc()).offset(skip).limit(limit).all()
    
    items = []
    for t in transcriptions:
        item = TranscriptionResponse(
            id=t.id,
            encounter_id=t.encounter_id,
            status=t.status,
            created_at=t.created_at,
            completed_at=t.completed_at,
            file_name=t.file_name,
            progress_percentage=t.progress_percentage or 0,
            language=t.language,
            format_preference=t.format_preference,
            error_message=t.error_message
        )
        
        if t.transcript:
            item.word_count = t.word_count
            item.duration_seconds = t.duration_seconds
        
        items.append(item)
    
    return TranscriptionListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.delete("/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a transcription and associated data"""
    
    transcription = db.query(Transcription).filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Delete associated clinical note
    db.query(ClinicalNote).filter_by(transcription_id=transcription_id).delete()
    
    # Delete audio file
    if transcription.file_path and os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)
    
    # Delete transcription record
    db.delete(transcription)
    db.commit()
    
    return {"message": "Transcription deleted successfully"}