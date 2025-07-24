from openai import OpenAI
from typing import Optional, Dict, Any
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
import io

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str = "en"
    duration: Optional[float] = None
    timestamp: Optional[datetime] = None


class TranscriptionService:
    def __init__(self):
        self.model = settings.WHISPER_MODEL
        self.audio_processor = None
        
    async def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            # Log audio data info
            logger.info(f"Transcribing audio: size={len(audio_data)} bytes")
            
            # Check minimum audio size (at least 1KB)
            if len(audio_data) < 1024:
                logger.warning(f"Audio data too small: {len(audio_data)} bytes")
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    timestamp=datetime.utcnow()
                )
            
            # Process audio for Whisper
            from app.services.audio_processor import AudioProcessor
            processor = AudioProcessor(None)
            audio_file = processor.process_audio_for_whisper(audio_data)
            
            # Call Whisper API
            response = await self._call_whisper_api(audio_file)
            
            # Extract transcription
            text = response.get("text", "")
            logger.info(f"Transcription result: '{text[:100]}...' (length: {len(text)})")
            
            # Calculate confidence (Whisper doesn't provide confidence scores directly)
            # We'll use text length and word count as a proxy
            word_count = len(text.split())
            confidence = min(0.95, 0.7 + (word_count * 0.01))
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=response.get("language", "en"),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Transcription error: {type(e).__name__}: {str(e)}")
            logger.error(f"Stack trace:", exc_info=True)
            return TranscriptionResult(
                text="",
                confidence=0.0,
                timestamp=datetime.utcnow()
            )
            
    async def _call_whisper_api(self, audio_file) -> Dict[str, Any]:
        """Call OpenAI Whisper API"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Convert audio_file to proper format if needed
            if isinstance(audio_file, bytes):
                audio_buffer = io.BytesIO(audio_file)
                audio_buffer.name = "audio.webm"  # Whisper needs a filename
            else:
                audio_buffer = audio_file
            
            # Log API call details
            logger.info(f"Calling Whisper API with model: {self.model}")
            logger.debug(f"Audio buffer size: {audio_buffer.getbuffer().nbytes if hasattr(audio_buffer, 'getbuffer') else 'unknown'}")
            
            response = await loop.run_in_executor(
                None,
                lambda: client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_buffer,
                    response_format="json",
                    language="en",
                    prompt="This is a medical consultation. Listen for medical terms, symptoms, diagnoses, and treatments."
                )
            )
            
            # Log successful response
            logger.info(f"Whisper API success: got transcription of length {len(response.text)}")
            
            # Convert response to dict format
            return {"text": response.text, "language": "en"}
            
        except Exception as e:
            logger.error(f"Whisper API error: {type(e).__name__}: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"API Response: {getattr(e.response, 'text', 'No response text')}")
            logger.error(f"Stack trace:", exc_info=True)
            raise
            
    async def transcribe_with_speaker_diarization(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe with speaker identification (future enhancement)"""
        # For now, return standard transcription
        # In future, integrate with speaker diarization service
        result = await self.transcribe(audio_data)
        
        return {
            "transcription": result,
            "speakers": [
                {
                    "id": "doctor",
                    "segments": [{"text": result.text, "start": 0, "end": None}]
                }
            ]
        }
        
    async def get_medical_context_prompt(self, encounter_type: str) -> str:
        """Get specialized prompt based on encounter type"""
        prompts = {
            "new_patient": "New patient consultation. Listen for chief complaint, medical history, current medications, allergies, and review of systems.",
            "follow_up": "Follow-up visit. Listen for progress updates, symptom changes, medication adherence, and treatment response.",
            "urgent": "Urgent care visit. Focus on acute symptoms, onset, severity, associated symptoms, and vital signs.",
            "specialty": "Specialty consultation. Listen for detailed examination findings, diagnostic results, and treatment recommendations."
        }
        
        return prompts.get(encounter_type, prompts["new_patient"])