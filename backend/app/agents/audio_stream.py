"""Audio Stream Agent for handling browser WebSocket connections"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, Set
from datetime import datetime
import base64

from fastapi import WebSocket, WebSocketDisconnect
from app.agents.base import StreamingAgent, AgentMessage, AgentHandoff
from app.agents.base import AgentOrchestrator

logger = logging.getLogger(__name__)


class AudioStreamAgent(StreamingAgent):
    """Handles audio streaming from browser clients"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        super().__init__(
            name="AudioStreamAgent",
            description="Handles real-time audio streaming from browser clients"
        )
        self.orchestrator = orchestrator
        self.active_sessions: Dict[str, WebSocket] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def handle_client_connection(self, websocket: WebSocket, user_id: str, metadata: Dict[str, Any] = None):
        """Handle a new client WebSocket connection"""
        await websocket.accept()
        
        session_id = f"{user_id}_{datetime.utcnow().timestamp()}"
        self.active_sessions[session_id] = websocket
        self.session_metadata[session_id] = metadata or {}
        
        logger.info(f"Client connected: {session_id}")
        
        # Notify transcription agent about new session
        await self.orchestrator.send_message(
            "RealtimeTranscriptionAgent",
            AgentMessage(
                agent_id=self.name,
                message_type="session:start",
                payload={
                    "session_id": session_id,
                    "user_id": user_id,
                    "metadata": metadata
                }
            )
        )
        
        try:
            await self._handle_client_messages(websocket, session_id)
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error handling client {session_id}: {str(e)}")
        finally:
            await self._cleanup_session(session_id)
            
    async def _handle_client_messages(self, websocket: WebSocket, session_id: str):
        """Handle incoming messages from a client"""
        while True:
            try:
                # Receive message from client
                message = await websocket.receive()
                
                if "text" in message:
                    # Handle text message
                    data = json.loads(message["text"])
                    await self._process_client_message(session_id, data)
                    
                elif "bytes" in message:
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    await self._process_audio_data(session_id, audio_data)
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {session_id}")
                continue
                
    async def _process_client_message(self, session_id: str, data: Dict[str, Any]):
        """Process a text message from client"""
        msg_type = data.get("type")
        
        if msg_type == "audio:config":
            # Audio configuration update
            self.session_metadata[session_id]["audio_config"] = data.get("config", {})
            
        elif msg_type == "encounter:start":
            # Start new encounter
            encounter_data = {
                "encounter_id": data.get("encounter_id"),
                "patient_id": data.get("patient_id"),
                "encounter_type": data.get("encounter_type", "general"),
                "session_id": session_id
            }
            
            # Update session metadata
            self.session_metadata[session_id].update(encounter_data)
            
            # Notify other agents
            await self.orchestrator.broadcast_message(
                AgentMessage(
                    agent_id=self.name,
                    message_type="encounter:started",
                    payload=encounter_data
                ),
                exclude=self.name
            )
            
        elif msg_type == "encounter:end":
            # End encounter
            await self.orchestrator.broadcast_message(
                AgentMessage(
                    agent_id=self.name,
                    message_type="encounter:ended",
                    payload={
                        "session_id": session_id,
                        "encounter_id": self.session_metadata[session_id].get("encounter_id")
                    }
                ),
                exclude=self.name
            )
            
    async def _process_audio_data(self, session_id: str, audio_data: bytes):
        """Process raw audio data from client"""
        # Send audio to transcription agent
        await self.orchestrator.send_message(
            "RealtimeTranscriptionAgent",
            AgentMessage(
                agent_id=self.name,
                message_type="audio:stream",
                payload=audio_data,
                metadata={
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "audio_config": self.session_metadata[session_id].get("audio_config", {})
                }
            )
        )
        
    async def _cleanup_session(self, session_id: str):
        """Clean up a session when client disconnects"""
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
        # Notify other agents
        await self.orchestrator.send_message(
            "RealtimeTranscriptionAgent",
            AgentMessage(
                agent_id=self.name,
                message_type="session:end",
                payload={"session_id": session_id}
            )
        )
        
        # Clean up metadata
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]
            
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process messages from other agents"""
        if message.message_type == "transcription:result":
            # Forward transcription to appropriate client
            await self._send_transcription_to_client(message.payload)
            
        elif message.message_type == "transcription:partial":
            # Forward partial transcription
            await self._send_partial_transcription_to_client(message.payload)
            
        elif message.message_type == "clinical:analysis":
            # Forward clinical analysis to client
            await self._send_clinical_analysis_to_client(message.payload)
            
        return None
        
    async def _send_transcription_to_client(self, data: Dict[str, Any]):
        """Send transcription result to client"""
        session_id = data.get("session_id")
        websocket = self.active_sessions.get(session_id)
        
        if websocket:
            try:
                await websocket.send_json({
                    "type": "transcription:complete",
                    "text": data.get("text", ""),
                    "confidence": data.get("confidence", 0.0),
                    "segments": data.get("segments", []),
                    "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
                })
            except Exception as e:
                logger.error(f"Error sending transcription to client: {str(e)}")
                
    async def _send_partial_transcription_to_client(self, data: Dict[str, Any]):
        """Send partial transcription to client"""
        session_id = data.get("session_id")
        websocket = self.active_sessions.get(session_id)
        
        if websocket:
            try:
                await websocket.send_json({
                    "type": "transcription:partial",
                    "text": data.get("text", ""),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error sending partial transcription: {str(e)}")
                
    async def _send_clinical_analysis_to_client(self, data: Dict[str, Any]):
        """Send clinical analysis to client"""
        session_id = data.get("session_id")
        websocket = self.active_sessions.get(session_id)
        
        if websocket:
            try:
                await websocket.send_json({
                    "type": "clinical:analysis",
                    "analysis": data.get("analysis", {}),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error sending clinical analysis: {str(e)}")
                
    async def broadcast_to_all_clients(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        disconnected = []
        
        for session_id, websocket in self.active_sessions.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {str(e)}")
                disconnected.append(session_id)
                
        # Clean up disconnected sessions
        for session_id in disconnected:
            await self._cleanup_session(session_id)