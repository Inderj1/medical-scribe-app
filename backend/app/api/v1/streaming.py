"""Streaming API endpoints for real-time text processing"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.core.security import get_current_active_user, decode_token
from app.models.user import User
from app.models.transcription import Transcription
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.core.config import settings
from app.agents.medical_scribe_supervisor import medical_scribe_supervisor
from app.agents.context_manager import handoff_context
from app.core.sse_manager import sse_manager
from app.services.agent_runner import update_progress

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
    """Start a new streaming transcription session"""
    
    logger.info(f"Starting streaming session for user {current_user.email}")
    logger.info(f"Session data received: {session_data}")
    
    encounter_id = session_data.get("encounter_id")
    if not encounter_id:
        logger.error("No encounter_id provided in session_data")
        raise HTTPException(status_code=400, detail="encounter_id is required")
    
    # Handle temporary encounter IDs
    encounter = None
    patient = None
    
    if encounter_id.startswith("temp-"):
        # Temporary encounter - get patient info from session data
        logger.info(f"Using temporary encounter ID: {encounter_id}")
        # We'll get patient info from EHR sections or create a minimal encounter
        ehr_sections = session_data.get("ehr_sections", {})
        
        # Create a minimal patient object for the session
        patient = type('Patient', (), {
            'id': str(uuid.uuid4()),
            'ehr_id': session_data.get('patient_ehr_id', ''),
            'mrn': session_data.get('patient_mrn', 'TEMP-MRN'),
            'first_name': session_data.get('patient_first_name', 'Unknown'),
            'last_name': session_data.get('patient_last_name', 'Patient'),
            'date_of_birth': None,
            'gender': session_data.get('patient_gender', 'unknown'),
            'allergies': ehr_sections.get('allergies'),
            'smoking_history': ehr_sections.get('social_history')
        })()
        
        # Create a minimal encounter object
        encounter = type('Encounter', (), {
            'id': encounter_id,
            'patient_id': patient.id,
            'patient': patient,
            'user_id': current_user.id,
            'chief_complaint': ehr_sections.get('chief_complaint', 'Medical consultation'),
            'encounter_date': datetime.utcnow(),
            'encounter_type': 'office_visit',
            'provider_name': session_data.get('provider_name', current_user.full_name),
            'location': session_data.get('location', 'Medical Office')
        })()
    else:
        # Try to find real encounter
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
        
        patient = encounter.patient
    
    # Create transcription record for streaming session
    # For temporary encounters, create the transcription without a real encounter_id
    if encounter_id.startswith("temp-"):
        transcription = Transcription(
            encounter_id=None,  # No real encounter ID for temporary sessions
            audio_file_path=None,  # No audio file for streaming
            status="streaming",
            progress=0
        )
    else:
        transcription = Transcription(
            encounter_id=encounter.id,
            audio_file_path=None,  # No audio file for streaming
            status="streaming",
            progress=0
        )
    
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Initialize session context
    session_id = str(transcription.id)
    
    # Include EHR data if provided in session_data
    ehr_sections = session_data.get("ehr_sections", {})
    logger.info(f"Received EHR sections for session {session_id}: {list(ehr_sections.keys()) if ehr_sections else 'None'}")
    if ehr_sections:
        for section, content in ehr_sections.items():
            if content:
                logger.info(f"EHR section '{section}': {str(content)[:100]}...")
    
    handoff_context.create_session(session_id, {
        "transcription_id": session_id,
        "encounter_id": str(encounter.id),
        "patient_id": str(patient.id),
        "format_preference": session_data.get("format_preference", "soap"),
        "streaming_mode": True,
        "transcript_chunks": [],
        "patient_context": {
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "age": _calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
            "chief_complaint": encounter.chief_complaint,
            "encounter_date": encounter.encounter_date.isoformat(),
            "provider_name": encounter.provider_name,
            "location": encounter.location,
            "encounter_type": encounter.encounter_type,
            # Include any additional patient data
            "allergies": patient.allergies if hasattr(patient, 'allergies') else None,
            "smoking_history": patient.smoking_history if hasattr(patient, 'smoking_history') else None,
            "ehr_id": patient.ehr_id if hasattr(patient, 'ehr_id') else None
        },
        "ehr_sections": ehr_sections  # Pre-populated sections from EHR
    })
    
    # Notify via SSE
    channel = f"transcription:{session_id}"
    await sse_manager.publish(channel, {
        "type": "streaming_started",
        "data": {
            "transcription_id": session_id,
            "status": "streaming",
            "message": "Streaming session started"
        }
    })
    
    return {
        "session_id": session_id,
        "transcription_id": session_id,
        "status": "streaming",
        "sse_endpoint": f"/api/v1/sse/transcription/{session_id}"
    }


@router.post("/{session_id}/text")
async def stream_text_chunk(
    session_id: str,
    text_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Stream a text chunk to the transcription session"""
    
    # Verify session exists
    try:
        transcription_uuid = uuid.UUID(session_id)
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_uuid
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify access - for temporary encounters, check if transcription exists
    if transcription.encounter_id and transcription.encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get text chunk
    text_chunk = text_data.get("text", "")
    is_final = text_data.get("is_final", False)
    timestamp = text_data.get("timestamp", datetime.utcnow().isoformat())
    
    # Update session context with new text
    context = handoff_context.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session context not found")
    
    # Append to transcript chunks
    context["transcript_chunks"].append({
        "text": text_chunk,
        "timestamp": timestamp,
        "is_final": is_final
    })
    
    # Update full transcript
    full_transcript = " ".join([chunk["text"] for chunk in context["transcript_chunks"]])
    context["transcript"] = full_transcript
    handoff_context.update_context(session_id, context)
    
    # Update database
    transcription.transcript = full_transcript
    transcription.updated_at = datetime.utcnow()
    db.commit()
    
    # Notify via SSE
    channel = f"transcription:{session_id}"
    await sse_manager.publish(channel, {
        "type": "transcription_chunk",
        "data": {
            "chunk": text_chunk,
            "is_final": is_final,
            "timestamp": timestamp,
            "total_length": len(full_transcript)
        }
    })
    
    # If we have enough text, trigger agent processing
    word_count = len(full_transcript.split())
    if word_count >= 50 and word_count % 50 == 0:  # Process every 50 words
        # Trigger agent analysis in background
        await _trigger_incremental_analysis(session_id, full_transcript)
    
    return {
        "status": "received",
        "chunk_length": len(text_chunk),
        "total_length": len(full_transcript)
    }


