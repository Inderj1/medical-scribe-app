"""Clinical Analysis Agent using GPT-4"""
import json
import logging
from typing import Dict, Any
from swarm import Agent
import openai

from app.core.config import settings
from app.agents.context_manager import handoff_context

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def analyze_transcript(session_id: str) -> str:
    """Start analysis of the transcript"""
    transcript = handoff_context.get_from_context(session_id, "transcript", "")
    if not transcript or not transcript.strip():
        logger.warning(f"Empty transcript for clinical analysis in session {session_id}")
        handoff_context.update_context(session_id, {
            "analysis_status": "skipped_empty",
            "clinical_data": {"note": "No speech input was recorded"}
        })
        return "Skipped analysis: No transcript content available"
    
    logger.info(f"Starting clinical analysis for session {session_id}")
    
    # Update status
    handoff_context.update_context(session_id, {
        "analysis_status": "started"
    })
    
    # Store SSE update in context for later publishing
    transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
    if transcription_id:
        handoff_context.update_context(session_id, {
            "pending_sse_event": {
                "type": "analyzing",
                "data": {"message": "Starting clinical analysis..."}
            }
        })
    
    return f"Starting analysis of transcript ({len(transcript)} characters)"


def extract_clinical_sections(session_id: str) -> Agent:
    """Extract clinical information from transcript and hand off to structuring"""
    try:
        transcript = handoff_context.get_from_context(session_id, "transcript", "")
        patient_context = handoff_context.get_from_context(session_id, "patient_context", {})
        speaker_segments = handoff_context.get_from_context(session_id, "speaker_segments", [])
        speaker_roles = handoff_context.get_from_context(session_id, "speaker_roles", {})
        
        # Handle empty transcript
        if not transcript or not transcript.strip():
            logger.warning(f"Empty transcript in extract_clinical_sections for session {session_id}")
            handoff_context.update_context(session_id, {
                "analysis_status": "completed_empty",
                "clinical_data": {"note": "No speech input was recorded"}
            })
            # Still hand off to next agent
            return note_structuring_agent
        ehr_sections = handoff_context.get_from_context(session_id, "ehr_sections", {})
        
        # Prepare speaker context for the prompt
        speaker_context = ""
        if speaker_roles:
            speaker_context = "\n\nSpeaker Information:\n"
            for speaker_id, role in speaker_roles.items():
                speaker_context += f"- {speaker_id}: {role}\n"
        
        system_prompt = f"""You are a medical scribe AI assistant. Extract and structure clinical information from the transcript into these exact JSON keys.
{speaker_context}

{{
  "chief_complaint": "Patient's main concern or reason for visit",
  "history_present_illness": "Detailed history of the present illness",
  "review_of_systems": "Systematic review of symptoms by body system",
  "past_medical_history": "Previous medical conditions, surgeries, hospitalizations",
  "medications": "Current medications with dosages",
  "allergies": "Known allergies and reaction types",
  "social_history": "Social habits, occupation, lifestyle factors",
  "family_history": "Relevant family medical history",
  "physical_examination": "Physical exam findings by system",
  "vital_signs": "Vital signs if mentioned (BP, HR, temp, etc.)",
  "diagnostic_results": "Lab results, imaging, test results",
  "assessment": "Clinical assessment and differential diagnosis",
  "plan": "Treatment plan and follow-up recommendations",
  "additional_notes": "Other relevant information that doesn't fit in standard sections",
  "care_coordination": "Communication with other providers, referrals, care team notes"
}}

For each section:
- Extract relevant information from the transcript
- If a section is not mentioned, set value to null
- For complex sections like review_of_systems or physical_examination, you may use nested objects
- Include confidence scores where appropriate
- Use "additional_notes" for any important information that doesn't clearly fit into other sections
- Use "care_coordination" for discussions about referrals, communication with other providers, or care team notes

IMPORTANT: 
- Use these exact JSON keys
- Build upon and enhance any existing EHR data provided, don't replace it unless the transcript contains updated information
- Don't force content into inappropriate sections - use additional_notes when uncertain
- Preserve ALL clinically relevant information from the transcript"""

        # Build context with EHR data
        existing_data_text = ""
        if ehr_sections:
            logger.info(f"Clinical agent received EHR sections: {list(ehr_sections.keys())}")
            existing_data_text = "\n\nExisting EHR Data (enhance with new information from transcript):\n"
            for section, content in ehr_sections.items():
                if content:
                    logger.info(f"Using EHR data for '{section}': {str(content)[:100]}...")
                    existing_data_text += f"{section.replace('_', ' ').title()}: {content}\n"
        else:
            logger.info("No EHR sections received by clinical agent")

        user_prompt = f"""Patient Context:
Name: {patient_context.get('first_name', '')} {patient_context.get('last_name', '')}
MRN: {patient_context.get('mrn', '')}
Age: {patient_context.get('age', 'Unknown')}
Gender: {patient_context.get('gender', 'Unknown')}
Chief Complaint (if known): {patient_context.get('chief_complaint', 'Not specified')}
Allergies: {patient_context.get('allergies', 'Unknown')}
Smoking History: {patient_context.get('smoking_history', 'Unknown')}
{existing_data_text}

Medical Transcript:
{transcript}

Extract and enhance clinical information according to the sections provided. Incorporate both EHR data and new information from the transcript."""

        # Call GPT-4
        response = client.chat.completions.create(
            model=settings.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        clinical_data = json.loads(response.choices[0].message.content)
        
        # Debug: Log what sections were extracted
        logger.info(f"Extracted clinical sections for session {session_id}: {list(clinical_data.keys())}")
        for key, value in clinical_data.items():
            if value:
                logger.info(f"Section '{key}': {str(value)[:100]}...")
        
        # Store in context
        handoff_context.update_context(session_id, {
            "clinical_data": clinical_data,
            "analysis_status": "completed"
        })
        
        # Send progress updates for key sections that the frontend expects
        sections_to_notify = [
            "chief_complaint", 
            "history_present_illness", 
            "past_medical_history",
            "medications", 
            "allergies", 
            "review_of_systems",
            "physical_examination",
            "assessment", 
            "plan",
            "diagnostic_results",
            "additional_notes",
            "care_coordination"
        ]
        transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
        
        # Store sections for SSE publishing by the streaming endpoint
        sections_for_sse = {}
        for section in sections_to_notify:
            if section in clinical_data and clinical_data[section]:
                sections_for_sse[section] = {
                    "content": str(clinical_data[section])[:500],  # Limit content size
                    "confidence": clinical_data.get(f"{section}_confidence", 0.8)
                }
        
        # Store in context for the streaming endpoint to publish
        handoff_context.update_context(session_id, {
            "sections_for_sse": sections_for_sse
        })
        
        logger.info(f"Prepared {len(sections_for_sse)} sections for SSE publishing: {list(sections_for_sse.keys())}")
        
        logger.info(f"Completed clinical analysis for session {session_id}")
        
        # Hand off to note structuring
        return note_structuring_agent
        
    except Exception as e:
        logger.error(f"Error in clinical analysis: {str(e)}")
        handoff_context.update_context(session_id, {
            "analysis_status": "failed",
            "analysis_error": str(e)
        })
        raise


def identify_medical_entities(session_id: str) -> str:
    """Identify key medical entities from the clinical data"""
    clinical_data = handoff_context.get_from_context(session_id, "clinical_data", {})
    
    entities = {
        "symptoms": [],
        "diagnoses": [],
        "medications": [],
        "procedures": [],
        "lab_values": []
    }
    
    # Extract entities from different sections
    if clinical_data.get("chief_complaint"):
        # Simple extraction - in production, use NER model
        entities["symptoms"].append(clinical_data["chief_complaint"])
    
    if clinical_data.get("medications"):
        entities["medications"] = clinical_data["medications"]
    
    if clinical_data.get("assessment"):
        entities["diagnoses"].append(clinical_data["assessment"])
    
    handoff_context.update_context(session_id, {
        "medical_entities": entities
    })
    
    return f"Identified {sum(len(v) for v in entities.values())} medical entities"


# Create the clinical analysis agent
clinical_analysis_agent = Agent(
    name="ClinicalAnalysisAgent",
    instructions="""You are a clinical analysis specialist using GPT-4.
    
Your responsibilities:
1. Analyze medical transcripts for clinical content
2. Extract information into standard medical sections
3. Identify key medical entities (symptoms, diagnoses, medications)
4. Calculate confidence scores for extracted information
5. Send progress updates for key sections via SSE
6. Hand off structured data to note formatting

Available functions:
- analyze_transcript(session_id) - Start analysis
- extract_clinical_sections(session_id) - Extract and structure, returns next agent
- identify_medical_entities(session_id) - Extract medical entities

Ensure accurate extraction and proper medical terminology.
""",
    functions=[
        analyze_transcript,
        extract_clinical_sections,
        identify_medical_entities
    ]
)


# Import at the bottom to avoid circular import
import asyncio
from app.agents.note_structuring_agent import note_structuring_agent