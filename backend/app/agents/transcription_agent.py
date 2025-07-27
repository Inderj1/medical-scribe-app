"""Medical Transcription Agent using OpenAI Agents SDK and Realtime API"""
import asyncio
import json
import logging
import websockets
from typing import Optional, Dict, Any, List
from datetime import datetime
import base64

from agents import Agent, function_tool, Handoff
from openai import AsyncOpenAI
from app.core.config import settings
from app.agents.transcription_models import (
    SessionStatus, AudioProcessingResult, SessionEndResult,
    MedicalEntity, ClinicalAnalysis
)

logger = logging.getLogger(__name__)


class RealtimeWebSocketClient:
    """WebSocket client for OpenAI Realtime API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.api_url = "wss://api.openai.com/v1/realtime"
        self.model = "gpt-4o-realtime-preview"
        self.is_connected = False
        self.transcription_callback = None
        
    async def connect(self):
        """Connect to OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.ws = await websockets.connect(
            self.api_url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=10
        )
        self.is_connected = True
        
        # Configure session
        await self._configure_session()
        
        # Start listening
        asyncio.create_task(self._listen())
        
    async def _configure_session(self):
        """Configure realtime session for medical transcription"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "model": self.model,
                "instructions": """You are a medical transcription assistant. 
                Transcribe medical consultations accurately, paying attention to:
                - Medical terminology and drug names
                - Symptoms and diagnoses
                - Dosages and measurements
                - Patient complaints and doctor assessments""",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "enabled": True,
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200  # Reduced for real-time
                },
                "temperature": 0.3
            }
        }
        await self.ws.send(json.dumps(config))
        
    async def _listen(self):
        """Listen for transcription results"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except Exception as e:
            logger.error(f"Realtime API error: {e}")
            self.is_connected = False
            
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle messages from Realtime API"""
        msg_type = data.get("type")
        
        if msg_type == "response.audio_transcript.delta":
            # Partial transcription
            text = data.get("delta", {}).get("audio_transcript", "")
            if text and self.transcription_callback:
                await self.transcription_callback(text, is_partial=True)
                
        elif msg_type == "response.audio_transcript.done":
            # Complete transcription
            text = data.get("audio_transcript", "")
            if text and self.transcription_callback:
                await self.transcription_callback(text, is_partial=False)
                
    async def send_audio(self, audio_data: bytes):
        """Send audio to Realtime API"""
        if self.is_connected:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await self.ws.send(json.dumps(message))
            
    async def disconnect(self):
        """Disconnect from Realtime API"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False


# Create the transcription agent
transcription_agent = Agent(
    name="TranscriptionAgent",
    instructions="""You are a medical transcription specialist. Your role is to:
    1. Manage real-time audio transcription using OpenAI's Realtime API
    2. Process continuous audio streams without buffering
    3. Extract medical terminology accurately
    4. Identify when to hand off to clinical analysis
    """
)

# Global WebSocket client instance
realtime_client = None


@function_tool
async def start_transcription_session(encounter_id: str, patient_id: str) -> SessionStatus:
    """Start a new transcription session"""
    global realtime_client
    
    if not realtime_client:
        realtime_client = RealtimeWebSocketClient(settings.OPENAI_API_KEY)
        
    if not realtime_client.is_connected:
        await realtime_client.connect()
        
    return SessionStatus(
        status="connected",
        encounter_id=encounter_id,
        patient_id=patient_id,
        session_started=datetime.utcnow().isoformat()
    )


@function_tool
async def process_audio_stream(audio_data: str) -> AudioProcessingResult:
    """Process incoming audio stream data (base64 encoded)"""
    global realtime_client
    
    if not realtime_client or not realtime_client.is_connected:
        return AudioProcessingResult(error="Not connected to transcription service", status="error", bytes=0)
        
    # Decode and send audio
    try:
        audio_bytes = base64.b64decode(audio_data)
        await realtime_client.send_audio(audio_bytes)
        return AudioProcessingResult(status="audio_processed", bytes=len(audio_bytes))
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        return AudioProcessingResult(error=str(e), status="error", bytes=0)


@function_tool
async def end_transcription_session() -> SessionEndResult:
    """End the current transcription session"""
    global realtime_client
    
    if realtime_client:
        await realtime_client.disconnect()
        realtime_client = None
        
    return SessionEndResult(status="disconnected", session_ended=datetime.utcnow().isoformat())


# We'll define the handoff function later

# Add tools to agent
transcription_agent.tools = [
    start_transcription_session,
    process_audio_stream,
    end_transcription_session
]


