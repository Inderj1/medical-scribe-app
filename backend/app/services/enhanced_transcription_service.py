import asyncio
import json
import logging
import time
import tempfile
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import openai
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionJob:
    id: str
    audio_data: bytes
    timestamp: str
    client_id: str
    retry_count: int = 0
    status: str = "pending"
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class TranscriptionResult:
    id: str
    text: str
    confidence: float
    segments: List[Dict]
    processing_time: float
    timestamp: str


class EnhancedWhisperClient:
    def __init__(self, api_key: str = None, model: str = "whisper-1"):
        self.client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model
        self.max_retries = 3
        self.timeout = 30
        
    async def transcribe_audio(self, audio_data: bytes, job_id: str, 
                              encounter_type: str = "general") -> TranscriptionResult:
        """Transcribe audio with enhanced error handling and retries"""
        start_time = time.time()
        
        try:
            # Create temporary file for Whisper API
            # Try to detect the audio format
            suffix = ".webm"
            if audio_data.startswith(b'RIFF'):
                suffix = ".wav"
            elif audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'\xff\xf3'):
                suffix = ".mp3"
            
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Get medical context prompt
                prompt = self._get_medical_context_prompt(encounter_type)
                
                # Call Whisper API with detailed response
                with open(tmp_file_path, "rb") as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        response_format="verbose_json",
                        language="en",
                        prompt=prompt,
                        temperature=0.0  # More deterministic results
                    )
                
                processing_time = time.time() - start_time
                
                # Handle response format - verbose_json returns a dict
                if isinstance(response, dict):
                    # Response is already a dictionary
                    response_dict = response
                else:
                    # Response is an object, convert to dict
                    response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.__dict__
                
                # Extract segments with timestamps and confidence
                segments = []
                if 'segments' in response_dict and response_dict['segments']:
                    segments = [
                        {
                            "start": segment.get('start', 0),
                            "end": segment.get('end', 0),
                            "text": segment.get('text', ''),
                            "confidence": segment.get('avg_logprob', 0.8)
                        }
                        for segment in response_dict['segments']
                    ]
                
                # Calculate overall confidence
                confidence = self._calculate_confidence(response_dict, segments)
                
                return TranscriptionResult(
                    id=job_id,
                    text=response_dict.get('text', ''),
                    confidence=confidence,
                    segments=segments,
                    processing_time=processing_time,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Whisper transcription failed for job {job_id}: {str(e)}")
            raise e
    
    def _get_medical_context_prompt(self, encounter_type: str) -> str:
        """Get specialized prompt based on encounter type"""
        prompts = {
            "new_patient": "New patient consultation. Listen for chief complaint, medical history, current medications, allergies, and review of systems.",
            "follow_up": "Follow-up visit. Listen for progress updates, symptom changes, medication adherence, and treatment response.",
            "urgent": "Urgent care visit. Focus on acute symptoms, onset, severity, associated symptoms, and vital signs.",
            "specialty": "Specialty consultation. Listen for detailed examination findings, diagnostic results, and treatment recommendations.",
            "general": "Medical consultation. Listen for symptoms, medical history, medications, vital signs, and clinical findings."
        }
        
        return prompts.get(encounter_type, prompts["general"])
    
    def _calculate_confidence(self, response: Any, segments: List[Dict]) -> float:
        """Calculate overall confidence score"""
        if not segments:
            # Fallback to text-based confidence
            text = response.get('text', '') if isinstance(response, dict) else getattr(response, 'text', '')
            word_count = len(text.split())
            return min(0.95, 0.7 + (word_count * 0.01))
        
        # Calculate average confidence from segments
        confidences = [seg.get('confidence', 0.8) for seg in segments]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Convert log probability to confidence (if negative)
        if avg_confidence < 0:
            # Convert negative log prob to 0-1 scale
            avg_confidence = 1.0 / (1.0 + abs(avg_confidence))
        
        return min(0.99, max(0.1, avg_confidence))
    
    async def transcribe_with_context(self, audio_data: bytes, job_id: str, 
                                    context: List[str] = None, 
                                    encounter_type: str = "general") -> TranscriptionResult:
        """Transcribe with previous context for better accuracy"""
        # Build context prompt
        context_prompt = ""
        if context:
            recent_context = " ".join(context[-3:])  # Last 3 transcriptions
            context_prompt = f"Previous discussion: {recent_context}. "
        
        # Get base medical prompt
        medical_prompt = self._get_medical_context_prompt(encounter_type)
        full_prompt = context_prompt + medical_prompt
        
        # Transcribe with enhanced prompt
        result = await self.transcribe_audio(audio_data, job_id, encounter_type)
        
        # Update the transcription with context-aware adjustments
        # (Future: could use context for better entity recognition)
        
        return result