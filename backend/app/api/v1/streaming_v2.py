"""Streaming API v2 using OpenAI Agents SDK"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from sqlalchemy.orm import Session
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import base64
import aiofiles
import tempfile
import os
from pathlib import Path

from app.db.session import get_db
from app.core.security import get_current_active_user, decode_token
from app.models.user import User
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.core.config import settings
from app.agents_v2 import orchestrator
from app.core.sse_manager import sse_manager
from app.services.agent_runner_v2 import process_streaming_session
from app.services.whisper_service import WhisperService

router = APIRouter()
logger = logging.getLogger(__name__)


def _calculate_age(date_of_birth) -> Optional[int]:
    """Calculate age from date of birth"""
    if not date_of_birth:
        return None
    today = datetime.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


@router.post("/start")
async def start_streaming_session(
    session_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a new streaming transcription session with OpenAI Agents SDK"""
    
    try:
        logger.info(f"Starting streaming session for user {current_user.email}")
        logger.info(f"Session data received: {session_data}")
        
        # Extract and validate required fields
        encounter_id = session_data.get("encounter_id")
        format_preference = session_data.get("format_preference", "soap")
        language = session_data.get("language", "en")
        
        if not encounter_id:
            raise HTTPException(status_code=400, detail="encounter_id is required")
        
        # Check if it's a temporary encounter
        is_temp_encounter = encounter_id.startswith("temp-")
        
        if is_temp_encounter:
            # For temporary encounters, use patient data from session
            patient_id = session_data.get("patient_id")  # Use the actual patient ID
            patient_ehr_id = session_data.get("patient_ehr_id")
            patient_mrn = session_data.get("patient_mrn")
            patient_first_name = session_data.get("patient_first_name")
            patient_last_name = session_data.get("patient_last_name")
            patient_gender = session_data.get("patient_gender")
            provider_name = session_data.get("provider_name", "Dr. Provider")
            
            # Generate a real UUID for the temporary encounter
            real_encounter_id = str(uuid.uuid4())
            
            # Use the patient_id from frontend - they should already exist
            if not patient_id:
                raise HTTPException(status_code=400, detail="patient_id is required for temporary encounters")
            
            # Verify patient exists or create if needed
            patient = db.query(Patient).filter_by(id=patient_id).first()
            if not patient:
                # Create patient from the provided data
                logger.info(f"Creating patient with id {patient_id}")
                patient = Patient(
                    id=patient_id,
                    ehr_id=patient_ehr_id,
                    mrn=patient_mrn or f"TEMP-{patient_id[:8]}",
                    first_name=patient_first_name or "Unknown",
                    last_name=patient_last_name or "Patient",
                    gender=patient_gender.lower() if patient_gender else None,
                    date_of_birth=datetime(1970, 1, 1),  # Default DOB
                    created_at=datetime.utcnow()
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)
            
            # Create a temporary encounter with the existing patient
            encounter = Encounter(
                id=real_encounter_id,
                user_id=current_user.id,
                patient_id=patient.id,  # Use the existing patient ID
                chief_complaint="Live transcription session",
                provider_name=provider_name,
                encounter_type="Office Visit",
                encounter_date=datetime.utcnow(),
                status="Active"
            )
            db.add(encounter)
            db.commit()
            
            # Update encounter_id to use the real UUID
            encounter_id = real_encounter_id
        else:
            # Verify encounter exists and belongs to user
            encounter = db.query(Encounter).filter_by(
                id=encounter_id,
                user_id=current_user.id
            ).first()
            
            if not encounter:
                raise HTTPException(status_code=404, detail="Encounter not found")
            
            # Get patient details
            patient = db.query(Patient).filter_by(id=encounter.patient_id).first()
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
        
        # Create transcription record
        transcription_id = str(uuid.uuid4())
        session_id = f"session_{transcription_id}"
        
        transcription = Transcription(
            id=transcription_id,
            encounter_id=encounter_id,
            user_id=current_user.id,
            file_name=f"streaming_session_{datetime.utcnow().isoformat()}.txt",
            format_preference=format_preference,
            language=language,
            status="streaming",
            streaming_session_id=session_id,
            created_at=datetime.utcnow()
        )
        db.add(transcription)
        db.commit()
        
        # Initialize session with orchestrator
        patient_context = {
            "patient_id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "age": _calculate_age(patient.date_of_birth),
            "gender": patient.gender,
            "mrn": patient.mrn,
            "encounter_id": encounter.id,
            "encounter_date": encounter.encounter_date.isoformat() if encounter.encounter_date else None,
            "chief_complaint": encounter.chief_complaint,
            "provider_name": encounter.provider_name,
            "allergies": getattr(patient, 'allergies', None),
            "medications": getattr(patient, 'current_medications', None)
        }
        
        # The actual session initialization happens when text starts arriving
        
        return {
            "session_id": session_id,
            "transcription_id": transcription_id,
            "status": "ready",
            "format_preference": format_preference,
            "language": language
        }
        
    except Exception as e:
        logger.error(f"Error in start_streaming_session: {str(e)}")
        raise


