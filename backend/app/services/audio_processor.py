import base64
import io
import asyncio
from typing import Optional, List
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.chunk_size = 4096  # bytes
        self.buffer_duration = 3  # seconds before processing (reduced from 5)
        self.sample_rate = 16000  # 16kHz for Whisper
        
    async def add_chunk(self, session_id: str, audio_chunk: str) -> None:
        """Add audio chunk to buffer"""
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_chunk)
            
            # Store the latest chunk, replacing the previous one
            # Since webm chunks can't be concatenated, we'll use the most recent complete chunk
            key = f"audio:buffer:{session_id}"
            last_chunk_key = f"audio:last_chunk:{session_id}"
            
            # Store this chunk as the latest complete chunk
            self.redis.set(last_chunk_key, audio_data, ex=3600)
            
            # Also add to buffer list for size tracking
            self.redis.rpush(key, audio_data)
            
            # Keep only last 5 chunks in buffer list (for size calculation)
            list_len = self.redis.llen(key)
            if list_len > 5:
                self.redis.ltrim(key, -5, -1)
            
            # Set expiration (1 hour)
            self.redis.expire(key, 3600)
            
            # Update last activity
            self.redis.set(f"audio:activity:{session_id}", 
                          datetime.utcnow().isoformat(), 
                          ex=3600)
                               
        except Exception as e:
            logger.error(f"Error adding audio chunk: {e}")
            raise
            
    async def should_transcribe(self, session_id: str) -> bool:
        """Check if we have enough audio to transcribe"""
        try:
            # Get buffer size
            key = f"audio:buffer:{session_id}"
            buffer_size = self.redis.llen(key)
            
            # For webm/opus format, we get chunks every 100ms
            # So 10 chunks = 1 second
            duration_seconds = buffer_size / 10.0
            
            logger.info(f"Buffer size: {buffer_size} chunks, estimated duration: {duration_seconds:.2f}s (need {self.buffer_duration}s)")
            
            return duration_seconds >= self.buffer_duration
            
        except Exception as e:
            logger.error(f"Error checking transcription readiness: {e}")
            return False
            
    async def get_audio_buffer(self, session_id: str) -> bytes:
        """Get the last complete audio chunk"""
        try:
            # Get the last complete chunk (webm chunks are self-contained)
            last_chunk_key = f"audio:last_chunk:{session_id}"
            last_chunk = self.redis.get(last_chunk_key)
            
            if not last_chunk:
                # Fallback to getting the last chunk from the buffer list
                key = f"audio:buffer:{session_id}"
                chunks = self.redis.lrange(key, -1, -1)
                if chunks:
                    last_chunk = chunks[0]
                else:
                    return b""
            
            logger.info(f"Retrieved audio chunk of {len(last_chunk)} bytes for transcription")
            return last_chunk
            
        except Exception as e:
            logger.error(f"Error getting audio buffer: {e}")
            return b""
            
    async def clear_buffer(self, session_id: str) -> None:
        """Clear processed audio buffer"""
        try:
            key = f"audio:buffer:{session_id}"
            last_chunk_key = f"audio:last_chunk:{session_id}"
            self.redis.delete(key)
            self.redis.delete(last_chunk_key)
            
        except Exception as e:
            logger.error(f"Error clearing buffer: {e}")
            
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up all session data"""
        try:
            keys = [
                f"audio:buffer:{session_id}",
                f"audio:activity:{session_id}",
                f"audio:last_chunk:{session_id}"
            ]
            
            for key in keys:
                self.redis.delete(key)
                
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            
    def process_audio_for_whisper(self, audio_data: bytes) -> io.BytesIO:
        """Process audio data for Whisper API"""
        try:
            # Log audio data info
            logger.info(f"Processing audio for Whisper: {len(audio_data)} bytes")
            
            # Check if we have valid audio data
            if not audio_data or len(audio_data) == 0:
                raise ValueError("Empty audio data received")
            
            # The audio data is already in webm/opus format from the browser
            # Whisper API accepts webm format directly
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = "audio.webm"  # Whisper needs a filename with extension
            audio_buffer.seek(0)
            
            # Verify the buffer is readable
            test_read = audio_buffer.read(4)
            audio_buffer.seek(0)
            logger.debug(f"Audio buffer header (first 4 bytes): {test_read.hex() if test_read else 'empty'}")
            
            return audio_buffer
            
        except Exception as e:
            logger.error(f"Error processing audio for Whisper: {type(e).__name__}: {str(e)}")
            raise