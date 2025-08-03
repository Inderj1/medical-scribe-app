"""Service for handling OpenAI Whisper API transcription with speaker diarization"""
import logging
import os
import aiofiles
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import openai
from openai import AsyncOpenAI
import json
import tempfile
import subprocess

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for handling audio transcription using OpenAI Whisper API"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "whisper-1"
        
    async def transcribe_with_diarization(
        self,
        audio_path: str,
        language: str = "en",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file with speaker diarization using OpenAI Whisper API
        
        Note: OpenAI Whisper API doesn't natively support speaker diarization yet.
        This implementation uses the standard transcription with timestamps,
        and implements a basic speaker change detection based on pauses.
        
        For production use, consider:
        1. Using pyannote.audio for speaker diarization
        2. Using AssemblyAI or Deepgram which have built-in diarization
        3. Post-processing with speaker embedding models
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "en" for English)
            prompt: Optional prompt to guide transcription
            
        Returns:
            Dict with transcription results including speaker segments
        """
        try:
            # Prepare prompt for medical context
            if not prompt:
                prompt = (
                    "This is a medical consultation between a healthcare provider and a patient. "
                    "The conversation may include medical terminology, symptoms, diagnoses, and treatment plans."
                )
            
            # Open audio file
            with open(audio_path, "rb") as audio_file:
                # Request transcription with timestamps
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format="verbose_json"  # Get timestamps
                )
            
            # Process response
            if hasattr(response, 'segments'):
                segments = self._process_segments_with_speakers(response.segments)
                
                return {
                    "status": "success",
                    "text": response.text,
                    "segments": segments,
                    "duration": response.duration if hasattr(response, 'duration') else None,
                    "language": response.language if hasattr(response, 'language') else language
                }
            else:
                # Fallback if no segments available
                return {
                    "status": "success",
                    "text": response.text,
                    "segments": [{
                        "text": response.text,
                        "speaker": "SPEAKER_00",
                        "start": 0,
                        "end": 0
                    }],
                    "duration": None,
                    "language": language
                }
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _process_segments_with_speakers(self, segments: List[Any]) -> List[Dict[str, Any]]:
        """
        Process transcription segments and assign speakers based on patterns
        
        This is a simplified speaker detection based on:
        1. Significant pauses between segments (> 1.5 seconds)
        2. Question/answer patterns
        3. Medical consultation patterns
        
        For production, use proper speaker diarization models.
        """
        processed_segments = []
        current_speaker = "SPEAKER_00"
        last_end_time = 0
        
        # Patterns that might indicate doctor speech
        doctor_patterns = [
            "how are you feeling",
            "what brings you",
            "let me examine",
            "i recommend",
            "prescription",
            "diagnosis",
            "treatment plan",
            "any questions",
            "follow up"
        ]
        
        # Patterns that might indicate patient speech
        patient_patterns = [
            "i feel",
            "i have been",
            "it hurts",
            "i'm experiencing",
            "started about",
            "yes, doctor",
            "no, doctor"
        ]
        
        for i, segment in enumerate(segments):
            text = segment.text.lower() if hasattr(segment, 'text') else str(segment.get('text', '')).lower()
            start = segment.start if hasattr(segment, 'start') else segment.get('start', 0)
            end = segment.end if hasattr(segment, 'end') else segment.get('end', 0)
            
            # Check for speaker change based on pause
            if start - last_end_time > 1.5:  # 1.5 second pause
                # Toggle speaker
                current_speaker = "SPEAKER_01" if current_speaker == "SPEAKER_00" else "SPEAKER_00"
            
            # Refine speaker based on content patterns
            if any(pattern in text for pattern in doctor_patterns):
                current_speaker = "SPEAKER_00"  # Doctor
            elif any(pattern in text for pattern in patient_patterns):
                current_speaker = "SPEAKER_01"  # Patient
            
            # Check for question marks (often indicates speaker change in next segment)
            if text.strip().endswith('?') and i < len(segments) - 1:
                # Next segment likely different speaker
                next_speaker = "SPEAKER_01" if current_speaker == "SPEAKER_00" else "SPEAKER_00"
            
            processed_segments.append({
                "text": segment.text if hasattr(segment, 'text') else segment.get('text', ''),
                "speaker": current_speaker,
                "start": start,
                "end": end
            })
            
            last_end_time = end
        
        # Post-process to merge consecutive segments from same speaker
        merged_segments = []
        for segment in processed_segments:
            if merged_segments and merged_segments[-1]["speaker"] == segment["speaker"]:
                # Merge with previous segment
                merged_segments[-1]["text"] += " " + segment["text"]
                merged_segments[-1]["end"] = segment["end"]
            else:
                merged_segments.append(segment)
        
        return merged_segments
    
    async def transcribe_simple(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Simple transcription without speaker diarization
        
        Args:
            audio_path: Path to audio file
            language: Language code
            
        Returns:
            Dict with transcription results
        """
        try:
            with open(audio_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language
                )
            
            return {
                "status": "success",
                "text": response.text
            }
            
        except Exception as e:
            logger.error(f"Error in simple transcription: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }