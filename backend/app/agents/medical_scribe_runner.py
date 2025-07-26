"""Medical Scribe Runner using OpenAI Agents SDK"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from agents import Runner, Session
from fastapi import WebSocket, WebSocketDisconnect
import json

from app.agents.transcription_agent import (
    transcription_agent,
    clinical_analysis_agent,
    note_formatting_agent,
    realtime_client
)

logger = logging.getLogger(__name__)


class MedicalScribeRunner:
    """Manages agent execution for medical scribe functionality"""
    
    def __init__(self):
        # Create runner with all agents
        self.agents = [
            transcription_agent,
            clinical_analysis_agent,
            note_formatting_agent
        ]
        
        # Session storage for multiple concurrent users
        self.sessions: Dict[str, Session] = {}
        
        # WebSocket connections
        self.connections: Dict[str, WebSocket] = {}
        
        # Setup realtime transcription callback
        self._setup_transcription_callback()
        
    def _setup_transcription_callback(self):
        """Setup callback for real-time transcriptions"""
        async def handle_transcription(text: str, is_partial: bool):
            """Handle transcription from Realtime API"""
            # Process through agents
            for session_id, session in self.sessions.items():
                if is_partial:
                    # Send partial transcription directly to client
                    await self._send_to_client(session_id, {
                        "type": "transcription:partial",
                        "text": text,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    # Run through clinical analysis for complete transcriptions
                    result = await Runner.run(
                        clinical_analysis_agent,
                        f"Analyze this medical transcription: {text}",
                        session=session
                    )
                    
                    # Send analysis to client
                    await self._send_to_client(session_id, {
                        "type": "transcription:complete",
                        "text": text,
                        "analysis": result.final_output,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        # Set the callback
        if realtime_client:
            realtime_client.transcription_callback = handle_transcription
            
    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Handle a new WebSocket connection from a client"""
        await websocket.accept()
        
        session_id = f"{user_id}_{datetime.utcnow().timestamp()}"
        
        # Create new session for this user
        session = Session()
        self.sessions[session_id] = session
        self.connections[session_id] = websocket
        
        logger.info(f"Client connected: {session_id}")
        
        try:
            await self._handle_client_messages(websocket, session_id, session)
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Error handling client {session_id}: {str(e)}")
        finally:
            await self._cleanup_session(session_id)
            
    async def _handle_client_messages(
        self,
        websocket: WebSocket,
        session_id: str,
        session: Session
    ):
        """Handle incoming messages from client"""
        while True:
            try:
                # Receive message
                message = await websocket.receive()
                
                if "text" in message:
                    data = json.loads(message["text"])
                    await self._process_client_message(session_id, session, data)
                    
                elif "bytes" in message:
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    await self._process_audio_data(session_id, session, audio_data)
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {session_id}")
                continue
                
    async def _process_client_message(
        self,
        session_id: str,
        session: Session,
        data: Dict[str, Any]
    ):
        """Process text message from client"""
        msg_type = data.get("type")
        
        if msg_type == "encounter:start":
            # Start transcription session
            encounter_id = data.get("encounter_id")
            patient_id = data.get("patient_id")
            
            result = await Runner.run(
                transcription_agent,
                f"Start transcription session for encounter {encounter_id} and patient {patient_id}",
                session=session
            )
            
            await self._send_to_client(session_id, {
                "type": "encounter:started",
                "encounter_id": encounter_id,
                "patient_id": patient_id,
                "status": result.final_output
            })
            
        elif msg_type == "encounter:end":
            # End transcription session
            result = await Runner.run(
                transcription_agent,
                "End the current transcription session",
                session=session
            )
            
            await self._send_to_client(session_id, {
                "type": "encounter:ended",
                "status": result.final_output
            })
            
        elif msg_type == "format:preference":
            # Update formatting preference
            format_type = data.get("format", "soap")
            session.add_message({
                "role": "user",
                "content": f"Set note format preference to: {format_type}"
            })
            
    async def _process_audio_data(
        self,
        session_id: str,
        session: Session,
        audio_data: bytes
    ):
        """Process raw audio data from client"""
        # Convert to base64 for the agent
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Process through transcription agent
        await Runner.run(
            transcription_agent,
            f"Process this audio stream: {audio_base64[:50]}...",  # Truncated for logging
            session=session
        )
        
    async def _send_to_client(self, session_id: str, data: Dict[str, Any]):
        """Send data to connected client"""
        websocket = self.connections.get(session_id)
        if websocket:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to client {session_id}: {str(e)}")
                
    async def _cleanup_session(self, session_id: str):
        """Clean up session when client disconnects"""
        # End transcription if active
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await Runner.run(
                transcription_agent,
                "End the current transcription session",
                session=session
            )
            del self.sessions[session_id]
            
        # Remove connection
        if session_id in self.connections:
            del self.connections[session_id]
            
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for session_id, websocket in self.connections.items():
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(session_id)
                
        # Clean up disconnected sessions
        for session_id in disconnected:
            await self._cleanup_session(session_id)
            
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "active_sessions": len(self.sessions),
            "connected_clients": len(self.connections),
            "agents": [agent.name for agent in self.agents],
            "realtime_connected": realtime_client.is_connected if realtime_client else False,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global runner instance
medical_scribe_runner = MedicalScribeRunner()