@router.post("/{session_id}/text")
async def add_text_to_session(
    session_id: str,
    text_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add text chunk to streaming session"""
    
    try:
        # Extract transcription ID from session ID
        transcription_id = session_id.replace("session_", "")
        
        # Verify session belongs to user
        transcription = db.query(Transcription).filter_by(
            id=transcription_id,
            user_id=current_user.id,
            status="streaming"
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Session not found or not active")
        
        # Extract text and speaker info
        text_chunk = text_data.get("text", "")
        speaker_id = text_data.get("speaker_id", "SPEAKER_00")
        is_final = text_data.get("is_final", False)
        
        if not text_chunk:
            return {"status": "ok", "message": "Empty text chunk ignored"}
        
        # Process text chunk with orchestrator
        result = orchestrator.process_text_chunk(
            session_id=session_id,
            text_chunk=text_chunk,
            speaker_id=speaker_id,
            is_final=is_final
        )
        
        # Send SSE update
        await sse_manager.publish(
            f"transcription_{transcription_id}",
            {
                "type": "text_chunk_added",
                "data": {
                    "text": text_chunk,
                    "speaker_id": speaker_id,
                    "is_final": is_final
                }
            }
        )
        
        return {
            "status": "ok",
            "session_id": session_id,
            "chunk_processed": True
        }
        
    except Exception as e:
        logger.error(f"Error adding text to session: {str(e)}")
        raise


@router.post("/{session_id}/audio")
async def add_audio_to_session(
    session_id: str,
    audio_file: UploadFile = File(...),
    chunk_number: int = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process audio chunk and return transcription with speaker diarization"""
    
    try:
        # Extract transcription ID from session ID
        transcription_id = session_id.replace("session_", "")
        
        # Verify session belongs to user
        transcription = db.query(Transcription).filter_by(
            id=transcription_id,
            user_id=current_user.id,
            status="streaming"
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Session not found or not active")
        
        # Save audio chunk temporarily
        temp_audio_path = None
        try:
            # Create temp file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                temp_audio_path = temp_file.name
                content = await audio_file.read()
                temp_file.write(content)
            
            # Process audio with Whisper service
            whisper_service = WhisperService()
            result = await whisper_service.transcribe_with_diarization(
                audio_path=temp_audio_path,
                language="en"
            )
            
            if result["status"] == "success":
                # Extract segments with speaker info
                segments = result.get("segments", [])
                
                # Process each segment through the orchestrator
                for segment in segments:
                    text = segment.get("text", "").strip()
                    speaker = segment.get("speaker", "SPEAKER_00")
                    start_time = segment.get("start", 0)
                    end_time = segment.get("end", 0)
                    
                    if text:
                        # Add text with speaker info to orchestrator
                        orchestrator.process_text_chunk(
                            session_id=session_id,
                            text_chunk=text,
                            speaker_id=speaker,
                            is_final=True
                        )
                        
                        # Send SSE update with speaker info
                        await sse_manager.send_event(
                            session_id=session_id,
                            event_type="transcript_chunk",
                            data={
                                "text": text,
                                "speaker": speaker,
                                "chunk_number": chunk_number,
                                "start_time": start_time,
                                "end_time": end_time,
                                "is_final": True
                            }
                        )
                
                # Store audio chunk metadata in database (optional)
                # This could be useful for replay or quality assurance
                
                return {
                    "status": "success",
                    "chunk_number": chunk_number,
                    "segments_count": len(segments),
                    "total_duration": result.get("duration", 0),
                    "speakers_detected": list(set(s.get("speaker", "SPEAKER_00") for s in segments))
                }
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Whisper transcription failed: {result.get('error', 'Unknown error')}"
                )
                
        finally:
            # Clean up temp file
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        
    except Exception as e:
        logger.error(f"Error processing audio chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/end")
async def end_streaming_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """End streaming session and trigger final processing"""
    
    try:
        # Extract transcription ID
        transcription_id = session_id.replace("session_", "")
        
        # Verify session belongs to user
        transcription = db.query(Transcription).filter_by(
            id=transcription_id,
            user_id=current_user.id,
            status="streaming"
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Session not found or not active")
        
        # Update transcription status
        transcription.status = "processing"
        db.commit()
        
        # Trigger final processing
        result = await process_streaming_session(
            session_id=session_id,
            transcription_id=transcription_id,
            patient_id=transcription.encounter.patient_id,
            encounter_id=transcription.encounter_id,
            format_preference=transcription.format_preference
        )
        
        return {
            "status": "processing",
            "session_id": session_id,
            "transcription_id": transcription_id,
            "message": "Session ended, processing transcript"
        }
        
    except Exception as e:
        logger.error(f"Error ending streaming session: {str(e)}")
        raise


@router.get("/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current status of streaming session"""
    
    # Extract transcription ID
    transcription_id = session_id.replace("session_", "")
    
    # Verify session belongs to user
    transcription = db.query(Transcription).filter_by(
        id=transcription_id,
        user_id=current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get status from orchestrator
    status = orchestrator.get_session_status(session_id)
    
    return {
        "session_id": session_id,
        "transcription_id": transcription_id,
        "status": transcription.status,
        "created_at": transcription.created_at.isoformat(),
        "session_info": status
    }


@router.websocket("/{session_id}/ws")
async def websocket_streaming(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for bidirectional streaming"""
    
    await websocket.accept()
    
    try:
        # Authenticate from query params
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="No token provided")
            return
        
        # Decode token to get user
        try:
            user_id = decode_token(token)
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Extract transcription ID
        transcription_id = session_id.replace("session_", "")
        
        # Verify session belongs to user
        transcription = db.query(Transcription).filter_by(
            id=transcription_id,
            user_id=user_id,
            status="streaming"
        ).first()
        
        if not transcription:
            await websocket.close(code=4004, reason="Session not found")
            return
        
        logger.info(f"WebSocket connected for session {session_id}")
        
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "transcription_id": transcription_id
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "text_chunk":
                # Process text chunk
                result = orchestrator.process_text_chunk(
                    session_id=session_id,
                    text_chunk=data.get("text", ""),
                    speaker_id=data.get("speaker_id", "SPEAKER_00"),
                    is_final=data.get("is_final", False)
                )
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "chunk_processed",
                    "status": "ok"
                })
                
            elif message_type == "end_session":
                # End the session
                transcription.status = "processing"
                db.commit()
                
                await websocket.send_json({
                    "type": "session_ended",
                    "status": "processing"
                })
                
                # Trigger processing
                await process_streaming_session(
                    session_id=session_id,
                    transcription_id=transcription_id,
                    patient_id=transcription.encounter.patient_id,
                    encounter_id=transcription.encounter_id,
                    format_preference=transcription.format_preference
                )
                
                break
                
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=4000, reason=str(e))