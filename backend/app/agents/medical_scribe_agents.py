"""Medical Scribe Agents using OpenAI Agents SDK with Handoffs"""
import asyncio
import base64
import json
import logging
import tempfile
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from swarm import Agent
from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ==================== AUDIO BUFFER ====================
class AudioBuffer:
    """Manages audio chunks for streaming transcription"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.audio_chunks: List[bytes] = []
        self.total_duration_ms = 0
        self.last_transcription_time = datetime.utcnow()
        
    def add_chunk(self, audio_data: bytes, duration_ms: int):
        """Add audio chunk to buffer"""
        self.audio_chunks.append(audio_data)
        self.total_duration_ms += duration_ms
        
    def should_transcribe(self) -> bool:
        """Check if we should transcribe"""
        # Transcribe if we have 5+ seconds of audio
        if self.total_duration_ms >= 5000:
            return True
        # Or if it's been too long since last transcription
        time_since_last = (datetime.utcnow() - self.last_transcription_time).total_seconds()
        return time_since_last > 10 and self.total_duration_ms > 0
        
    def get_audio_and_clear(self) -> Tuple[bytes, int]:
        """Get combined audio and clear buffer"""
        if not self.audio_chunks:
            return b'', 0
        combined = b''.join(self.audio_chunks)
        duration = self.total_duration_ms
        self.audio_chunks = []
        self.total_duration_ms = 0
        self.last_transcription_time = datetime.utcnow()
        return combined, duration


# ==================== SESSION MANAGEMENT ====================
# Global state for sessions (in production, use Redis)
audio_sessions: Dict[str, Dict[str, Any]] = {}
_handoff_context: Dict[str, Any] = {}


# ==================== TRANSCRIPTION AGENT ====================
def start_transcription_session(session_id: str, encounter_id: str) -> str:
    """Start a new transcription session"""
    audio_sessions[session_id] = {
        "encounter_id": encounter_id,
        "buffer": AudioBuffer(),
        "transcript": "",
        "start_time": datetime.utcnow(),
        "segment_count": 0
    }
    
    return f"Started transcription session {session_id} for encounter {encounter_id}"


def process_audio_chunk(session_id: str, audio_data: str, duration_ms: int) -> str:
    """Process an audio chunk"""
    if session_id not in audio_sessions:
        return "Error: Session not found"
    
    session = audio_sessions[session_id]
    buffer = session["buffer"]
    
    # Decode base64 audio
    try:
        audio_bytes = base64.b64decode(audio_data)
        buffer.add_chunk(audio_bytes, duration_ms)
    except Exception as e:
        return f"Error decoding audio: {str(e)}"
    
    # Check if we should transcribe
    if buffer.should_transcribe():
        audio_to_transcribe, audio_duration = buffer.get_audio_and_clear()
        
        # Create temporary WAV file for Whisper
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            # In production, properly format as WAV
            # For now, just write raw audio
            tmp_file.write(audio_to_transcribe)
            tmp_path = tmp_file.name
            
        try:
            # Transcribe with Whisper (using sync client for Swarm compatibility)
            with open(tmp_path, 'rb') as audio_file:
                # Use previous transcript as prompt for context
                prompt = f"Medical consultation. Previous: {session['transcript'][-200:]}" if session['transcript'] else "Medical consultation transcript."
                
                response = sync_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    prompt=prompt
                )
                
            # Update session
            new_text = response.text.strip()
            if new_text:
                if session["transcript"]:
                    session["transcript"] += " "
                session["transcript"] += new_text
                session["segment_count"] += 1
                
            return f"Transcribed segment {session['segment_count']}: {new_text[:100]}..."
            
        except Exception as e:
            return f"Transcription error: {str(e)}"
        finally:
            os.unlink(tmp_path)
            
    return f"Audio chunk buffered. Buffer duration: {buffer.total_duration_ms}ms"


def end_transcription_session(session_id: str) -> Agent:
    """End a transcription session and hand off to clinical analysis"""
    if session_id not in audio_sessions:
        return "Error: Session not found"
    
    session = audio_sessions[session_id]
    
    # Process any remaining audio
    buffer = session["buffer"]
    if buffer.total_duration_ms > 0:
        # Force transcription of remaining audio
        audio_to_transcribe, _ = buffer.get_audio_and_clear()
        # Process it (simplified for brevity)
        
    # Store context in global state for the next agent
    # In production, use proper context passing mechanism
    global _handoff_context
    _handoff_context = {
        "encounter_id": session["encounter_id"],
        "transcript": session["transcript"],
        "duration_seconds": (datetime.utcnow() - session["start_time"]).total_seconds(),
        "segment_count": session["segment_count"],
        "session_id": session_id
    }
    
    # Clean up session
    del audio_sessions[session_id]
    
    # Return the next agent to hand off to
    return clinical_analysis_agent


# Create transcription agent
transcription_agent = Agent(
    name="TranscriptionAgent",
    instructions="""You are a medical transcription specialist. Your responsibilities:
    1. Manage audio streaming sessions
    2. Buffer audio chunks appropriately
    3. Transcribe using Whisper API when buffer is ready
    4. Maintain transcription context across segments
    5. Hand off complete transcripts to clinical analysis
    
    Available functions:
    - start_transcription_session(session_id, encounter_id)
    - process_audio_chunk(session_id, audio_data, duration_ms)
    - end_transcription_session(session_id)
    """,
    functions=[
        start_transcription_session,
        process_audio_chunk,
        end_transcription_session
    ]
)


# ==================== CLINICAL ANALYSIS AGENT ====================
def analyze_transcript(transcript: str = None, encounter_id: str = None) -> Agent:
    """Analyze transcript for clinical content"""
    
    # Get context from handoff if not provided
    global _handoff_context
    if transcript is None and _handoff_context:
        transcript = _handoff_context.get("transcript")
        encounter_id = _handoff_context.get("encounter_id")
    
    if not transcript:
        return "Error: No transcript provided"
    
    system_prompt = """Extract medical information and categorize into these sections:
    - Chief Complaint: Main reason for visit
    - History of Present Illness: Symptom details, onset, severity
    - Medications: Current medications with doses
    - Vital Signs: BP, HR, Temp, etc.
    - Physical Examination: Exam findings
    - Assessment: Clinical impressions
    - Plan: Treatment plan and follow-up
    
    Also extract:
    - Medical entities (symptoms, diagnoses, medications)
    - Abnormal findings that need attention
    
    Return as structured JSON."""
    
    response = sync_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt + "\n\nRespond with valid JSON only."},
            {"role": "user", "content": f"Analyze this medical transcript:\n\n{transcript}"}
        ],
        temperature=0.3
    )
    
    analysis = json.loads(response.choices[0].message.content)
    
    # Update handoff context
    _handoff_context.update({
        "encounter_id": encounter_id,
        "transcript": transcript,
        "clinical_sections": analysis,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Return the next agent
    return note_structuring_agent


# Create clinical analysis agent
clinical_analysis_agent = Agent(
    name="ClinicalAnalysisAgent",
    instructions="""You are a clinical analysis specialist. Your responsibilities:
    1. Analyze transcribed medical conversations
    2. Extract medical entities (symptoms, medications, diagnoses)
    3. Identify vital signs and measurements
    4. Categorize information by clinical sections
    5. Hand off structured data to note formatting
    
    Available function:
    - analyze_transcript(transcript, encounter_id)
    """,
    functions=[analyze_transcript]
)


# ==================== NOTE STRUCTURING AGENT ====================
def format_clinical_note(clinical_sections: str = None, format_type: str = "soap") -> str:
    """Format clinical sections into a structured note"""
    
    # Get from handoff context if not provided
    global _handoff_context
    if clinical_sections is None and _handoff_context:
        clinical_sections = _handoff_context.get("clinical_sections")
    
    # Parse the clinical sections
    try:
        if isinstance(clinical_sections, dict):
            sections = clinical_sections
        elif isinstance(clinical_sections, str):
            sections = json.loads(clinical_sections)
        else:
            return "Error: No clinical sections provided"
    except:
        return "Error parsing clinical sections"
    
    if format_type == "soap":
        note_parts = []
        
        # Subjective
        subjective_content = []
        if sections.get("chief_complaint"):
            subjective_content.append(f"Chief Complaint: {sections['chief_complaint']}")
        if sections.get("history_of_present_illness"):
            subjective_content.append(f"HPI: {sections['history_of_present_illness']}")
            
        if subjective_content:
            note_parts.append("SUBJECTIVE:\n" + "\n".join(subjective_content))
            
        # Objective
        objective_content = []
        if sections.get("vital_signs"):
            objective_content.append(f"Vital Signs: {sections['vital_signs']}")
        if sections.get("physical_examination"):
            objective_content.append(f"Physical Exam: {sections['physical_examination']}")
            
        if objective_content:
            note_parts.append("OBJECTIVE:\n" + "\n".join(objective_content))
            
        # Assessment
        if sections.get("assessment"):
            note_parts.append(f"ASSESSMENT:\n{sections['assessment']}")
            
        # Plan
        if sections.get("plan"):
            note_parts.append(f"PLAN:\n{sections['plan']}")
            
        return "\n\n".join(note_parts)
        
    elif format_type == "bullet":
        # Bullet point format
        lines = ["CLINICAL NOTE:"]
        for section, content in sections.items():
            if content:
                section_name = section.replace("_", " ").title()
                lines.append(f"• {section_name}: {content}")
        return "\n".join(lines)
        
    else:
        # Default narrative format
        return json.dumps(sections, indent=2)


# Create note structuring agent
note_structuring_agent = Agent(
    name="NoteStructuringAgent",
    instructions="""You are a clinical note formatting specialist. Your responsibilities:
    1. Take analyzed clinical data and format into proper clinical notes
    2. Support different note formats (SOAP, narrative, bullet points)
    3. Ensure medical documentation standards
    4. Organize information logically by section
    5. Return the final formatted note
    
    Available function:
    - format_clinical_note(clinical_sections, format_type)
    """,
    functions=[format_clinical_note]
)


# ==================== QUALITY ASSURANCE AGENT ====================
def check_note_quality(clinical_note: str) -> str:
    """Check the quality and completeness of a clinical note"""
    
    # Simple quality checks
    required_sections = ["chief complaint", "assessment", "plan"]
    missing_sections = []
    
    note_lower = clinical_note.lower()
    for section in required_sections:
        if section not in note_lower:
            missing_sections.append(section)
            
    quality_report = {
        "complete": len(missing_sections) == 0,
        "missing_sections": missing_sections,
        "word_count": len(clinical_note.split()),
        "has_medications": "medication" in note_lower or "mg" in note_lower,
        "has_vital_signs": any(term in note_lower for term in ["bp", "blood pressure", "heart rate", "temperature"]),
        "quality_score": 1.0 - (len(missing_sections) / len(required_sections))
    }
    
    return f"Quality check complete. Score: {quality_report['quality_score']:.2f}. Report: {json.dumps(quality_report, indent=2)}"


# Create quality assurance agent
quality_assurance_agent = Agent(
    name="QualityAssuranceAgent",
    instructions="""You are a clinical documentation quality specialist. Your responsibilities:
    1. Check clinical notes for completeness
    2. Identify missing required sections
    3. Validate medical information accuracy
    4. Ensure documentation standards are met
    5. Provide quality scores and recommendations
    
    Available function:
    - check_note_quality(clinical_note)
    """,
    functions=[check_note_quality]
)


# ==================== SUPERVISOR AGENT ====================
supervisor_agent = Agent(
    name="MedicalScribeSupervisor",
    instructions="""You are the medical scribe supervisor orchestrating the documentation process.
    
    Your workflow:
    1. Start with the TranscriptionAgent for audio processing
    2. Hand off to ClinicalAnalysisAgent for medical content extraction
    3. Hand off to NoteStructuringAgent for formatting
    4. Optionally use QualityAssuranceAgent to check the final note
    
    Guide the conversation and ensure smooth handoffs between agents.
    """
)


# Export all agents
__all__ = [
    'transcription_agent',
    'clinical_analysis_agent',
    'note_structuring_agent',
    'quality_assurance_agent',
    'supervisor_agent',
    'start_transcription_session',
    'process_audio_chunk',
    'end_transcription_session'
]