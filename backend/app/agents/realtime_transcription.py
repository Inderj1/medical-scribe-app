"""Realtime Transcription Agent using OpenAI's Realtime API"""
import asyncio
import json
import logging
import websockets
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import base64

from app.agents.base import StreamingAgent, AgentMessage, AgentHandoff
from app.core.config import settings

logger = logging.getLogger(__name__)


class RealtimeTranscriptionAgent(StreamingAgent):
    """Handles real-time audio transcription using OpenAI's Realtime API"""
    
    def __init__(self):
        super().__init__(
            name="RealtimeTranscriptionAgent",
            description="Handles real-time audio transcription with OpenAI Realtime API"
        )
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        # Callbacks for transcription events
        self._on_transcription: Optional[Callable] = None
        self._on_partial_transcription: Optional[Callable] = None
        self._on_audio_response: Optional[Callable] = None
        
        # OpenAI Realtime API configuration
        self.api_url = "wss://api.openai.com/v1/realtime"
        self.model = settings.OPENAI_REALTIME_MODEL if hasattr(settings, 'OPENAI_REALTIME_MODEL') else "gpt-4o-realtime-preview"
        
    async def start(self):
        """Start the agent and connect to OpenAI Realtime API"""
        await super().start()
        await self._connect_to_openai()
        
    async def stop(self):
        """Stop the agent and disconnect from OpenAI"""
        await self._disconnect_from_openai()
        await super().stop()
        
    async def _connect_to_openai(self):
        """Establish WebSocket connection to OpenAI Realtime API"""
        try:
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.openai_ws = await websockets.connect(
                self.api_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            self._reconnect_attempts = 0
            
            # Start listening for messages
            asyncio.create_task(self._listen_to_openai())
            
            # Configure session
            await self._configure_session()
            
            logger.info("Connected to OpenAI Realtime API")
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {str(e)}")
            await self._handle_connection_error()
            
    async def _disconnect_from_openai(self):
        """Disconnect from OpenAI Realtime API"""
        if self.openai_ws:
            await self.openai_ws.close()
            self.openai_ws = None
            self.is_connected = False
            logger.info("Disconnected from OpenAI Realtime API")
            
    async def _configure_session(self):
        """Configure the OpenAI Realtime session"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "model": self.model,
                "instructions": """You are a medical scribe assistant. 
                Listen carefully to medical consultations and transcribe them accurately.
                Pay special attention to:
                - Medical terminology, conditions, and symptoms
                - Medication names and dosages
                - Vital signs and measurements
                - Patient history and complaints
                - Doctor's assessments and plans
                
                Maintain HIPAA compliance and patient confidentiality.""",
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
                    "silence_duration_ms": 500
                },
                "temperature": 0.3,
                "max_response_output_tokens": 4096
            }
        }
        
        await self._send_to_openai(session_config)
        
    async def _send_to_openai(self, message: Dict[str, Any]):
        """Send a message to OpenAI Realtime API"""
        if self.openai_ws and self.is_connected:
            try:
                await self.openai_ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to OpenAI: {str(e)}")
                await self._handle_connection_error()
                
    async def _listen_to_openai(self):
        """Listen for messages from OpenAI Realtime API"""
        try:
            async for message in self.openai_ws:
                data = json.loads(message)
                await self._handle_openai_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("OpenAI WebSocket connection closed")
            await self._handle_connection_error()
        except Exception as e:
            logger.error(f"Error in OpenAI listener: {str(e)}")
            await self._handle_connection_error()
            
    async def _handle_openai_message(self, message: Dict[str, Any]):
        """Handle messages from OpenAI Realtime API"""
        msg_type = message.get("type")
        
        if msg_type == "error":
            logger.error(f"OpenAI API error: {message.get('error')}")
            
        elif msg_type == "session.created" or msg_type == "session.updated":
            self.session_id = message.get("session", {}).get("id")
            logger.info(f"Session configured: {self.session_id}")
            
        elif msg_type == "response.audio_transcript.delta":
            # Partial transcription update
            delta = message.get("delta", {}).get("audio_transcript", "")
            if delta and self._on_partial_transcription:
                await self._on_partial_transcription(delta)
                
        elif msg_type == "response.audio_transcript.done":
            # Complete transcription
            transcript = message.get("audio_transcript", "")
            if transcript and self._on_transcription:
                await self._on_transcription(transcript)
                
        elif msg_type == "response.audio.delta":
            # Audio response chunk
            audio_data = message.get("delta", {}).get("audio")
            if audio_data and self._on_audio_response:
                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_data)
                await self._on_audio_response(audio_bytes)
                
        elif msg_type == "input_audio_buffer.speech_started":
            logger.debug("Speech started detected")
            
        elif msg_type == "input_audio_buffer.speech_stopped":
            logger.debug("Speech stopped detected")
            
        elif msg_type == "response.done":
            # Response completed
            logger.debug("Response completed")
            
    async def _handle_connection_error(self):
        """Handle connection errors with exponential backoff"""
        self.is_connected = False
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            wait_time = min(60, 2 ** self._reconnect_attempts)
            logger.info(f"Reconnecting in {wait_time} seconds (attempt {self._reconnect_attempts})")
            await asyncio.sleep(wait_time)
            await self._connect_to_openai()
        else:
            logger.error("Max reconnection attempts reached")
            
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages from other agents"""
        if message.message_type == "audio:stream":
            # Handle audio stream data
            audio_data = message.payload
            await self.send_audio(audio_data)
            
        elif message.message_type == "session:start":
            # Start a new transcription session
            session_data = message.payload
            await self.start_session(session_data)
            
        elif message.message_type == "session:end":
            # End the current session
            await self.end_session()
            
        return None
        
    async def send_audio(self, audio_data: bytes):
        """Send audio data to OpenAI Realtime API"""
        if not self.is_connected:
            logger.warning("Not connected to OpenAI, dropping audio")
            return
            
        # OpenAI expects base64 encoded audio in the message
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        
        await self._send_to_openai(message)
        
    async def start_session(self, session_data: Dict[str, Any]):
        """Start a new transcription session"""
        # Clear any existing audio buffer
        clear_message = {
            "type": "input_audio_buffer.clear"
        }
        await self._send_to_openai(clear_message)
        
        # Update session configuration if needed
        if "instructions" in session_data:
            update_message = {
                "type": "session.update",
                "session": {
                    "instructions": session_data["instructions"]
                }
            }
            await self._send_to_openai(update_message)
            
    async def end_session(self):
        """End the current transcription session"""
        # Commit any remaining audio
        commit_message = {
            "type": "input_audio_buffer.commit"
        }
        await self._send_to_openai(commit_message)
        
    def on_transcription(self, callback: Callable):
        """Register callback for complete transcriptions"""
        self._on_transcription = callback
        
    def on_partial_transcription(self, callback: Callable):
        """Register callback for partial transcriptions"""
        self._on_partial_transcription = callback
        
    def on_audio_response(self, callback: Callable):
        """Register callback for audio responses"""
        self._on_audio_response = callback