"""Batch Transcription Agent using OpenAI Whisper API"""
import asyncio
import json
import logging
import tempfile
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class BatchTranscriptionAgent(BaseAgent):
    """Agent for processing audio files using OpenAI Whisper API"""
    
    def __init__(self):
        super().__init__(
            name="BatchTranscriptionAgent",
            description="Processes audio files and generates transcriptions using Whisper API"
        )
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.supported_formats = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm']
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "transcribe_audio":
            return await self._handle_transcription_request(message)
        elif message.message_type == "check_audio_quality":
            return await self._check_audio_quality(message)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
            
    async def _handle_transcription_request(self, message: AgentMessage) -> AgentMessage:
        """Handle audio transcription request"""
        try:
            audio_file_path = message.payload.get("audio_file_path")
            encounter_id = message.payload.get("encounter_id")
            transcription_id = message.payload.get("transcription_id")
            
            if not audio_file_path:
                return self._create_error_response(message, "No audio file path provided")
                
            # Validate file format
            file_ext = Path(audio_file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return self._create_error_response(
                    message, 
                    f"Unsupported audio format: {file_ext}. Supported formats: {', '.join(self.supported_formats)}"
                )
                
            # Transcribe using Whisper API
            logger.info(f"Starting transcription for {transcription_id}")
            transcription = await self._transcribe_audio(audio_file_path)
            
            # Create response with transcription
            response_data = {
                "transcription_id": transcription_id,
                "encounter_id": encounter_id,
                "text": transcription["text"],
                "language": transcription.get("language", "en"),
                "duration": transcription.get("duration"),
                "segments": transcription.get("segments", []),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            # Create handoff message to clinical context agent
            return AgentHandoff.create_handoff_message(
                from_agent=self.name,
                to_agent="ClinicalContextAgent",
                data=response_data,
                handoff_type="analyze_transcription"
            )
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return self._create_error_response(message, str(e))
            
    async def _transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper API"""
        with open(audio_file_path, 'rb') as audio_file:
            # Get detailed transcription with timestamps
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                language="en",
                timestamp_granularities=["segment"]
            )
            
        # Convert response to dict
        return {
            "text": response.text,
            "language": response.language,
            "duration": response.duration,
            "segments": [
                {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in (response.segments or [])
            ]
        }
        
    async def _check_audio_quality(self, message: AgentMessage) -> AgentMessage:
        """Check audio file quality metrics"""
        try:
            audio_file_path = message.payload.get("audio_file_path")
            
            # Get file size
            file_size = os.path.getsize(audio_file_path)
            
            # Basic quality metrics
            quality_metrics = {
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "format_supported": Path(audio_file_path).suffix.lower() in self.supported_formats,
                "estimated_processing_time": self._estimate_processing_time(file_size),
                "quality_score": 0.95  # Placeholder - implement actual quality check
            }
            
            return AgentMessage(
                agent_id=self.name,
                message_type="audio_quality_result",
                payload=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Audio quality check error: {str(e)}")
            return self._create_error_response(message, str(e))
            
    def _estimate_processing_time(self, file_size: int) -> float:
        """Estimate processing time based on file size"""
        # Rough estimate: 1MB takes ~2 seconds to process
        return round(file_size / (1024 * 1024) * 2, 1)
        
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create error response message"""
        return AgentMessage(
            agent_id=self.name,
            message_type="transcription_error",
            payload={
                "error": error,
                "original_request": original_message.payload,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Agent factory function
def create_batch_transcription_agent() -> BatchTranscriptionAgent:
    """Create and return a batch transcription agent instance"""
    return BatchTranscriptionAgent()