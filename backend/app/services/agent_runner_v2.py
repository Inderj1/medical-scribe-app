"""Agent Runner Service v2 using OpenAI Agents SDK"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.agents_v2 import orchestrator
from app.core.sse_manager import sse_manager
from app.services.ehrbase.client import EHRBaseClient
from app.db.session import SessionLocal, get_redis

logger = logging.getLogger(__name__)


async def run_agent_workflow(
    transcription_id: str,
    audio_path: str,
    patient_id: str,
    encounter_id: str,
    format_preference: str = "soap",
    language: str = "en"
) -> Dict[str, Any]:
    """Run the complete agent workflow for audio transcription"""
    
    channel = f"transcription_{transcription_id}"
    
    try:
        logger.info(f"Starting agent workflow for transcription {transcription_id}")
        
        # Get patient and encounter context
        patient_context = await _get_patient_context(patient_id, encounter_id)
        
        # Run the orchestrator
        result = await orchestrator.process_audio_transcription(
            transcription_id=transcription_id,
            audio_path=audio_path,
            patient_context=patient_context,
            format_preference=format_preference,
            language=language
        )
        
        if result["success"]:
            # Update database with completion
            await _update_transcription_complete(transcription_id)
            
            # Send final SSE event
            await sse_manager.publish(channel, {
                "type": "workflow_complete",
                "data": {
                    "transcription_id": transcription_id,
                    "success": True,
                    "final_agent": result.get("final_agent", "unknown")
                }
            })
        else:
            # Handle error
            await _update_transcription_error(transcription_id, result.get("error", "Unknown error"))
            
            await sse_manager.publish(channel, {
                "type": "workflow_error",
                "data": {
                    "transcription_id": transcription_id,
                    "error": result.get("error")
                }
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in agent workflow: {str(e)}")
        await _update_transcription_error(transcription_id, str(e))
        
        await sse_manager.publish(channel, {
            "type": "workflow_error",
            "data": {
                "transcription_id": transcription_id,
                "error": str(e)
            }
        })
        
        raise


async def process_streaming_session(
    session_id: str,
    transcription_id: str,
    patient_id: str,
    encounter_id: str,
    format_preference: str = "soap"
) -> Dict[str, Any]:
    """Process a completed streaming session"""
    
    try:
        logger.info(f"Processing streaming session {session_id}")
        
        # Get patient context
        patient_context = await _get_patient_context(patient_id, encounter_id)
        
        # Run the orchestrator
        result = await orchestrator.process_streaming_transcript(
            session_id=session_id,
            transcription_id=transcription_id,
            patient_context=patient_context,
            format_preference=format_preference
        )
        
        if result["success"]:
            await _update_transcription_complete(transcription_id)
        else:
            await _update_transcription_error(transcription_id, result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing streaming session: {str(e)}")
        await _update_transcription_error(transcription_id, str(e))
        raise


async def update_progress(transcription_id: str, percentage: int, status: str) -> None:
    """Update processing progress"""
    channel = f"transcription_{transcription_id}"
    
    await sse_manager.publish(channel, {
        "type": "progress_update",
        "data": {
            "transcription_id": transcription_id,
            "progress_percentage": percentage,
            "status": status
        }
    })
    
    # Update in database
    with SessionLocal() as db:
        transcription = db.query(Transcription).filter_by(id=transcription_id).first()
        if transcription:
            transcription.progress_percentage = percentage
            transcription.processing_status = status
            db.commit()


async def _get_patient_context(patient_id: str, encounter_id: str) -> Dict[str, Any]:
    """Get patient and encounter context including EHR data"""
    
    with SessionLocal() as db:
        # Get patient
        patient = db.query(Patient).filter_by(id=patient_id).first()
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        # Get encounter
        encounter = db.query(Encounter).filter_by(id=encounter_id).first()
        if not encounter:
            raise ValueError(f"Encounter {encounter_id} not found")
        
        # Build context
        patient_context = {
            "patient_id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender,
            "mrn": patient.mrn,
            "encounter_id": encounter.id,
            "encounter_date": encounter.encounter_date.isoformat() if encounter.encounter_date else None,
            "chief_complaint": encounter.chief_complaint,
            "provider_name": encounter.provider_name
        }
        
        # Get allergies and medications if available
        if patient.allergies:
            patient_context["allergies"] = patient.allergies
        
        if patient.current_medications:
            patient_context["medications"] = patient.current_medications
        
        # Get EHR data if available
        try:
            ehr_sections = await _fetch_ehr_sections(patient.mrn, encounter.id)
            if ehr_sections:
                patient_context["ehr_sections"] = ehr_sections
        except Exception as e:
            logger.error(f"Error fetching EHR data: {str(e)}")
        
        return patient_context


async def _fetch_ehr_sections(mrn: str, encounter_id: str) -> Optional[Dict[str, Any]]:
    """Fetch relevant sections from EHRBase"""
    
    try:
        ehr_client = EHRBaseClient()
        
        # Get patient EHR ID
        patient_ehr_id = await ehr_client.get_patient_ehr_id(mrn)
        if not patient_ehr_id:
            return None
        
        # Fetch relevant data
        sections = {}
        
        # Get medications
        medications = await ehr_client.get_medications(patient_ehr_id)
        if medications:
            sections["medications"] = medications
        
        # Get allergies
        allergies = await ehr_client.get_allergies(patient_ehr_id)
        if allergies:
            sections["allergies"] = allergies
        
        # Get recent vitals
        vitals = await ehr_client.get_recent_vitals(patient_ehr_id)
        if vitals:
            sections["vitals"] = vitals
        
        # Get problem list
        problems = await ehr_client.get_problem_list(patient_ehr_id)
        if problems:
            sections["problem_list"] = problems
        
        return sections if sections else None
        
    except Exception as e:
        logger.error(f"Error fetching EHR sections: {str(e)}")
        return None


async def _update_transcription_complete(transcription_id: str):
    """Update transcription as completed"""
    
    with SessionLocal() as db:
        transcription = db.query(Transcription).filter_by(id=transcription_id).first()
        if transcription:
            transcription.status = "completed"
            transcription.progress_percentage = 100
            transcription.completed_at = datetime.utcnow()
            db.commit()


async def _update_transcription_error(transcription_id: str, error: str):
    """Update transcription with error"""
    
    with SessionLocal() as db:
        transcription = db.query(Transcription).filter_by(id=transcription_id).first()
        if transcription:
            transcription.status = "error"
            transcription.error_message = error
            transcription.completed_at = datetime.utcnow()
            db.commit()


async def cleanup_old_sessions():
    """Cleanup old sessions periodically"""
    
    while True:
        try:
            # Clean up sessions older than 1 hour
            await asyncio.sleep(3600)  # Run every hour
            
            # This is now handled by the orchestrator's cleanup mechanism
            logger.info("Session cleanup task running")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Retry after 1 minute