"""Streaming Medical Scribe Supervisor for managing real-time transcription sessions"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from app.agents.base import BaseAgent, AgentMessage, AgentOrchestrator, AgentHandoff
from app.agents.streaming_transcription_agent import StreamingTranscriptionAgent
from app.agents.batch_clinical_context_agent import BatchClinicalContextAgent
from app.agents.batch_note_structuring_agent import BatchNoteStructuringAgent

logger = logging.getLogger(__name__)


class StreamingSession:
    """Represents an active streaming transcription session"""
    
    def __init__(self, session_id: str, encounter_id: str, transcription_id: str, user_id: str):
        self.session_id = session_id
        self.encounter_id = encounter_id
        self.transcription_id = transcription_id
        self.user_id = user_id
        self.start_time = datetime.utcnow()
        self.status = "active"
        self.audio_chunks_received = 0
        self.total_duration_ms = 0
        self.current_transcript = ""
        self.clinical_sections = {}
        self.last_activity = datetime.utcnow()
        self.sequence_tracker = {}
        

class StreamingMedicalScribeSupervisor:
    """Supervises streaming transcription sessions"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.active_sessions: Dict[str, StreamingSession] = {}
        
        # Initialize agents
        self._init_agents()
        
        # Start orchestrator
        asyncio.create_task(self._start_orchestrator())
        
        # Start session cleanup task
        asyncio.create_task(self._cleanup_inactive_sessions())
        
    def _init_agents(self):
        """Initialize all agents in the system"""
        # Create agent instances
        self.transcription_agent = StreamingTranscriptionAgent()
        self.clinical_context_agent = BatchClinicalContextAgent()
        self.note_structuring_agent = BatchNoteStructuringAgent()
        
        # Register agents with orchestrator
        self.orchestrator.register_agent(self.transcription_agent)
        self.orchestrator.register_agent(self.clinical_context_agent)
        self.orchestrator.register_agent(self.note_structuring_agent)
        
        # Set up message handlers
        self._setup_message_handlers()
        
        logger.info("Streaming agents initialized and registered")
        
    def _setup_message_handlers(self):
        """Set up custom message handlers"""
        # Handle transcription segments
        self.transcription_agent.register_handler(
            "transcription_segment",
            self._handle_transcription_segment
        )
        
        # Handle clinical analysis results
        self.clinical_context_agent.register_handler(
            "clinical_analysis_complete",
            self._handle_clinical_analysis
        )
        
        # Handle note structuring results
        self.note_structuring_agent.register_handler(
            "note_structured",
            self._handle_note_structured
        )
        
    async def _start_orchestrator(self):
        """Start the agent orchestrator"""
        await self.orchestrator.start()
        logger.info("Streaming Medical Scribe Supervisor started")
        
    async def start_session(
        self,
        session_id: str,
        encounter_id: str,
        transcription_id: str,
        audio_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Start a new streaming session"""
        try:
            # Create session
            session = StreamingSession(
                session_id=session_id,
                encounter_id=encounter_id,
                transcription_id=transcription_id,
                user_id=user_id
            )
            self.active_sessions[session_id] = session
            
            # Send start message to transcription agent
            message = AgentMessage(
                agent_id="Supervisor",
                message_type="start_session",
                payload={
                    "session_id": session_id,
                    "encounter_id": encounter_id,
                    "audio_config": audio_config
                }
            )
            
            await self.orchestrator.send_message("StreamingTranscriptionAgent", message)
            
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
        duration_ms: int,
        sequence_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process an audio chunk"""
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "error": "Session not found"
            }
            
        session = self.active_sessions[session_id]
        session.last_activity = datetime.utcnow()
        session.audio_chunks_received += 1
        session.total_duration_ms += duration_ms
        
        # Track sequence for ordering
        if sequence_number is not None:
            session.sequence_tracker[sequence_number] = True
            
        # Send to transcription agent
        message = AgentMessage(
            agent_id="Supervisor",
            message_type="audio_chunk",
            payload={
                "session_id": session_id,
                "audio_data": audio_data,
                "duration_ms": duration_ms
            }
        )
        
        await self.orchestrator.send_message("StreamingTranscriptionAgent", message)
        
        return {
            "status": "success",
            "chunks_received": session.audio_chunks_received,
            "total_duration_ms": session.total_duration_ms,
            "current_transcript_preview": session.current_transcript[:200] + "..." if len(session.current_transcript) > 200 else session.current_transcript
        }
        
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a streaming session"""
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "error": "Session not found"
            }
            
        session = self.active_sessions[session_id]
        session.status = "ending"
        
        # Send end message to transcription agent
        message = AgentMessage(
            agent_id="Supervisor",
            message_type="end_session",
            payload={
                "session_id": session_id
            }
        )
        
        await self.orchestrator.send_message("StreamingTranscriptionAgent", message)
        
        # Wait for final processing (with timeout)
        try:
            await asyncio.wait_for(
                self._wait_for_session_completion(session_id),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Session {session_id} completion timeout")
            
        # Get final results
        result = {
            "status": "success",
            "session_id": session_id,
            "transcription_id": session.transcription_id,
            "final_transcription": session.current_transcript,
            "clinical_note": self._format_clinical_note(session.clinical_sections),
            "duration_seconds": (datetime.utcnow() - session.start_time).total_seconds(),
            "audio_chunks_processed": session.audio_chunks_received,
            "total_audio_duration_ms": session.total_duration_ms
        }
        
        # Clean up session
        del self.active_sessions[session_id]
        
        return result
        
    async def _wait_for_session_completion(self, session_id: str):
        """Wait for session to complete processing"""
        while session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.status == "completed":
                break
            await asyncio.sleep(0.5)
            
    def validate_session(self, session_id: str, user_id: str) -> bool:
        """Validate session exists and belongs to user"""
        if session_id not in self.active_sessions:
            return False
        return self.active_sessions[session_id].user_id == user_id
        
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status"""
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "error": "Session not found"
            }
            
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": session.status,
            "duration_seconds": (datetime.utcnow() - session.start_time).total_seconds(),
            "audio_chunks_received": session.audio_chunks_received,
            "total_duration_ms": session.total_duration_ms,
            "transcript_length": len(session.current_transcript),
            "clinical_sections_identified": list(session.clinical_sections.keys()),
            "last_activity": session.last_activity.isoformat()
        }
        
    async def get_current_transcript(self, session_id: str) -> Dict[str, Any]:
        """Get current transcript and clinical sections"""
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "error": "Session not found"
            }
            
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "current_transcript": session.current_transcript,
            "clinical_sections": session.clinical_sections,
            "transcript_length": len(session.current_transcript),
            "last_updated": session.last_activity.isoformat()
        }
        
    async def trigger_clinical_analysis(self, session_id: str) -> Dict[str, Any]:
        """Manually trigger clinical analysis on current transcript"""
        if session_id not in self.active_sessions:
            return {
                "status": "error",
                "error": "Session not found"
            }
            
        session = self.active_sessions[session_id]
        
        # Send current transcript for analysis
        if session.current_transcript:
            message = AgentHandoff.create_handoff_message(
                from_agent="Supervisor",
                to_agent="ClinicalContextAgent",
                data={
                    "session_id": session_id,
                    "encounter_id": session.encounter_id,
                    "text": session.current_transcript,
                    "is_partial": True
                },
                handoff_type="analyze_transcription"
            )
            
            await self.orchestrator.send_message("ClinicalContextAgent", message)
            
            return {
                "status": "success",
                "message": "Clinical analysis triggered"
            }
        else:
            return {
                "status": "error",
                "error": "No transcript available for analysis"
            }
            
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        user_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if session.user_id == user_id:
                user_sessions.append({
                    "session_id": session_id,
                    "encounter_id": session.encounter_id,
                    "status": session.status,
                    "start_time": session.start_time.isoformat(),
                    "duration_seconds": (datetime.utcnow() - session.start_time).total_seconds()
                })
                
        return user_sessions
        
    # Message handlers
    async def _handle_transcription_segment(self, message: AgentMessage):
        """Handle transcription segment from agent"""
        payload = message.payload
        session_id = payload.get("session_id")
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Update transcript
            session.current_transcript = payload.get("total_text", "")
            
            # Trigger clinical analysis periodically (every 5 segments)
            if payload.get("segment_number", 0) % 5 == 0:
                await self.trigger_clinical_analysis(session_id)
                
    async def _handle_clinical_analysis(self, message: AgentMessage):
        """Handle clinical analysis results"""
        payload = message.payload
        session_id = payload.get("session_id")
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Update clinical sections
            if "clinical_sections" in payload:
                session.clinical_sections.update(payload["clinical_sections"])
                
    async def _handle_note_structured(self, message: AgentMessage):
        """Handle structured note results"""
        payload = message.payload
        session_id = payload.get("session_id")
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Mark session as completed
            if payload.get("is_final"):
                session.status = "completed"
                
    def _format_clinical_note(self, clinical_sections: Dict[str, Any]) -> str:
        """Format clinical sections into a note"""
        if not clinical_sections:
            return ""
            
        # Simple SOAP format
        note_parts = []
        
        if "chief_complaint" in clinical_sections:
            note_parts.append(f"**CHIEF COMPLAINT:**\n{clinical_sections['chief_complaint']}")
            
        if "history_present_illness" in clinical_sections:
            note_parts.append(f"**HISTORY OF PRESENT ILLNESS:**\n{clinical_sections['history_present_illness']}")
            
        if "medications" in clinical_sections:
            note_parts.append(f"**MEDICATIONS:**\n{clinical_sections['medications']}")
            
        if "vital_signs" in clinical_sections:
            note_parts.append(f"**VITAL SIGNS:**\n{clinical_sections['vital_signs']}")
            
        if "physical_examination" in clinical_sections:
            note_parts.append(f"**PHYSICAL EXAMINATION:**\n{clinical_sections['physical_examination']}")
            
        if "assessment" in clinical_sections:
            note_parts.append(f"**ASSESSMENT:**\n{clinical_sections['assessment']}")
            
        if "plan" in clinical_sections:
            note_parts.append(f"**PLAN:**\n{clinical_sections['plan']}")
            
        return "\n\n".join(note_parts)
        
    async def _cleanup_inactive_sessions(self):
        """Clean up inactive sessions periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                cutoff_time = datetime.utcnow()
                sessions_to_remove = []
                
                for session_id, session in self.active_sessions.items():
                    # Remove sessions inactive for more than 30 minutes
                    if (cutoff_time - session.last_activity).total_seconds() > 1800:
                        sessions_to_remove.append(session_id)
                        
                for session_id in sessions_to_remove:
                    logger.info(f"Cleaning up inactive session: {session_id}")
                    await self.end_session(session_id)
                    
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")
                
    async def shutdown(self):
        """Shutdown the supervisor and all agents"""
        # End all active sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self.end_session(session_id)
            
        # Stop orchestrator
        await self.orchestrator.stop()
        logger.info("Streaming Medical Scribe Supervisor shutdown complete")


# Singleton instance
_streaming_supervisor_instance: Optional[StreamingMedicalScribeSupervisor] = None


def get_streaming_supervisor() -> StreamingMedicalScribeSupervisor:
    """Get or create the streaming medical scribe supervisor instance"""
    global _streaming_supervisor_instance
    if _streaming_supervisor_instance is None:
        _streaming_supervisor_instance = StreamingMedicalScribeSupervisor()
    return _streaming_supervisor_instance