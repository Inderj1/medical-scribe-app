"""Agent Runner Service for background processing"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid

from sqlalchemy.orm import Session

from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.agents.medical_scribe_supervisor import medical_scribe_supervisor
from app.agents.context_manager import handoff_context
from app.core.sse_manager import sse_manager
from app.services.ehrbase.client import EHRBaseClient
from app.db.session import SessionLocal, get_redis

logger = logging.getLogger(__name__)


async def run_agent_processing(
    transcription_id: str,
    audio_file_path: str,
    format_preference: str = "soap"
) -> None:
    """Run agent processing pipeline for audio transcription"""
    
    db = SessionLocal()
    redis = get_redis()
    channel = f"transcription:{transcription_id}"
    
    try:
        # Update status to processing
        transcription = db.query(Transcription).filter(
            Transcription.id == uuid.UUID(transcription_id)
        ).first()
        
        if not transcription:
            logger.error(f"Transcription {transcription_id} not found")
            return
        
        transcription.status = "processing"
        transcription.progress = 0
        db.commit()
        
        # Send initial SSE event
        await sse_manager.publish(channel, {
            "type": "processing_started",
            "data": {
                "transcription_id": transcription_id,
                "status": "processing",
                "message": "Agent processing started"
            }
        })
        
        # Get encounter and patient data
        encounter = transcription.encounter
        patient = encounter.patient
        
        # Initialize handoff context with full patient info
        handoff_context.create_session(transcription_id, {
            "audio_file_path": audio_file_path,
            "format_preference": format_preference,
            "transcription_id": transcription_id,
            "encounter_id": str(encounter.id),
            "patient_id": str(patient.id),
            "patient_context": {
                "mrn": patient.mrn,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "gender": patient.gender,
                "age": _calculate_age(patient.date_of_birth),
                "chief_complaint": encounter.chief_complaint,
                "encounter_date": encounter.encounter_date.isoformat(),
                "provider_name": encounter.provider_name,
                "location": encounter.location
            }
        })
        
        # Get EHRBase patient summary if available
        if patient.ehr_id:
            try:
                ehrbase_client = EHRBaseClient()
                patient_summary = await ehrbase_client.get_patient_summary(patient.ehr_id)
                handoff_context.update_context(transcription_id, {
                    "ehr_patient_summary": patient_summary
                })
                await ehrbase_client.close()
            except Exception as e:
                logger.warning(f"Could not fetch EHRBase summary: {str(e)}")
        
        # Run agent pipeline
        logger.info(f"Starting agent pipeline for transcription {transcription_id}")
        
        # Execute supervisor agent (runs in sync thread due to Swarm)
        result = await asyncio.to_thread(
            medical_scribe_supervisor.process_audio,
            transcription_id
        )
        
        # Get final context
        final_context = handoff_context.get_context(transcription_id)
        
        if final_context.get("error"):
            # Handle error
            transcription.status = "failed"
            transcription.error_message = final_context["error"]
            db.commit()
            
            await sse_manager.publish(channel, {
                "type": "error",
                "data": {
                    "error": final_context["error"],
                    "transcription_id": transcription_id
                }
            })
            
        else:
            # Save results
            transcription.transcript = final_context.get("transcript", "")
            transcription.audio_duration_seconds = final_context.get("audio_duration")
            transcription.status = "completed"
            transcription.progress = 100
            transcription.completed_at = datetime.utcnow()
            
            # Create clinical note
            clinical_sections = final_context.get("clinical_sections", {})
            structured_note = final_context.get("structured_note", {})
            quality_results = final_context.get("quality_assessment", {})
            
            clinical_note = ClinicalNote(
                transcription_id=transcription.id,
                encounter_id=transcription.encounter_id,
                format_type=format_preference,
                chief_complaint=clinical_sections.get("chief_complaint"),
                history_present_illness=clinical_sections.get("history_of_present_illness"),
                review_of_systems=clinical_sections.get("review_of_systems"),
                past_medical_history=clinical_sections.get("past_medical_history"),
                past_surgical_history=clinical_sections.get("past_surgical_history"),
                medications=clinical_sections.get("medications"),
                allergies=clinical_sections.get("allergies"),
                social_history=clinical_sections.get("social_history"),
                family_history=clinical_sections.get("family_history"),
                physical_exam=clinical_sections.get("physical_examination"),
                diagnostic_results=clinical_sections.get("diagnostic_results"),
                subjective=structured_note.get("subjective"),
                objective=structured_note.get("objective"),
                assessment=structured_note.get("assessment"),
                plan=structured_note.get("plan"),
                quality_score=quality_results.get("overall_score", 0.0),
                ai_confidence_scores=quality_results
            )
            
            db.add(clinical_note)
            db.commit()
            
            # Save to EHRBase if patient has EHR ID
            if patient.ehr_id:
                try:
                    ehrbase_client = EHRBaseClient()
                    composition = await _create_ehr_composition(
                        ehrbase_client,
                        patient.ehr_id,
                        clinical_note,
                        clinical_sections
                    )
                    clinical_note.ehr_composition_id = composition.get("uid")
                    db.commit()
                    await ehrbase_client.close()
                except Exception as e:
                    logger.error(f"Failed to save to EHRBase: {str(e)}")
            
            # Send completion event
            await sse_manager.publish(channel, {
                "type": "completed",
                "data": {
                    "transcription_id": transcription_id,
                    "status": "completed",
                    "clinical_note_id": str(clinical_note.id),
                    "quality_score": clinical_note.quality_score
                }
            })
            
            logger.info(f"Agent pipeline completed for transcription {transcription_id}")
        
    except Exception as e:
        logger.error(f"Agent processing error for {transcription_id}: {str(e)}")
        
        # Update status
        if transcription:
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
        
        # Send error event
        await sse_manager.publish(channel, {
            "type": "error",
            "data": {
                "error": str(e),
                "transcription_id": transcription_id
            }
        })
        
    finally:
        # Cleanup
        handoff_context.delete_session(transcription_id)
        db.close()
        
        # Store final status in Redis for 1 hour
        redis.setex(
            f"transcription:status:{transcription_id}",
            3600,
            json.dumps({
                "status": transcription.status if transcription else "unknown",
                "completed_at": datetime.utcnow().isoformat()
            })
        )


async def update_progress(
    transcription_id: str,
    progress: int,
    message: str
) -> None:
    """Update transcription progress and send SSE event"""
    
    db = SessionLocal()
    channel = f"transcription:{transcription_id}"
    
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == uuid.UUID(transcription_id)
        ).first()
        
        if transcription:
            transcription.progress = progress
            db.commit()
        
        # Send progress event
        await sse_manager.publish(channel, {
            "type": "progress",
            "data": {
                "transcription_id": transcription_id,
                "progress": progress,
                "message": message
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
    finally:
        db.close()


def _calculate_age(date_of_birth) -> Optional[int]:
    """Calculate age from date of birth"""
    if not date_of_birth:
        return None
    today = datetime.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


async def _create_ehr_composition(
    ehrbase_client: EHRBaseClient,
    ehr_id: str,
    clinical_note: ClinicalNote,
    clinical_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create composition in EHRBase"""
    
    # Create OpenEHR composition
    composition = {
        "_type": "COMPOSITION",
        "name": {
            "_type": "DV_TEXT",
            "value": "Clinical Encounter Note"
        },
        "archetype_node_id": "openEHR-EHR-COMPOSITION.encounter.v1",
        "language": {
            "_type": "CODE_PHRASE",
            "terminology_id": {
                "_type": "TERMINOLOGY_ID",
                "value": "ISO_639-1"
            },
            "code_string": "en"
        },
        "territory": {
            "_type": "CODE_PHRASE",
            "terminology_id": {
                "_type": "TERMINOLOGY_ID",
                "value": "ISO_3166-1"
            },
            "code_string": "US"
        },
        "category": {
            "_type": "DV_CODED_TEXT",
            "value": "event",
            "defining_code": {
                "_type": "CODE_PHRASE",
                "terminology_id": {
                    "_type": "TERMINOLOGY_ID",
                    "value": "openehr"
                },
                "code_string": "433"
            }
        },
        "composer": {
            "_type": "PARTY_IDENTIFIED",
            "name": "Medical Scribe AI"
        },
        "content": []
    }
    
    # Add chief complaint
    if clinical_note.chief_complaint:
        composition["content"].append({
            "_type": "EVALUATION",
            "name": {"value": "Chief Complaint"},
            "archetype_node_id": "openEHR-EHR-EVALUATION.reason_for_encounter.v1",
            "data": {
                "_type": "ITEM_TREE",
                "archetype_node_id": "at0001",
                "items": [{
                    "_type": "ELEMENT",
                    "name": {"value": "Presenting complaint"},
                    "archetype_node_id": "at0002",
                    "value": {
                        "_type": "DV_TEXT",
                        "value": clinical_note.chief_complaint
                    }
                }]
            }
        })
    
    # Add history of present illness
    if clinical_note.history_present_illness:
        composition["content"].append({
            "_type": "EVALUATION",
            "name": {"value": "History of Present Illness"},
            "archetype_node_id": "openEHR-EHR-EVALUATION.clinical_synopsis.v1",
            "data": {
                "_type": "ITEM_TREE",
                "archetype_node_id": "at0001",
                "items": [{
                    "_type": "ELEMENT",
                    "name": {"value": "Synopsis"},
                    "archetype_node_id": "at0002",
                    "value": {
                        "_type": "DV_TEXT",
                        "value": clinical_note.history_present_illness
                    }
                }]
            }
        })
    
    # Add medications if present
    if clinical_note.medications:
        composition["content"].append({
            "_type": "EVALUATION",
            "name": {"value": "Medication Summary"},
            "archetype_node_id": "openEHR-EHR-EVALUATION.medication_summary.v0",
            "data": {
                "_type": "ITEM_TREE",
                "archetype_node_id": "at0001",
                "items": [{
                    "_type": "ELEMENT",
                    "name": {"value": "Summary"},
                    "archetype_node_id": "at0002",
                    "value": {
                        "_type": "DV_TEXT",
                        "value": clinical_note.medications
                    }
                }]
            }
        })
    
    # Add assessment and plan
    if clinical_note.assessment or clinical_note.plan:
        composition["content"].append({
            "_type": "EVALUATION",
            "name": {"value": "Clinical Assessment"},
            "archetype_node_id": "openEHR-EHR-EVALUATION.clinical_synopsis.v1",
            "data": {
                "_type": "ITEM_TREE",
                "archetype_node_id": "at0001",
                "items": [
                    {
                        "_type": "ELEMENT",
                        "name": {"value": "Assessment"},
                        "archetype_node_id": "at0002",
                        "value": {
                            "_type": "DV_TEXT",
                            "value": clinical_note.assessment or ""
                        }
                    },
                    {
                        "_type": "ELEMENT",
                        "name": {"value": "Plan"},
                        "archetype_node_id": "at0003",
                        "value": {
                            "_type": "DV_TEXT",
                            "value": clinical_note.plan or ""
                        }
                    }
                ]
            }
        })
    
    return await ehrbase_client.create_composition(ehr_id, composition)