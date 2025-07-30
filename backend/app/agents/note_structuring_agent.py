"""Note Structuring Agent for formatting clinical notes"""
import logging
from typing import Dict, Any
from datetime import datetime
from swarm import Agent

from app.core.config import settings
from app.core.sse_manager import sse_manager
from app.agents.context_manager import handoff_context

logger = logging.getLogger(__name__)


def format_soap_note(session_id: str) -> str:
    """Format clinical data as SOAP note"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    
    subjective_parts = []
    
    # Chief Complaint
    if clinical_data.get("chief_complaint"):
        subjective_parts.append(f"CHIEF COMPLAINT: {clinical_data['chief_complaint']}")
    
    # HPI
    if clinical_data.get("history_present_illness"):
        subjective_parts.append(f"HISTORY OF PRESENT ILLNESS: {clinical_data['history_present_illness']}")
    
    # ROS
    if clinical_data.get("review_of_systems"):
        ros = clinical_data["review_of_systems"]
        if isinstance(ros, dict):
            ros_text = "\n".join([f"  - {system}: {finding}" for system, finding in ros.items()])
            subjective_parts.append(f"REVIEW OF SYSTEMS:\n{ros_text}")
    
    # Past Medical History
    if clinical_data.get("past_medical_history"):
        subjective_parts.append(f"PAST MEDICAL HISTORY: {clinical_data['past_medical_history']}")
    
    subjective = "\n\n".join(subjective_parts) if subjective_parts else "No subjective data documented."
    
    # Objective
    objective_parts = []
    
    # Vital Signs
    if clinical_data.get("vital_signs"):
        vitals = clinical_data["vital_signs"]
        if isinstance(vitals, dict):
            vitals_text = ", ".join([f"{k}: {v}" for k, v in vitals.items()])
            objective_parts.append(f"VITAL SIGNS: {vitals_text}")
    
    # Physical Exam
    if clinical_data.get("physical_examination"):
        exam = clinical_data["physical_examination"]
        if isinstance(exam, dict):
            exam_text = "\n".join([f"  {system}: {finding}" for system, finding in exam.items()])
            objective_parts.append(f"PHYSICAL EXAMINATION:\n{exam_text}")
        else:
            objective_parts.append(f"PHYSICAL EXAMINATION: {exam}")
    
    objective = "\n\n".join(objective_parts) if objective_parts else "No objective data documented."
    
    # Assessment
    assessment = clinical_data.get("assessment", "No assessment documented.")
    
    # Plan
    plan = clinical_data.get("plan", "No plan documented.")
    
    # Create SOAP note
    soap_note = {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan
    }
    
    handoff_context.update_context(session_id, {
        "soap_note": soap_note,
        "formatted_note_type": "soap"
    })
    
    return "SOAP note formatted successfully"


def format_bullet_note(session_id: str) -> str:
    """Format clinical data as bullet points"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    encounter_date = handoff_context.get_from_context(session_id, "encounter_date", datetime.now())
    
    lines = [
        "CLINICAL ENCOUNTER NOTE",
        f"Date: {encounter_date}",
        "",
        "CLINICAL FINDINGS:"
    ]
    
    # Add each section as bullet points
    sections_order = [
        ("chief_complaint", "Chief Complaint"),
        ("history_present_illness", "HPI"),
        ("review_of_systems", "Review of Systems"),
        ("past_medical_history", "Past Medical History"),
        ("medications", "Current Medications"),
        ("allergies", "Allergies"),
        ("vital_signs", "Vital Signs"),
        ("physical_examination", "Physical Exam"),
        ("assessment", "Assessment"),
        ("plan", "Plan")
    ]
    
    for key, title in sections_order:
        if clinical_data.get(key):
            lines.append(f"\n• {title}:")
            content = clinical_data[key]
            
            if isinstance(content, dict):
                for sub_key, sub_value in content.items():
                    lines.append(f"  - {sub_key}: {sub_value}")
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        lines.append(f"  - {item.get('name', item)}")
                    else:
                        lines.append(f"  - {item}")
            else:
                lines.append(f"  {content}")
    
    bullet_note = "\n".join(lines)
    
    handoff_context.update_context(session_id, {
        "bullet_note": bullet_note,
        "formatted_note_type": "bullet"
    })
    
    return "Bullet point note formatted successfully"


