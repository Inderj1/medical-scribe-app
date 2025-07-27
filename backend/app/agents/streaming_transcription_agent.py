"""Streaming Transcription Agent using OpenAI Whisper API with audio chunks"""
import asyncio
import json
import logging
import tempfile
import os
import wave
import io
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Manages audio chunks for streaming transcription"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_chunks: List[bytes] = []
        self.total_duration_ms = 0
        self.last_transcription_time = datetime.utcnow()
        
    def add_chunk(self, audio_data: bytes, duration_ms: int):
        """Add audio chunk to buffer"""
        self.audio_chunks.append(audio_data)
        self.total_duration_ms += duration_ms
        
    def get_audio_for_transcription(self) -> Tuple[bytes, int]:
        """Get accumulated audio and clear buffer"""
        if not self.audio_chunks:
            return b'', 0
            
        # Combine all chunks
        combined_audio = b''.join(self.audio_chunks)
        duration = self.total_duration_ms
        
        # Clear buffer
        self.audio_chunks = []
        self.total_duration_ms = 0
        self.last_transcription_time = datetime.utcnow()
        
        return combined_audio, duration
        
    def should_transcribe(self, min_duration_ms: int = 5000, max_duration_ms: int = 30000) -> bool:
        """Check if we should transcribe based on buffer size or time"""
        # Transcribe if we have enough audio
        if self.total_duration_ms >= min_duration_ms:
            return True
            
        # Force transcription if buffer is getting too large
        if self.total_duration_ms >= max_duration_ms:
            return True
            
        # Transcribe if it's been too long since last transcription (avoid losing context)
        time_since_last = (datetime.utcnow() - self.last_transcription_time).total_seconds()
        if time_since_last > 10 and self.total_duration_ms > 0:  # 10 seconds
            return True
            
        return False
        
    def create_wav_file(self, audio_data: bytes) -> bytes:
        """Convert raw audio to WAV format for Whisper"""
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
            
        wav_buffer.seek(0)
        return wav_buffer.read()