# Create the clinical analysis agent
clinical_analysis_agent = Agent(
    name="ClinicalAnalysisAgent",
    instructions="""You are a clinical analysis specialist. Your role is to:
    1. Analyze transcribed medical conversations
    2. Extract medical entities (symptoms, medications, diagnoses)
    3. Identify which section of the clinical note each piece of information belongs to
    4. Structure information for the note formatting agent
    
    Focus on accuracy and medical terminology. Categorize information into:
    - Chief Complaint
    - History of Present Illness
    - Medications
    - Vital Signs
    - Physical Exam
    - Assessment & Plan
    """
)


@function_tool
async def analyze_transcription(text: str) -> ClinicalAnalysis:
    """Analyze transcribed text for medical content"""
    
    # Use OpenAI to analyze the text
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    system_prompt = """Extract medical information from this transcription and categorize it:
    - Chief Complaint: Main reason for visit
    - Symptoms: Include onset, severity, location
    - Medications: Name, dose, frequency
    - Vital Signs: BP, HR, Temp, etc.
    - Physical Exam: Findings
    - Assessment: Diagnoses or impressions
    - Plan: Treatment plans, follow-up
    
    Return as structured JSON."""
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcription: {text}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    analysis = json.loads(response.choices[0].message.content)
    
    return ClinicalAnalysis(
        text=text,
        chief_complaint=analysis.get("chief_complaint"),
        symptoms=analysis.get("symptoms"),
        medications=analysis.get("medications"),
        vital_signs=analysis.get("vital_signs"),
        physical_exam=analysis.get("physical_exam"),
        assessment=analysis.get("assessment"),
        plan=analysis.get("plan"),
        timestamp=datetime.utcnow().isoformat()
    )


@function_tool
async def extract_medical_entities(text: str) -> List[MedicalEntity]:
    """Extract specific medical entities from text"""
    entities = []
    
    # Simple pattern matching for common medical terms
    # In production, use a medical NER model
    import re
    
    # Medication patterns
    med_pattern = r'\b(\w+)\s+(\d+)\s*(mg|mcg|ml|units?)\b'
    for match in re.finditer(med_pattern, text, re.IGNORECASE):
        entities.append(MedicalEntity(
            type="medication",
            name=match.group(1),
            dose=match.group(2),
            unit=match.group(3)
        ))
        
    # Vital signs patterns
    bp_pattern = r'\b(\d{2,3})/(\d{2,3})\b'
    for match in re.finditer(bp_pattern, text):
        entities.append(MedicalEntity(
            type="vital_sign",
            name="blood_pressure",
            systolic=match.group(1),
            diastolic=match.group(2)
        ))
        
    return entities


# Add tools to clinical analysis agent
clinical_analysis_agent.tools = [
    analyze_transcription,
    extract_medical_entities
]


# Create the note formatting agent
note_formatting_agent = Agent(
    name="NoteFormattingAgent",
    instructions="""You are a clinical note formatting specialist. Your role is to:
    1. Take analyzed clinical data and format it into proper clinical notes
    2. Support different note formats (SOAP, narrative, bullet points)
    3. Ensure proper medical documentation standards
    4. Organize information logically by section
    """
)


@function_tool
async def format_clinical_note(
    analysis: dict,
    format_type: str = "soap"
) -> str:
    """Format analyzed data into a clinical note"""
    
    if format_type == "soap":
        note_parts = []
        
        # Subjective
        if analysis.get("chief_complaint") or analysis.get("symptoms"):
            note_parts.append("**SUBJECTIVE:**")
            if analysis.get("chief_complaint"):
                note_parts.append(f"Chief Complaint: {analysis['chief_complaint']}")
            if analysis.get("symptoms"):
                note_parts.append(f"Symptoms: {', '.join(analysis['symptoms'])}")
                
        # Objective
        if analysis.get("vital_signs") or analysis.get("physical_exam"):
            note_parts.append("\n**OBJECTIVE:**")
            if analysis.get("vital_signs"):
                note_parts.append(f"Vital Signs: {analysis['vital_signs']}")
            if analysis.get("physical_exam"):
                note_parts.append(f"Physical Exam: {analysis['physical_exam']}")
                
        # Assessment
        if analysis.get("assessment"):
            note_parts.append(f"\n**ASSESSMENT:**\n{analysis['assessment']}")
            
        # Plan
        if analysis.get("plan"):
            note_parts.append(f"\n**PLAN:**\n{analysis['plan']}")
            
        return "\n".join(note_parts)
        
    elif format_type == "bullet":
        # Bullet format implementation
        note_parts = ["**Clinical Note:**"]
        for key, value in analysis.items():
            if value:
                note_parts.append(f"• {key.replace('_', ' ').title()}: {value}")
        return "\n".join(note_parts)
        
    else:
        # Default narrative format
        return json.dumps(analysis, indent=2)


note_formatting_agent.tools = [format_clinical_note]


# Export agents
__all__ = [
    'transcription_agent',
    'clinical_analysis_agent', 
    'note_formatting_agent'
]