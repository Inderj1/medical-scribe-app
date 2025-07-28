"""Medical Scribe Supervisor using OpenAI Agents SDK"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from swarm import Swarm
from app.agents.openai_streaming_agents import (
    transcription_agent,
    clinical_analysis_agent, 
    note_structuring_agent,
    start_transcription_session,
    process_audio_chunk,
    end_transcription_session
)

logger = logging.getLogger(__name__)


class OpenAIAgentSupervisor:
    """Supervisor for OpenAI Agents SDK based medical scribe"""
    
    def __init__(self):
        self.swarm = Swarm()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("OpenAI Agent Supervisor initialized")
        
    async def start_session(
        self,
        session_id: str,
        encounter_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Start a new transcription session"""
        try:
            # Initialize session tracking
            self.active_sessions[session_id] = {
                "encounter_id": encounter_id,
                "user_id": user_id,
                "start_time": datetime.utcnow(),
                "status": "active",
                "current_agent": "transcription"
            }
            
            # Start transcription session via agent
            result = await self.swarm.run(
                agent=transcription_agent,
                input=f"Start transcription session with session_id={session_id} and encounter_id={encounter_id}"
            )
            
            # The agent function will be called directly
            agent_result = await start_transcription_session(session_id, encounter_id)
            
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Session started successfully"
            }
            
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def process_audio_chunk(
        self,
        session_id: str,
        audio_data: str,
        duration_ms: int
    ) -> Dict[str, Any]:
        """Process an audio chunk through the agent"""
        if session_id not in self.active_sessions:
            return {"status": "error", "error": "Session not found"}
            
        try:
            # Process via agent function
            result = await process_audio_chunk(session_id, audio_data, duration_ms)
            
            # Update session tracking
            session = self.active_sessions[session_id]
            session["last_activity"] = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a session and process through full pipeline"""
        if session_id not in self.active_sessions:
            return {"status": "error", "error": "Session not found"}
            
        try:
            session = self.active_sessions[session_id]
            
            # End transcription session - this returns a Handoff
            handoff_result = await end_transcription_session(session_id)
            
            # Process the handoff chain
            final_result = await self._process_handoff_chain(
                handoff_result,
                session["encounter_id"]
            )
            
            # Clean up
            del self.active_sessions[session_id]
            
            return {
                "status": "success",
                "session_id": session_id,
                "clinical_note": final_result.get("formatted_note", ""),
                "format": final_result.get("format", "soap"),
                "sections": final_result.get("sections", [])
            }
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    async def _process_handoff_chain(
        self,
        initial_handoff,
        encounter_id: str
    ) -> Dict[str, Any]:
        """Process a chain of agent handoffs"""
        current_result = initial_handoff
        
        # Process handoffs until we get a final result
        while hasattr(current_result, 'agent'):
            if current_result.agent == clinical_analysis_agent:
                # Call clinical analysis
                metadata = current_result.metadata
                current_result = await clinical_analysis_agent.functions[0](
                    transcript=metadata["transcript"],
                    encounter_id=encounter_id
                )
                
            elif current_result.agent == note_structuring_agent:
                # Call note structuring
                metadata = current_result.metadata
                current_result = await note_structuring_agent.functions[0](
                    clinical_sections=metadata["clinical_sections"],
                    format_type="soap"
                )
                
            else:
                break
                
        return current_result if isinstance(current_result, dict) else {}
        
    def validate_session(self, session_id: str, user_id: str) -> bool:
        """Validate session exists and belongs to user"""
        if session_id not in self.active_sessions:
            return False
        return self.active_sessions[session_id]["user_id"] == user_id
        
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status"""
        if session_id not in self.active_sessions:
            return {"status": "error", "error": "Session not found"}
            
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "current_agent": session["current_agent"],
            "duration_seconds": (datetime.utcnow() - session["start_time"]).total_seconds(),
            "last_activity": session.get("last_activity", session["start_time"]).isoformat()
        }
        
    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions"""
        cutoff_time = datetime.utcnow()
        sessions_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            last_activity = session.get("last_activity", session["start_time"])
            if (cutoff_time - last_activity).total_seconds() > timeout_minutes * 60:
                sessions_to_remove.append(session_id)
                
        for session_id in sessions_to_remove:
            logger.info(f"Cleaning up inactive session: {session_id}")
            await self.end_session(session_id)


# Singleton instance
_supervisor_instance: Optional[OpenAIAgentSupervisor] = None


def get_openai_agent_supervisor() -> OpenAIAgentSupervisor:
    """Get or create the OpenAI agent supervisor instance"""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = OpenAIAgentSupervisor()
    return _supervisor_instance