def structure_clinical_note(session_id: str) -> Agent:
    """Structure the clinical note based on format preference and hand off to QA"""
    try:
        format_preference = handoff_context.get_from_context(session_id, "format_preference", "soap")
        
        logger.info(f"Structuring clinical note for session {session_id} in {format_preference} format")
        
        # Format based on preference
        if format_preference == "soap":
            result = format_soap_note(session_id)
        elif format_preference == "bullet":
            result = format_bullet_note(session_id)
        else:
            # Default to SOAP
            result = format_soap_note(session_id)
            format_preference = "soap"
        
        # Get the formatted note
        if format_preference == "soap":
            formatted_note = handoff_context.get_from_context(session_id, "soap_note", {})
        else:
            formatted_note = handoff_context.get_from_context(session_id, "bullet_note", "")
        
        # Update context with final note
        handoff_context.update_context(session_id, {
            "final_note": formatted_note,
            "structuring_status": "completed"
        })
        
        # Send SSE update
        transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
        if transcription_id:
            asyncio.create_task(
                sse_manager.publish(
                    f"transcription:{transcription_id}",
                    "note_structured",
                    {
                        "format": format_preference,
                        "note": formatted_note
                    }
                )
            )
        
        logger.info(f"Completed note structuring for session {session_id}")
        
        # Hand off to quality assurance
        return quality_assurance_agent
        
    except Exception as e:
        logger.error(f"Error in note structuring: {str(e)}")
        handoff_context.update_context(session_id, {
            "structuring_status": "failed",
            "structuring_error": str(e)
        })
        raise


def add_medical_codes(session_id: str) -> str:
    """Add relevant medical codes (ICD-10, CPT) to the note"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    
    # Simple mapping - in production, use proper medical coding API
    icd_codes = []
    
    assessment = clinical_data.get("assessment", "").lower()
    if "hypertension" in assessment:
        icd_codes.append("I10 - Essential (primary) hypertension")
    if "diabetes" in assessment:
        icd_codes.append("E11.9 - Type 2 diabetes mellitus without complications")
    if "chest pain" in clinical_data.get("chief_complaint", "").lower():
        icd_codes.append("R07.9 - Chest pain, unspecified")
    
    handoff_context.update_context(session_id, {
        "medical_codes": {
            "icd10": icd_codes,
            "cpt": []  # Would add procedure codes here
        }
    })
    
    return f"Added {len(icd_codes)} ICD-10 codes"


# Create the note structuring agent
note_structuring_agent = Agent(
    name="NoteStructuringAgent",
    instructions="""You are a clinical note formatting specialist.
    
Your responsibilities:
1. Format clinical data into standard note formats (SOAP, bullet points)
2. Ensure proper medical documentation structure
3. Maintain clinical accuracy while improving readability
4. Add relevant medical codes when applicable
5. Send formatted note via SSE
6. Hand off to quality assurance for validation

Available functions:
- format_soap_note(session_id) - Format as SOAP note
- format_bullet_note(session_id) - Format as bullet points
- structure_clinical_note(session_id) - Main structuring function, returns next agent
- add_medical_codes(session_id) - Add ICD-10/CPT codes

Ensure professional medical documentation standards.
""",
    functions=[
        format_soap_note,
        format_bullet_note,
        structure_clinical_note,
        add_medical_codes
    ]
)


# Import at the bottom to avoid circular import
import asyncio
from app.agents.quality_assurance_agent import quality_assurance_agent