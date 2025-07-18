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
        self.buffer_duration = 5  # seconds before processing
        self.sample_rate = 16000  # 16kHz for Whisper
        
    async def add_chunk(self, session_id: str, audio_chunk: str) -> None:
        """Add audio chunk to buffer"""
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_chunk)
            
            # Add to Redis list
            key = f"audio:buffer:{session_id}"
            await self.redis.rpush(key, audio_data)
            
            # Set expiration (1 hour)
            await self.redis.expire(key, 3600)
            
            # Update last activity
            await self.redis.set(f"audio:activity:{session_id}", 
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
            buffer_size = await self.redis.llen(key)
            
            # Calculate approximate duration based on chunk count
            # Assuming 16kHz mono audio, 2 bytes per sample
            bytes_per_second = self.sample_rate * 2
            chunks_per_second = bytes_per_second / self.chunk_size
            duration_seconds = buffer_size / chunks_per_second
            
            return duration_seconds >= self.buffer_duration
            
        except Exception as e:
            logger.error(f"Error checking transcription readiness: {e}")
            return False
            
    async def get_audio_buffer(self, session_id: str) -> bytes:
        """Get and combine all audio chunks from buffer"""
        try:
            key = f"audio:buffer:{session_id}"
            
            # Get all chunks
            chunks = await self.redis.lrange(key, 0, -1)
            
            if not chunks:
                return b""
                
            # Combine chunks
            audio_buffer = b"".join(chunks)
            
            return audio_buffer
            
        except Exception as e:
            logger.error(f"Error getting audio buffer: {e}")
            return b""
            
    async def clear_buffer(self, session_id: str) -> None:
        """Clear processed audio buffer"""
        try:
            key = f"audio:buffer:{session_id}"
            await self.redis.delete(key)
            
        except Exception as e:
            logger.error(f"Error clearing buffer: {e}")
            
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up all session data"""
        try:
            keys = [
                f"audio:buffer:{session_id}",
                f"audio:activity:{session_id}"
            ]
            
            for key in keys:
                await self.redis.delete(key)
                
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            
    def process_audio_for_whisper(self, audio_data: bytes) -> io.BytesIO:
        """Process audio data for Whisper API"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize audio
            audio_normalized = audio_array.astype(np.float32) / 32768.0
            
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            
            # Simple WAV header for 16kHz mono audio
            sample_rate = 16000
            num_channels = 1
            bits_per_sample = 16
            
            # Write WAV header
            wav_buffer.write(b'RIFF')
            wav_buffer.write((36 + len(audio_data)).to_bytes(4, 'little'))
            wav_buffer.write(b'WAVE')
            wav_buffer.write(b'fmt ')
            wav_buffer.write((16).to_bytes(4, 'little'))
            wav_buffer.write((1).to_bytes(2, 'little'))  # PCM
            wav_buffer.write((num_channels).to_bytes(2, 'little'))
            wav_buffer.write((sample_rate).to_bytes(4, 'little'))
            wav_buffer.write((sample_rate * num_channels * bits_per_sample // 8).to_bytes(4, 'little'))
            wav_buffer.write((num_channels * bits_per_sample // 8).to_bytes(2, 'little'))
            wav_buffer.write((bits_per_sample).to_bytes(2, 'little'))
            wav_buffer.write(b'data')
            wav_buffer.write(len(audio_data).to_bytes(4, 'little'))
            wav_buffer.write(audio_data)
            
            wav_buffer.seek(0)
            return wav_buffer
            
        except Exception as e:
            logger.error(f"Error processing audio for Whisper: {e}")
            raise