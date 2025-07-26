"""Medical Scribe Supervisor Agent - Orchestrates all agents"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.agents.base import AgentOrchestrator
from app.agents.realtime_transcription import RealtimeTranscriptionAgent
from app.agents.audio_stream import AudioStreamAgent
from app.agents.clinical_context import ClinicalContextAgent
from app.agents.note_structuring import NoteStructuringAgent

logger = logging.getLogger(__name__)


class MedicalScribeSupervisor:
    """Supervisor that manages all agents in the medical scribe system"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.agents = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize all agents and register them with the orchestrator"""
        if self._initialized:
            return
            
        try:
            # Create agents
            self.agents["transcription"] = RealtimeTranscriptionAgent()
            self.agents["audio_stream"] = AudioStreamAgent(self.orchestrator)
            self.agents["clinical_context"] = ClinicalContextAgent(self.orchestrator)
            self.agents["note_structuring"] = NoteStructuringAgent(self.orchestrator)
            
            # Register agents with orchestrator
            for agent in self.agents.values():
                self.orchestrator.register_agent(agent)
                
            # Set up agent callbacks and connections
            await self._setup_agent_connections()
            
            # Start the orchestrator
            await self.orchestrator.start()
            
            self._initialized = True
            logger.info("Medical Scribe Supervisor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize supervisor: {str(e)}")
            raise
            
    async def _setup_agent_connections(self):
        """Set up connections between agents"""
        transcription_agent = self.agents["transcription"]
        
        # Set up transcription callbacks
        transcription_agent.on_transcription(self._handle_complete_transcription)
        transcription_agent.on_partial_transcription(self._handle_partial_transcription)
        
    async def _handle_complete_transcription(self, text: str):
        """Handle complete transcription from Realtime API"""
        # Get session context from somewhere (this would be enhanced)
        session_id = "current_session"  # This should come from the transcription agent
        
        # Send to clinical context agent
        await self.orchestrator.send_message(
            "ClinicalContextAgent",
            {
                "agent_id": "RealtimeTranscriptionAgent",
                "message_type": "transcription:complete",
                "payload": {
                    "text": text,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        
    async def _handle_partial_transcription(self, text: str):
        """Handle partial transcription from Realtime API"""
        # Send to audio stream agent for immediate client update
        await self.orchestrator.send_message(
            "AudioStreamAgent",
            {
                "agent_id": "RealtimeTranscriptionAgent",
                "message_type": "transcription:partial",
                "payload": {
                    "text": text,
                    "session_id": "current_session",  # This should be dynamic
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        
    async def handle_client_connection(self, websocket, user_id: str, metadata: Dict[str, Any] = None):
        """Handle a new client connection"""
        if not self._initialized:
            await self.initialize()
            
        # Delegate to audio stream agent
        audio_stream_agent = self.agents["audio_stream"]
        await audio_stream_agent.handle_client_connection(websocket, user_id, metadata)
        
    async def shutdown(self):
        """Shutdown all agents gracefully"""
        if self._initialized:
            await self.orchestrator.stop()
            self._initialized = False
            logger.info("Medical Scribe Supervisor shut down")
            
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            "supervisor": "running" if self._initialized else "stopped",
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            status["agents"][name] = {
                "name": agent.name,
                "running": agent.is_running,
                "description": agent.description
            }
            
        return status