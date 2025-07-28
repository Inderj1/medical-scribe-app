"""Medical Scribe Agents using OpenAI Agents SDK"""
import asyncio
import base64
import json
import logging
import tempfile
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from swarm import Agent, Handoff
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


# Audio buffer for streaming
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


# Global state for sessions (in production, use Redis or similar)
audio_sessions: Dict[str, Dict[str, Any]] = {}


# Create the transcription agent
transcription_agent = Agent(
    name="TranscriptionAgent",
    instructions="""You are a medical transcription specialist. Your role is to:
    1. Manage audio streaming sessions
    2. Buffer audio chunks appropriately
    3. Transcribe using Whisper API when buffer is ready
    4. Maintain transcription context across segments
    5. Hand off complete transcripts to clinical analysis
    """
)


async def start_transcription_session(session_id: str, encounter_id: str) -> Dict[str, Any]:
    """Start a new transcription session"""
    audio_sessions[session_id] = {
        "encounter_id": encounter_id,
        "buffer": AudioBuffer(),
        "transcript": "",
        "start_time": datetime.utcnow(),
        "segment_count": 0
    }
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Transcription session started"
    }


async def process_audio_chunk(session_id: str, audio_data: str, duration_ms: int) -> Dict[str, Any]:
    """Process an audio chunk"""
    if session_id not in audio_sessions:
        return {"status": "error", "message": "Session not found"}
    
    session = audio_sessions[session_id]
    buffer = session["buffer"]
    
    # Decode base64 audio
    audio_bytes = base64.b64decode(audio_data)
    buffer.add_chunk(audio_bytes, duration_ms)
    
    # Check if we should transcribe
    if buffer.should_transcribe():
        audio_to_transcribe, audio_duration = buffer.get_audio_and_clear()
        
        # Create temporary WAV file for Whisper
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            # In production, properly format as WAV
            tmp_file.write(audio_to_transcribe)
            tmp_path = tmp_file.name
            
        try:
            # Transcribe with Whisper
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            with open(tmp_path, 'rb') as audio_file:
                # Use previous transcript as prompt for context
                prompt = f"Medical consultation. Previous: {session['transcript'][-200:]}" if session['transcript'] else "Medical consultation transcript."
                
                response = await client.audio.transcriptions.create(
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
                
            return {
                "status": "success",
                "segment": new_text,
                "total_segments": session["segment_count"],
                "transcript_length": len(session["transcript"])
            }
            
        finally:
            os.unlink(tmp_path)
            
    return {
        "status": "success",
        "message": "Audio chunk buffered",
        "buffer_duration_ms": buffer.total_duration_ms
    }


async def end_transcription_session(session_id: str) -> Dict[str, Any]:
    """End a transcription session and hand off to clinical analysis"""
    if session_id not in audio_sessions:
        return {"status": "error", "message": "Session not found"}
    
    session = audio_sessions[session_id]
    
    # Process any remaining audio
    buffer = session["buffer"]
    if buffer.total_duration_ms > 0:
        # Process final chunk
        await process_audio_chunk(session_id, "", 0)  # Force transcription
        
    # Prepare handoff data
    handoff_data = {
        "encounter_id": session["encounter_id"],
        "transcript": session["transcript"],
        "duration_seconds": (datetime.utcnow() - session["start_time"]).total_seconds(),
        "segment_count": session["segment_count"]
    }
    
    # Clean up session
    del audio_sessions[session_id]
    
    # Hand off to clinical analysis
    return Handoff(
        agent=clinical_analysis_agent,
        metadata=handoff_data
    )


# Add functions to transcription agent
transcription_agent.functions = [
    start_transcription_session,
    process_audio_chunk,
    end_transcription_session
]


# Create the clinical analysis agent
clinical_analysis_agent = Agent(
    name="ClinicalAnalysisAgent",
    instructions="""You are a clinical analysis specialist. Your role is to:
    1. Analyze transcribed medical conversations
    2. Extract medical entities (symptoms, medications, diagnoses)
    3. Identify vital signs and measurements
    4. Categorize information by clinical sections
    5. Hand off structured data to note formatting
    """
)


async def analyze_transcript(transcript: str, encounter_id: str) -> Dict[str, Any]:
    """Analyze transcript for clinical content"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
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
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this medical transcript:\n\n{transcript}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    analysis = json.loads(response.choices[0].message.content)
    
    # Prepare handoff to note structuring
    handoff_data = {
        "encounter_id": encounter_id,
        "transcript": transcript,
        "clinical_sections": analysis,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return Handoff(
        agent=note_structuring_agent,
        metadata=handoff_data
    )


# Add function to clinical analysis agent
clinical_analysis_agent.functions = [analyze_transcript]


# Create the note structuring agent
note_structuring_agent = Agent(
    name="NoteStructuringAgent",
    instructions="""You are a clinical note formatting specialist. Your role is to:
    1. Take analyzed clinical data and format into proper clinical notes
    2. Support different note formats (SOAP, narrative, bullet points)
    3. Ensure medical documentation standards
    4. Organize information logically by section
    5. Return the final formatted note
    """
)


async def format_clinical_note(
    clinical_sections: Dict[str, Any],
    format_type: str = "soap"
) -> Dict[str, Any]:
    """Format clinical sections into a structured note"""
    
    if format_type == "soap":
        note_parts = []
        
        # Subjective
        subjective_content = []
        if clinical_sections.get("chief_complaint"):
            subjective_content.append(f"Chief Complaint: {clinical_sections['chief_complaint']}")
        if clinical_sections.get("history_of_present_illness"):
            subjective_content.append(f"HPI: {clinical_sections['history_of_present_illness']}")
            
        if subjective_content:
            note_parts.append("SUBJECTIVE:\n" + "\n".join(subjective_content))
            
        # Objective
        objective_content = []
        if clinical_sections.get("vital_signs"):
            objective_content.append(f"Vital Signs: {clinical_sections['vital_signs']}")
        if clinical_sections.get("physical_examination"):
            objective_content.append(f"Physical Exam: {clinical_sections['physical_examination']}")
            
        if objective_content:
            note_parts.append("OBJECTIVE:\n" + "\n".join(objective_content))
            
        # Assessment
        if clinical_sections.get("assessment"):
            note_parts.append(f"ASSESSMENT:\n{clinical_sections['assessment']}")
            
        # Plan
        if clinical_sections.get("plan"):
            note_parts.append(f"PLAN:\n{clinical_sections['plan']}")
            
        formatted_note = "\n\n".join(note_parts)
        
    elif format_type == "bullet":
        # Bullet point format
        lines = []
        for section, content in clinical_sections.items():
            if content:
                section_name = section.replace("_", " ").title()
                lines.append(f"• {section_name}: {content}")
        formatted_note = "\n".join(lines)
        
    else:
        # Default narrative format
        formatted_note = json.dumps(clinical_sections, indent=2)
        
    return {
        "status": "completed",
        "formatted_note": formatted_note,
        "format": format_type,
        "sections": list(clinical_sections.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }


# Add function to note structuring agent
note_structuring_agent.functions = [format_clinical_note]


# Export agents and functions
__all__ = [
    'transcription_agent',
    'clinical_analysis_agent',
    'note_structuring_agent',
    'start_transcription_session',
    'process_audio_chunk',
    'end_transcription_session'
]