class StreamingTranscriptionAgent(BaseAgent):
    """Agent for processing streaming audio using OpenAI Whisper API"""
    
    def __init__(self):
        super().__init__(
            name="StreamingTranscriptionAgent",
            description="Processes audio chunks and generates progressive transcriptions"
        )
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Session audio buffers
        self.session_buffers: Dict[str, AudioBuffer] = {}
        
        # Session transcription context
        self.session_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Background tasks for periodic transcription
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "start_session":
            return await self._handle_start_session(message)
        elif message.message_type == "audio_chunk":
            return await self._handle_audio_chunk(message)
        elif message.message_type == "end_session":
            return await self._handle_end_session(message)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
            
    async def _handle_start_session(self, message: AgentMessage) -> AgentMessage:
        """Initialize a new transcription session"""
        session_id = message.payload.get("session_id")
        encounter_id = message.payload.get("encounter_id")
        audio_config = message.payload.get("audio_config", {})
        
        # Initialize session
        self.session_buffers[session_id] = AudioBuffer(
            sample_rate=audio_config.get("sample_rate", 16000),
            channels=audio_config.get("channels", 1)
        )
        
        self.session_contexts[session_id] = {
            "encounter_id": encounter_id,
            "session_id": session_id,
            "start_time": datetime.utcnow(),
            "transcription_count": 0,
            "total_text": "",
            "audio_config": audio_config
        }
        
        # Start background task for periodic transcription
        self.background_tasks[session_id] = asyncio.create_task(
            self._periodic_transcription_check(session_id)
        )
        
        logger.info(f"Started transcription session: {session_id}")
        
        return AgentMessage(
            agent_id=self.name,
            message_type="session_started",
            payload={
                "session_id": session_id,
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    async def _handle_audio_chunk(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming audio chunk"""
        session_id = message.payload.get("session_id")
        audio_data = message.payload.get("audio_data")  # Base64 encoded
        duration_ms = message.payload.get("duration_ms", 0)
        
        if session_id not in self.session_buffers:
            logger.error(f"Unknown session: {session_id}")
            return None
            
        # Decode audio data
        import base64
        audio_bytes = base64.b64decode(audio_data)
        
        # Add to buffer
        buffer = self.session_buffers[session_id]
        buffer.add_chunk(audio_bytes, duration_ms)
        
        # Check if we should transcribe
        if buffer.should_transcribe():
            return await self._transcribe_buffer(session_id)
            
        return None
        
    async def _handle_end_session(self, message: AgentMessage) -> AgentMessage:
        """End transcription session and process any remaining audio"""
        session_id = message.payload.get("session_id")
        
        if session_id not in self.session_buffers:
            logger.error(f"Unknown session: {session_id}")
            return self._create_error_response(message, "Unknown session")
            
        # Cancel background task
        if session_id in self.background_tasks:
            self.background_tasks[session_id].cancel()
            
        # Transcribe any remaining audio
        final_result = await self._transcribe_buffer(session_id, is_final=True)
        
        # Get complete transcription
        context = self.session_contexts[session_id]
        
        # Clean up session
        del self.session_buffers[session_id]
        del self.session_contexts[session_id]
        if session_id in self.background_tasks:
            del self.background_tasks[session_id]
            
        # Return final transcription for clinical analysis
        return AgentHandoff.create_handoff_message(
            from_agent=self.name,
            to_agent="ClinicalContextAgent",
            data={
                "session_id": session_id,
                "encounter_id": context["encounter_id"],
                "text": context["total_text"],
                "duration_seconds": (datetime.utcnow() - context["start_time"]).total_seconds(),
                "transcription_count": context["transcription_count"],
                "timestamp": datetime.utcnow().isoformat(),
                "is_final": True
            },
            handoff_type="analyze_transcription"
        )
        
    async def _transcribe_buffer(self, session_id: str, is_final: bool = False) -> Optional[AgentMessage]:
        """Transcribe accumulated audio buffer"""
        buffer = self.session_buffers[session_id]
        context = self.session_contexts[session_id]
        
        # Get audio data
        audio_data, duration_ms = buffer.get_audio_for_transcription()
        
        if not audio_data:
            return None
            
        try:
            # Convert to WAV format
            wav_data = buffer.create_wav_file(audio_data)
            
            # Create temporary file for Whisper API
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_file_path = tmp_file.name
                
            try:
                # Transcribe with Whisper
                with open(tmp_file_path, 'rb') as audio_file:
                    # Use prompt to maintain context from previous transcriptions
                    prompt = self._create_prompt(context)
                    
                    response = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="en",
                        prompt=prompt,
                        response_format="text"
                    )
                    
                transcription_text = response.strip()
                
                # Update context
                context["transcription_count"] += 1
                if transcription_text:
                    # Add space between segments
                    if context["total_text"]:
                        context["total_text"] += " "
                    context["total_text"] += transcription_text
                    
                # Create response
                result = {
                    "session_id": session_id,
                    "encounter_id": context["encounter_id"],
                    "text_segment": transcription_text,
                    "total_text": context["total_text"],
                    "segment_number": context["transcription_count"],
                    "duration_ms": duration_ms,
                    "is_partial": not is_final,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Transcribed segment {context['transcription_count']} for session {session_id}")
                
                # Send partial transcription for incremental processing
                if not is_final:
                    return AgentMessage(
                        agent_id=self.name,
                        message_type="transcription_segment",
                        payload=result
                    )
                    
            finally:
                # Clean up temp file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return self._create_error_response(
                AgentMessage(agent_id=self.name, message_type="error", payload={}),
                str(e)
            )
            
        return None
        
    def _create_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for Whisper to maintain context"""
        # Use the last ~200 characters of previous transcription as context
        # This helps Whisper maintain consistency in medical terminology
        if context["total_text"]:
            last_text = context["total_text"][-200:]
            # Find last complete sentence
            last_period = last_text.rfind('.')
            if last_period > 0:
                last_text = last_text[last_period + 1:].strip()
            return f"Medical consultation transcript. Previous context: ...{last_text}"
        else:
            return "Medical consultation transcript between doctor and patient."
            
    async def _periodic_transcription_check(self, session_id: str):
        """Periodically check if buffer needs transcription"""
        try:
            while session_id in self.session_buffers:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                buffer = self.session_buffers.get(session_id)
                if buffer and buffer.should_transcribe():
                    await self._transcribe_buffer(session_id)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in periodic transcription check: {str(e)}")
            
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
def create_streaming_transcription_agent() -> StreamingTranscriptionAgent:
    """Create and return a streaming transcription agent instance"""
    return StreamingTranscriptionAgent()