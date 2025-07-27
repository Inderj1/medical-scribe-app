"""Batch Transcription API endpoints"""
import os
import logging
import tempfile
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.core.auth import get_current_user
from app.models.user import User
from app.agents.batch_medical_scribe_supervisor import get_medical_scribe_supervisor

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported audio formats
SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


@router.post("/upload")
async def upload_audio_for_transcription(
    background_tasks: BackgroundTasks,
    encounter_id: str = Form(...),
    audio_file: UploadFile = File(...),
    format_preference: Optional[str] = Form("soap"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload an audio file for transcription and clinical note generation
    
    Args:
        encounter_id: The encounter ID this transcription belongs to
        audio_file: The audio file to transcribe
        format_preference: Preferred note format (soap, bullet, narrative, epic_template)
        
    Returns:
        Transcription ID and initial status
    """
    try:
        # Validate encounter exists and belongs to user
        encounter = db.query(Encounter).filter(
            Encounter.id == encounter_id,
            Encounter.user_id == current_user.id
        ).first()
        
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
            
        # Validate file format
        file_ext = os.path.splitext(audio_file.filename)[1].lower()
        if file_ext not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
            
        # Check file size
        audio_file.file.seek(0, 2)  # Seek to end
        file_size = audio_file.file.tell()
        audio_file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
            
        # Save audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
        # Create transcription record in database
        transcription = Transcription(
            encounter_id=encounter_id,
            status="processing",
            audio_file_path=tmp_file_path,
            format_preference=format_preference
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Get supervisor and start processing
        supervisor = get_medical_scribe_supervisor()
        
        # Start async processing
        result = await supervisor.process_audio_file(
            audio_file_path=tmp_file_path,
            encounter_id=encounter_id,
            transcription_id=str(transcription.id),
            options={
                "format_preference": format_preference,
                "user_id": str(current_user.id)
            }
        )
        
        # Schedule cleanup of temp file after processing
        background_tasks.add_task(cleanup_temp_file, tmp_file_path, delay=3600)  # Clean up after 1 hour
        
        return {
            "transcription_id": str(transcription.id),
            "status": "processing",
            "message": "Audio file uploaded successfully and processing started",
            "estimated_time_seconds": estimate_processing_time(file_size),
            "poll_url": f"/api/v1/transcription/{transcription.id}/status"
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio file: {str(e)}")
        # Clean up temp file if created
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{transcription_id}/status")
async def get_transcription_status(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of a transcription
    
    Args:
        transcription_id: The transcription ID to check
        
    Returns:
        Current status and progress information
    """
    # Validate transcription exists and belongs to user
    transcription = db.query(Transcription).join(Encounter).filter(
        Transcription.id == transcription_id,
        Encounter.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    # Get status from supervisor
    supervisor = get_medical_scribe_supervisor()
    status = await supervisor.get_transcription_status(transcription_id)
    
    # Update database status if changed
    if status.get("status") and status["status"] != transcription.status:
        transcription.status = status["status"]
        db.commit()
        
    return status


@router.get("/{transcription_id}")
async def get_transcription_result(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the completed transcription result
    
    Args:
        transcription_id: The transcription ID to retrieve
        
    Returns:
        Complete transcription with clinical notes
    """
    # Validate transcription exists and belongs to user
    transcription = db.query(Transcription).join(Encounter).filter(
        Transcription.id == transcription_id,
        Encounter.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    # Get result from supervisor
    supervisor = get_medical_scribe_supervisor()
    result = await supervisor.get_completed_transcription(transcription_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # Update database with results
    if result.get("status") == "completed":
        transcription.status = "completed"
        transcription.transcription_text = result["results"].get("transcription_text", "")
        transcription.clinical_note = result["results"].get("formatted_note", "")
        db.commit()
        
    return result


@router.get("/{transcription_id}/qa")
async def get_transcription_qa_results(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get quality assurance results for a transcription
    
    Args:
        transcription_id: The transcription ID
        
    Returns:
        QA metrics and alerts
    """
    # Validate transcription exists and belongs to user
    transcription = db.query(Transcription).join(Encounter).filter(
        Transcription.id == transcription_id,
        Encounter.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    # Get result from supervisor
    supervisor = get_medical_scribe_supervisor()
    result = await supervisor.get_completed_transcription(transcription_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # Extract QA metrics
    qa_results = {
        "transcription_id": transcription_id,
        "quality_metrics": result["results"].get("quality_metrics", {}),
        "confidence_scores": result["results"].get("confidence_scores", {}),
        "medical_terms": result["results"].get("medical_terms", []),
        "abnormal_findings": extract_abnormal_findings(result["results"]),
        "review_required": check_review_required(result["results"])
    }
    
    return qa_results


@router.post("/{transcription_id}/reformat")
async def reformat_transcription(
    transcription_id: str,
    format: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reformat an existing transcription in a different format
    
    Args:
        transcription_id: The transcription ID
        format: Target format (soap, bullet, narrative, epic_template)
        
    Returns:
        Reformatted clinical note
    """
    # Validate transcription exists and belongs to user
    transcription = db.query(Transcription).join(Encounter).filter(
        Transcription.id == transcription_id,
        Encounter.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    if transcription.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Transcription must be completed before reformatting"
        )
        
    # Get supervisor
    supervisor = get_medical_scribe_supervisor()
    
    # Get the completed transcription
    result = await supervisor.get_completed_transcription(transcription_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # Send reformat request to note structuring agent
    from app.agents.base import AgentMessage
    
    message = AgentMessage(
        agent_id="API",
        message_type="format_note",
        payload={
            "note_data": result["results"].get("structured_sections", {}),
            "format": format
        }
    )
    
    # Send directly to note structuring agent
    response = await supervisor.note_structuring_agent.process(message)
    
    if response and response.message_type == "note_reformatted":
        return {
            "transcription_id": transcription_id,
            "format": format,
            "formatted_note": response.payload["formatted_note"],
            "timestamp": response.payload["timestamp"]
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to reformat note")


@router.delete("/{transcription_id}")
async def cancel_transcription(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel an active transcription
    
    Args:
        transcription_id: The transcription ID to cancel
        
    Returns:
        Cancellation confirmation
    """
    # Validate transcription exists and belongs to user
    transcription = db.query(Transcription).join(Encounter).filter(
        Transcription.id == transcription_id,
        Encounter.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    # Cancel in supervisor
    supervisor = get_medical_scribe_supervisor()
    result = await supervisor.cancel_transcription(transcription_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # Update database
    transcription.status = "cancelled"
    db.commit()
    
    # Clean up audio file if exists
    if transcription.audio_file_path and os.path.exists(transcription.audio_file_path):
        try:
            os.unlink(transcription.audio_file_path)
        except:
            pass
            
    return result


# Helper functions
def estimate_processing_time(file_size: int) -> int:
    """Estimate processing time based on file size"""
    # Rough estimate: 1MB takes ~3 seconds (transcription + analysis + structuring)
    return int(file_size / (1024 * 1024) * 3)


async def cleanup_temp_file(file_path: str, delay: int = 0):
    """Clean up temporary file after delay"""
    if delay > 0:
        import asyncio
        await asyncio.sleep(delay)
        
    if os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to clean up temp file {file_path}: {str(e)}")


def extract_abnormal_findings(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract abnormal findings from results"""
    abnormal = []
    
    # Check for abnormal vital signs
    if "structured_sections" in results:
        sections = results["structured_sections"]
        if "vital_signs" in sections:
            vital_data = sections["vital_signs"]
            if "abnormal_flags" in vital_data:
                abnormal.extend(vital_data["abnormal_flags"])
                
    return abnormal


def check_review_required(results: Dict[str, Any]) -> bool:
    """Check if manual review is required"""
    # Check section updates for review flags
    if "section_updates" in results:
        for update in results["section_updates"]:
            if update.get("metadata", {}).get("requires_review"):
                return True
                
    # Check quality metrics
    if "quality_metrics" in results:
        metrics = results["quality_metrics"]
        if metrics.get("quality_grade") == "C":
            return True
        if metrics.get("missing_required_sections"):
            return True
            
    return False