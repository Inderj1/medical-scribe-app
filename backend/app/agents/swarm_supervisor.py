"""Medical Scribe Supervisor using Swarm for agent orchestration"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from swarm import Swarm
from app.agents.medical_scribe_agents import (
    supervisor_agent,
    transcription_agent,
    clinical_analysis_agent,
    note_structuring_agent,
    quality_assurance_agent,
    start_transcription_session,
    process_audio_chunk,
    end_transcription_session
)

logger = logging.getLogger(__name__)


class SwarmMedicalScribeSupervisor:
    """Supervisor using Swarm for OpenAI Agents orchestration"""
    
    def __init__(self):
        self.client = Swarm()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("Swarm Medical Scribe Supervisor initialized")
        
    async def start_session(
        self,
        session_id: str,
        encounter_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Start a new transcription session"""
        try:
            # Track session
            self.active_sessions[session_id] = {
                "encounter_id": encounter_id,
                "user_id": user_id,
                "start_time": datetime.utcnow(),
                "status": "active"
            }
            
            # Use Swarm to start session
            response = self.client.run(
                agent=transcription_agent,
                messages=[{
                    "role": "user",
                    "content": f"Start a transcription session with session_id={session_id} and encounter_id={encounter_id}"
                }]
            )
            
            # The agent will call the start_transcription_session function
            logger.info(f"Session {session_id} started: {response.messages[-1].content}")
            
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
        """Process an audio chunk"""
        if session_id not in self.active_sessions:
            return {"status": "error", "error": "Session not found"}
            
        try:
            # Use Swarm to process audio
            response = self.client.run(
                agent=transcription_agent,
                messages=[{
                    "role": "user",
                    "content": f"Process audio chunk for session {session_id} with duration {duration_ms}ms"
                }],
                context_variables={
                    "session_id": session_id,
                    "audio_data": audio_data,
                    "duration_ms": duration_ms
                }
            )
            
            # Update session
            session = self.active_sessions[session_id]
            session["last_activity"] = datetime.utcnow()
            
            # Parse response
            result_content = response.messages[-1].content
            
            return {
                "status": "success",
                "message": result_content,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a session and get the final clinical note"""
        if session_id not in self.active_sessions:
            return {"status": "error", "error": "Session not found"}
            
        try:
            session = self.active_sessions[session_id]
            
            # Use Swarm to end session and process through pipeline
            response = self.client.run(
                agent=supervisor_agent,
                messages=[{
                    "role": "user",
                    "content": f"End transcription session {session_id} and create a complete clinical note"
                }]
            )
            
            # Process all handoffs
            final_agent = response.agent
            final_messages = response.messages
            
            # Extract the clinical note from the conversation
            clinical_note = None
            for message in reversed(final_messages):
                if "SUBJECTIVE:" in message.content or "CLINICAL NOTE:" in message.content:
                    clinical_note = message.content
                    break
                    
            # Clean up
            del self.active_sessions[session_id]
            
            return {
                "status": "success",
                "session_id": session_id,
                "clinical_note": clinical_note or "No clinical note generated",
                "final_agent": final_agent.name if final_agent else "Unknown",
                "duration_seconds": (datetime.utcnow() - session["start_time"]).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return {"status": "error", "error": str(e)}
            
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
            "duration_seconds": (datetime.utcnow() - session["start_time"]).total_seconds(),
            "last_activity": session.get("last_activity", session["start_time"]).isoformat()
        }
        
    async def run_quality_check(self, clinical_note: str) -> Dict[str, Any]:
        """Run quality assurance on a clinical note"""
        try:
            response = self.client.run(
                agent=quality_assurance_agent,
                messages=[{
                    "role": "user",
                    "content": f"Check the quality of this clinical note:\n\n{clinical_note}"
                }]
            )
            
            return {
                "status": "success",
                "quality_report": response.messages[-1].content
            }
            
        except Exception as e:
            logger.error(f"Error running quality check: {str(e)}")
            return {"status": "error", "error": str(e)}


# Singleton instance
_swarm_supervisor_instance: Optional[SwarmMedicalScribeSupervisor] = None


def get_swarm_supervisor() -> SwarmMedicalScribeSupervisor:
    """Get or create the Swarm supervisor instance"""
    global _swarm_supervisor_instance
    if _swarm_supervisor_instance is None:
        _swarm_supervisor_instance = SwarmMedicalScribeSupervisor()
    return _swarm_supervisor_instance