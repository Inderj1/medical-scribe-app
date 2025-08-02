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
    
    try:
        logger.info(f"Starting streaming session for user {current_user.email}")
        logger.info(f"Session data received: {session_data}")
    except Exception as e:
        logger.error(f"Error in start_streaming_session: {str(e)}")
        raise
    
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
            'gender': session_data.get('patient_gender', 'UNKNOWN').upper(),
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
            # First try as UUID
            encounter_uuid = uuid.UUID(encounter_id)
            encounter = db.query(Encounter).filter(
                Encounter.id == encounter_uuid,
                Encounter.user_id == current_user.id
            ).first()
        except ValueError:
            # If not a valid UUID, treat as temporary encounter
            logger.warning(f"Invalid UUID format for encounter_id: {encounter_id}, treating as temporary")
            encounter_id = f"temp-{encounter_id}"
            
            # Create temporary patient and encounter objects
            ehr_sections = session_data.get("ehr_sections", {})
            
            patient = type('Patient', (), {
                'id': str(uuid.uuid4()),
                'ehr_id': session_data.get('patient_ehr_id', ''),
                'mrn': session_data.get('patient_mrn', 'TEMP-MRN'),
                'first_name': session_data.get('patient_first_name', 'Unknown'),
                'last_name': session_data.get('patient_last_name', 'Patient'),
                'date_of_birth': None,
                'gender': session_data.get('patient_gender', 'UNKNOWN').upper(),
                'allergies': ehr_sections.get('allergies'),
                'smoking_history': ehr_sections.get('social_history')
            })()
            
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
        
        if not encounter and not encounter_id.startswith("temp-"):
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        patient = encounter.patient
    
    # Create transcription record for streaming session
    # For temporary encounters, we need to create a real encounter first
    if encounter_id.startswith("temp-"):
        # Create a temporary patient first or get existing one
        from app.models.patient import Patient
        
        # Check if patient with this MRN already exists
        existing_patient = db.query(Patient).filter(
            Patient.mrn == patient.mrn
        ).first()
        
        if existing_patient:
            temp_patient = existing_patient
            logger.info(f"Using existing patient with MRN: {patient.mrn}")
        else:
            temp_patient = Patient(
                ehr_id=patient.ehr_id if hasattr(patient, 'ehr_id') else f"temp-ehr-{uuid.uuid4()}",
                mrn=patient.mrn,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth if hasattr(patient, 'date_of_birth') and patient.date_of_birth else datetime(1900, 1, 1).date(),
                gender=patient.gender.upper() if patient.gender else 'UNKNOWN'
            )
            db.add(temp_patient)
            db.flush()  # Get the patient ID
        
        # Create a real encounter for the temporary session
        real_encounter = Encounter(
            user_id=current_user.id,
            patient_id=temp_patient.id,  # Use the temporary patient
            chief_complaint=encounter.chief_complaint,
            encounter_date=encounter.encounter_date,
            encounter_type=encounter.encounter_type,
            provider_name=encounter.provider_name,
            location=encounter.location,
            status="ACTIVE"
        )
        db.add(real_encounter)
        db.flush()  # Flush to get the ID
        
        transcription = Transcription(
            encounter_id=real_encounter.id,
            audio_file_path=None,  # No audio file for streaming
            status="streaming",
            progress=0,
            speaker_count=1  # Default to 1, will be updated if multiple speakers detected
        )
    else:
        transcription = Transcription(
            encounter_id=encounter.id,
            audio_file_path=None,  # No audio file for streaming
            status="streaming",
            progress=0,
            speaker_count=1  # Default to 1, will be updated if multiple speakers detected
        )
    
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Initialize session context
    session_id = str(transcription.id)
    
    # Include EHR data if provided in session_data
    ehr_sections = session_data.get("ehr_sections", {})
    
    # Initialize speaker tracking
    enable_speaker_diarization = session_data.get("enable_speaker_diarization", False)
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
        "speakers": set(),  # Track unique speakers
        "speaker_count": 0,
        "enable_speaker_diarization": enable_speaker_diarization,
        "patient_context": {
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender.upper() if hasattr(patient, 'gender') and patient.gender else 'UNKNOWN',
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
    
    # Get text chunk with speaker info
    text_chunk = text_data.get("text", "")
    is_final = text_data.get("is_final", False)
    timestamp = text_data.get("timestamp", datetime.utcnow().isoformat())
    speaker_id = text_data.get("speaker_id", "SPEAKER_00")  # Default speaker
    
    logger.info(f"[STREAMING] Received text chunk for session {session_id}: '{text_chunk}' (is_final: {is_final}, speaker: {speaker_id})")
    
    # Update session context with new text
    context = handoff_context.get_context(session_id)
    if not context:
        # If context is lost but transcription exists, check if we can recreate it
        if transcription.status == "processing":
            raise HTTPException(
                status_code=409, 
                detail="Session is already being processed. Cannot add more text."
            )
        elif transcription.status == "completed":
            raise HTTPException(
                status_code=409, 
                detail="Session is already completed. Cannot add more text."
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail="Session context not found. Please start a new session."
            )
    
    # Initialize speaker tracking if needed
    if "speakers" not in context:
        context["speakers"] = set()
    context["speakers"].add(speaker_id)
    
    # Initialize or update last analysis timestamp
    if "last_analysis_time" not in context:
        context["last_analysis_time"] = datetime.utcnow()
    if "last_analysis_word_count" not in context:
        context["last_analysis_word_count"] = 0
    
    # Append to transcript chunks
    context["transcript_chunks"].append({
        "text": text_chunk,
        "timestamp": timestamp,
        "is_final": is_final,
        "speaker_id": speaker_id
    })
    
    # Update full transcript
    full_transcript = " ".join([chunk["text"] for chunk in context["transcript_chunks"]])
    context["transcript"] = full_transcript
    context["speaker_count"] = len(context["speakers"])
    handoff_context.update_context(session_id, context)
    
    logger.info(f"[STREAMING] Updated transcript - Total chunks: {len(context['transcript_chunks'])}, Full transcript length: {len(full_transcript)} chars")
    
    # Update database
    transcription.transcript = full_transcript
    transcription.updated_at = datetime.utcnow()
    if context["speaker_count"] > 1:
        transcription.speaker_count = context["speaker_count"]
    db.commit()
    
    # Notify via SSE
    channel = f"transcription:{session_id}"
    await sse_manager.publish(channel, {
        "type": "transcription_chunk",
        "data": {
            "chunk": text_chunk,
            "is_final": is_final,
            "timestamp": timestamp,
            "total_length": len(full_transcript),
            "speaker_id": speaker_id,
            "speaker_count": context["speaker_count"]
        }
    })
    
    # If we have enough text, trigger agent processing
    word_count = len(full_transcript.split())
    logger.info(f"[STREAMING] Current transcript word count: {word_count} words")
    
    # Check if we should trigger analysis based on words or time
    time_since_last_analysis = (datetime.utcnow() - context["last_analysis_time"]).total_seconds()
    words_since_last_analysis = word_count - context["last_analysis_word_count"]
    
    # Trigger analysis if:
    # 1. We have at least 5 new words, OR
    # 2. It's been 5 seconds since last analysis AND we have at least 3 new words
    should_analyze = (
        (words_since_last_analysis >= 5) or 
        (time_since_last_analysis >= 5 and words_since_last_analysis >= 3)
    )
    
    if should_analyze and word_count >= 3:  # Minimum 3 words total
        logger.info(f"[STREAMING] Triggering incremental analysis: {word_count} words, "
                   f"{words_since_last_analysis} new words, {time_since_last_analysis:.1f}s since last analysis")
        
        # Update tracking
        context["last_analysis_time"] = datetime.utcnow()
        context["last_analysis_word_count"] = word_count
        handoff_context.update_context(session_id, context)
        
        # Trigger agent analysis in background
        await _trigger_incremental_analysis(session_id, full_transcript)
    
    return {
        "status": "received",
        "chunk_length": len(text_chunk),
        "total_length": len(full_transcript),
        "speaker_id": speaker_id,
        "speaker_count": context["speaker_count"]
    }


@router.get("/{session_id}/sections")
async def get_session_sections(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all completed sections for a streaming session"""
    
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
    
    # Verify access
    if transcription.encounter_id and transcription.encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get sections from context
    context = handoff_context.get_context(session_id)
    if not context:
        logger.warning(f"No context found for session {session_id}, returning empty sections")
        return {"sections": {}}
    
    # Get the sections that have been processed
    sections_for_sse = context.get("sections_for_sse", {})
    clinical_data = context.get("clinical_data", {})
    
    # Combine both sources of section data
    all_sections = {}
    
    # Add sections from SSE (these are the formatted sections ready for display)
    for section, section_data in sections_for_sse.items():
        all_sections[section] = {
            "content": section_data.get("content", ""),
            "confidence": section_data.get("confidence", 0.0),
            "source": "agent_processing"
        }
    
    # Add any clinical data sections that might not be in sections_for_sse
    for section, content in clinical_data.items():
        if section not in all_sections and content:
            all_sections[section] = {
                "content": content,
                "confidence": 1.0,
                "source": "clinical_analysis"
            }
    
    logger.info(f"[SECTIONS] Returning {len(all_sections)} sections for session {session_id}: {list(all_sections.keys())}")
    
    return {
        "sections": all_sections,
        "transcription_status": transcription.status,
        "last_updated": context.get("last_update_time", datetime.utcnow()).isoformat()
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
    
    # Check if session is already in final state
    if transcription.status == "processing":
        logger.info(f"[STREAMING] Session {session_id} already processing, returning success")
        return {
            "status": "already_processing",
            "transcription_id": session_id,
            "message": "Session is already being processed"
        }
    elif transcription.status == "completed":
        logger.info(f"[STREAMING] Session {session_id} already completed, returning success")
        return {
            "status": "already_completed", 
            "transcription_id": session_id,
            "message": "Session is already completed"
        }
    
    # Get final transcript
    context = handoff_context.get_context(session_id)
    if not context:
        logger.error(f"[STREAMING] No context found for session {session_id}")
        raise HTTPException(
            status_code=404, 
            detail="Session context not found. Please start a new session."
        )
    
    # Update status to processing
    transcription.status = "processing"
    db.commit()
    
    final_transcript = context.get("transcript", "")
    logger.info(f"[STREAMING] End session {session_id} - Transcript length: {len(final_transcript)} chars, Word count: {len(final_transcript.split()) if final_transcript else 0} words")
    logger.info(f"[STREAMING] Transcript preview: {final_transcript[:200]}..." if final_transcript else "[STREAMING] Empty transcript!")
    logger.info(f"[STREAMING] Transcript chunks count: {len(context.get('transcript_chunks', []))}")
    
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
        logger.info(f"[INCREMENTAL] Starting incremental analysis for session {session_id}, transcript length: {len(transcript)} chars")
        
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
        
        # Run the medical scribe supervisor for incremental analysis
        logger.info(f"[INCREMENTAL] Running agent processing for session {session_id}")
        result = await medical_scribe_supervisor.process_streaming_transcript(
            session_id=session_id
        )
        logger.info(f"[INCREMENTAL] Agent processing result: {result}")
        
        # Get the sections from context and publish them
        context = handoff_context.get_context(session_id)
        sections_for_sse = context.get("sections_for_sse", {}) if context else {}
        logger.info(f"[INCREMENTAL] Found {len(sections_for_sse)} sections to publish: {list(sections_for_sse.keys())}")
        
        # Publish individual section completion events
        for section, section_data in sections_for_sse.items():
            # Get current subscriber count for debugging
            subscriber_count = sse_manager.get_subscriber_count(channel)
            logger.info(f"[INCREMENTAL] Publishing section_completed for '{section}' to {subscriber_count} subscribers")
            
            await sse_manager.publish(channel, {
                "type": "section_completed",
                "data": {
                    "section": section,
                    "content": section_data["content"],
                    "confidence": section_data["confidence"]
                }
            })
            logger.info(f"[INCREMENTAL] Published section_completed event for: {section} (content length: {len(section_data['content'])})")
        
    except Exception as e:
        logger.error(f"[INCREMENTAL] Error triggering incremental analysis: {e}", exc_info=True)


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
                speaker_id = data.get("speaker_id", "SPEAKER_00")  # Default speaker
                
                # Update context
                context = handoff_context.get_context(session_id)
                if context:
                    # Initialize speaker tracking if needed
                    if "speakers" not in context:
                        context["speakers"] = set()
                    context["speakers"].add(speaker_id)
                    
                    context["transcript_chunks"].append({
                        "text": text_chunk,
                        "timestamp": datetime.utcnow().isoformat(),
                        "is_final": is_final,
                        "speaker_id": speaker_id
                    })
                    
                    # Build full transcript with speaker labels
                    full_transcript = " ".join([chunk["text"] for chunk in context["transcript_chunks"]])
                    context["transcript"] = full_transcript
                    context["speaker_count"] = len(context["speakers"])
                    handoff_context.update_context(session_id, context)
                    
                    # Update transcription with speaker count
                    if context["speaker_count"] > 1:
                        transcription.speaker_count = context["speaker_count"]
                        db.commit()
                    
                    # Send acknowledgment with speaker info
                    await websocket.send_json({
                        "type": "ack",
                        "chunk_received": len(text_chunk),
                        "total_length": len(full_transcript),
                        "speaker_id": speaker_id,
                        "speaker_count": context["speaker_count"]
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