@router.post("/{session_id}/end")
async def end_streaming_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """End a streaming session and trigger final processing"""
    
    # Verify session exists
    try:
        transcription_uuid = uuid.UUID(session_id)
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_uuid
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify access - for temporary encounters, check if transcription exists
    if transcription.encounter_id and transcription.encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update status
    transcription.status = "processing"
    db.commit()
    
    # Get final transcript
    context = handoff_context.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session context not found")
    
    final_transcript = context.get("transcript", "")
    
    # Notify via SSE
    channel = f"transcription:{session_id}"
    await sse_manager.publish(channel, {
        "type": "streaming_ended",
        "data": {
            "transcription_id": session_id,
            "status": "processing",
            "message": "Streaming ended, processing final transcript",
            "transcript_length": len(final_transcript)
        }
    })
    
    # Trigger full agent processing
    await _trigger_final_processing(session_id, transcription, db)
    
    return {
        "status": "ended",
        "transcription_id": session_id,
        "processing": True
    }


async def _trigger_incremental_analysis(session_id: str, transcript: str):
    """Trigger incremental analysis by agents"""
    
    try:
        # Update context to trigger partial analysis
        handoff_context.update_context(session_id, {
            "partial_analysis_requested": True,
            "analysis_checkpoint": len(transcript)
        })
        
        # Send progress update
        channel = f"transcription:{session_id}"
        await sse_manager.publish(channel, {
            "type": "analysis_update",
            "data": {
                "message": "Analyzing transcript...",
                "checkpoint": len(transcript.split())
            }
        })
        
    except Exception as e:
        logger.error(f"Error triggering incremental analysis: {e}")


async def _trigger_final_processing(session_id: str, transcription: Transcription, db: Session):
    """Trigger final processing by the agent pipeline"""
    
    try:
        # Run the medical scribe supervisor
        result = await medical_scribe_supervisor.process_streaming_transcript(
            session_id=session_id
        )
        
        # Get the sections from context and publish them
        context = handoff_context.get_context(session_id)
        sections_for_sse = context.get("sections_for_sse", {}) if context else {}
        
        channel = f"transcription:{session_id}"
        
        # Publish individual section completion events
        for section, section_data in sections_for_sse.items():
            await sse_manager.publish(channel, {
                "type": "section_completed",
                "data": {
                    "section": section,
                    "content": section_data["content"],
                    "confidence": section_data["confidence"]
                }
            })
            logger.info(f"Published section_completed event for: {section}")
        
        # Update transcription status
        transcription.status = "completed"
        transcription.completed_at = datetime.utcnow()
        transcription.progress = 100
        db.commit()
        
        # Send completion event
        await sse_manager.publish(channel, {
            "type": "completed",
            "data": {
                "transcription_id": session_id,
                "status": "completed",
                "message": "Processing completed",
                "sections_published": len(sections_for_sse)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in final processing: {e}")
        
        # Update status to failed
        transcription.status = "failed"
        transcription.error_message = str(e)
        db.commit()
        
        # Send error event
        channel = f"transcription:{session_id}"
        await sse_manager.publish(channel, {
            "type": "error",
            "data": {
                "error": str(e),
                "transcription_id": session_id
            }
        })


@router.websocket("/{session_id}/ws")
async def websocket_streaming(
    websocket: WebSocket,
    session_id: str,
    token: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for bidirectional streaming (alternative to REST)"""
    
    # Authenticate via token
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if not email:
            await websocket.close(code=4001, reason="Invalid token")
            return
            
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except Exception as e:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Verify session
    try:
        transcription_uuid = uuid.UUID(session_id)
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_uuid
        ).first()
        
        if not transcription or transcription.encounter.user_id != user.id:
            await websocket.close(code=4004, reason="Session not found")
            return
    except ValueError:
        await websocket.close(code=4000, reason="Invalid session ID")
        return
    
    await websocket.accept()
    
    try:
        while True:
            # Receive text chunks
            data = await websocket.receive_json()
            
            if data.get("type") == "text_chunk":
                # Process text chunk
                text_chunk = data.get("text", "")
                is_final = data.get("is_final", False)
                
                # Update context
                context = handoff_context.get_context(session_id)
                if context:
                    context["transcript_chunks"].append({
                        "text": text_chunk,
                        "timestamp": datetime.utcnow().isoformat(),
                        "is_final": is_final
                    })
                    
                    full_transcript = " ".join([chunk["text"] for chunk in context["transcript_chunks"]])
                    context["transcript"] = full_transcript
                    handoff_context.update_context(session_id, context)
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "ack",
                        "chunk_received": len(text_chunk),
                        "total_length": len(full_transcript)
                    })
                    
            elif data.get("type") == "end_session":
                # End streaming session
                await _trigger_final_processing(session_id, transcription, db)
                await websocket.send_json({
                    "type": "session_ended",
                    "status": "processing"
                })
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=4002, reason=str(e))