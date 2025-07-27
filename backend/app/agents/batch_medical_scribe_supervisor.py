"""Batch Medical Scribe Supervisor for agent orchestration"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from enum import Enum

from app.agents.base import BaseAgent, AgentMessage, AgentOrchestrator
from app.agents.batch_transcription_agent import BatchTranscriptionAgent
from app.agents.batch_clinical_context_agent import BatchClinicalContextAgent
from app.agents.batch_note_structuring_agent import BatchNoteStructuringAgent

logger = logging.getLogger(__name__)


class TranscriptionStatus(Enum):
    """Transcription processing status"""
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    STRUCTURING = "structuring"
    COMPLETED = "completed"
    ERROR = "error"


class BatchMedicalScribeSupervisor:
    """Supervises and orchestrates the medical scribe agent system"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.active_transcriptions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize agents
        self._init_agents()
        
        # Start the orchestrator
        asyncio.create_task(self._start_orchestrator())
        
    def _init_agents(self):
        """Initialize all agents in the system"""
        # Create agent instances
        self.transcription_agent = BatchTranscriptionAgent()
        self.clinical_context_agent = BatchClinicalContextAgent()
        self.note_structuring_agent = BatchNoteStructuringAgent()
        
        # Register agents with orchestrator
        self.orchestrator.register_agent(self.transcription_agent)
        self.orchestrator.register_agent(self.clinical_context_agent)
        self.orchestrator.register_agent(self.note_structuring_agent)
        
        # Set up message handlers
        self._setup_message_handlers()
        
        logger.info("All agents initialized and registered")
        
    def _setup_message_handlers(self):
        """Set up custom message handlers for supervisor"""
        # Handle agent responses
        self.transcription_agent.register_handler(
            "transcription_error",
            self._handle_transcription_error
        )
        
        self.clinical_context_agent.register_handler(
            "clinical_analysis_error",
            self._handle_analysis_error
        )
        
        self.note_structuring_agent.register_handler(
            "note_structured",
            self._handle_note_completed
        )
        
        self.note_structuring_agent.register_handler(
            "note_structuring_error",
            self._handle_structuring_error
        )
        
    async def _start_orchestrator(self):
        """Start the agent orchestrator"""
        await self.orchestrator.start()
        logger.info("Medical Scribe Supervisor started")
        
    async def process_audio_file(
        self,
        audio_file_path: str,
        encounter_id: str,
        transcription_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process an audio file through the complete pipeline"""
        try:
            # Generate transcription ID if not provided
            if not transcription_id:
                transcription_id = str(uuid.uuid4())
                
            # Initialize transcription tracking
            self.active_transcriptions[transcription_id] = {
                "transcription_id": transcription_id,
                "encounter_id": encounter_id,
                "audio_file_path": audio_file_path,
                "status": TranscriptionStatus.PENDING,
                "started_at": datetime.utcnow().isoformat(),
                "current_stage": "initialization",
                "progress": 0,
                "options": options or {},
                "results": {},
                "errors": []
            }
            
            # Start transcription process
            await self._start_transcription(transcription_id)
            
            return {
                "transcription_id": transcription_id,
                "status": "processing",
                "message": "Audio file processing started"
            }
            
        except Exception as e:
            logger.error(f"Error starting audio processing: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }
            
    async def _start_transcription(self, transcription_id: str):
        """Start the transcription process"""
        transcription_data = self.active_transcriptions[transcription_id]
        
        # Update status
        transcription_data["status"] = TranscriptionStatus.TRANSCRIBING
        transcription_data["current_stage"] = "transcription"
        transcription_data["progress"] = 10
        
        # Create message for transcription agent
        message = AgentMessage(
            agent_id="Supervisor",
            message_type="transcribe_audio",
            payload={
                "audio_file_path": transcription_data["audio_file_path"],
                "encounter_id": transcription_data["encounter_id"],
                "transcription_id": transcription_id
            }
        )
        
        # Send to transcription agent
        await self.orchestrator.send_message("BatchTranscriptionAgent", message)
        
    async def get_transcription_status(self, transcription_id: str) -> Dict[str, Any]:
        """Get the current status of a transcription"""
        if transcription_id not in self.active_transcriptions:
            return {
                "error": "Transcription not found",
                "transcription_id": transcription_id
            }
            
        transcription_data = self.active_transcriptions[transcription_id]
        
        # Calculate estimated time remaining
        progress = transcription_data["progress"]
        if progress > 0:
            elapsed = (datetime.utcnow() - datetime.fromisoformat(
                transcription_data["started_at"]
            )).total_seconds()
            estimated_total = (elapsed / progress) * 100
            estimated_remaining = estimated_total - elapsed
        else:
            estimated_remaining = None
            
        return {
            "transcription_id": transcription_id,
            "status": transcription_data["status"].value,
            "current_stage": transcription_data["current_stage"],
            "progress": transcription_data["progress"],
            "started_at": transcription_data["started_at"],
            "estimated_remaining_seconds": estimated_remaining,
            "partial_results": self._get_partial_results(transcription_data),
            "errors": transcription_data["errors"]
        }
        
    def _get_partial_results(self, transcription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get partial results based on current progress"""
        results = transcription_data["results"]
        status = transcription_data["status"]
        
        partial = {
            "sections_completed": [],
            "sections_pending": []
        }
        
        # Determine completed sections based on status
        if status.value >= TranscriptionStatus.ANALYZING.value:
            partial["sections_completed"].append("transcription")
            
        if status.value >= TranscriptionStatus.STRUCTURING.value:
            partial["sections_completed"].append("clinical_analysis")
            
        if status == TranscriptionStatus.COMPLETED:
            partial["sections_completed"].append("note_structuring")
            
        # Add actual content if available
        if "transcription_text" in results:
            partial["transcription_preview"] = results["transcription_text"][:200] + "..."
            
        if "clinical_sections" in results:
            partial["identified_sections"] = list(results["clinical_sections"].keys())
            
        if "formatted_note" in results:
            partial["note_preview"] = results["formatted_note"][:200] + "..."
            
        return partial
        
    async def get_completed_transcription(self, transcription_id: str) -> Dict[str, Any]:
        """Get the completed transcription results"""
        if transcription_id not in self.active_transcriptions:
            return {
                "error": "Transcription not found",
                "transcription_id": transcription_id
            }
            
        transcription_data = self.active_transcriptions[transcription_id]
        
        if transcription_data["status"] != TranscriptionStatus.COMPLETED:
            return {
                "error": "Transcription not yet completed",
                "status": transcription_data["status"].value,
                "transcription_id": transcription_id
            }
            
        return {
            "transcription_id": transcription_id,
            "encounter_id": transcription_data["encounter_id"],
            "status": "completed",
            "completed_at": transcription_data.get("completed_at"),
            "duration_seconds": self._calculate_duration(transcription_data),
            "results": transcription_data["results"]
        }
        
    def _calculate_duration(self, transcription_data: Dict[str, Any]) -> float:
        """Calculate processing duration"""
        if "completed_at" in transcription_data:
            start = datetime.fromisoformat(transcription_data["started_at"])
            end = datetime.fromisoformat(transcription_data["completed_at"])
            return (end - start).total_seconds()
        return 0
        
    async def cancel_transcription(self, transcription_id: str) -> Dict[str, Any]:
        """Cancel an active transcription"""
        if transcription_id not in self.active_transcriptions:
            return {
                "error": "Transcription not found",
                "transcription_id": transcription_id
            }
            
        transcription_data = self.active_transcriptions[transcription_id]
        
        if transcription_data["status"] == TranscriptionStatus.COMPLETED:
            return {
                "error": "Transcription already completed",
                "transcription_id": transcription_id
            }
            
        # Update status
        transcription_data["status"] = TranscriptionStatus.ERROR
        transcription_data["errors"].append({
            "error": "Cancelled by user",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Clean up
        del self.active_transcriptions[transcription_id]
        
        return {
            "transcription_id": transcription_id,
            "status": "cancelled",
            "message": "Transcription cancelled successfully"
        }
        
    # Message handlers
    async def _handle_transcription_error(self, message: AgentMessage):
        """Handle transcription errors"""
        error_data = message.payload
        transcription_id = error_data.get("original_request", {}).get("transcription_id")
        
        if transcription_id and transcription_id in self.active_transcriptions:
            transcription_data = self.active_transcriptions[transcription_id]
            transcription_data["status"] = TranscriptionStatus.ERROR
            transcription_data["errors"].append({
                "stage": "transcription",
                "error": error_data.get("error"),
                "timestamp": error_data.get("timestamp")
            })
            
    async def _handle_analysis_error(self, message: AgentMessage):
        """Handle clinical analysis errors"""
        error_data = message.payload
        transcription_id = error_data.get("original_request", {}).get("transcription_id")
        
        if transcription_id and transcription_id in self.active_transcriptions:
            transcription_data = self.active_transcriptions[transcription_id]
            transcription_data["status"] = TranscriptionStatus.ERROR
            transcription_data["errors"].append({
                "stage": "clinical_analysis",
                "error": error_data.get("error"),
                "timestamp": error_data.get("timestamp")
            })
            
    async def _handle_structuring_error(self, message: AgentMessage):
        """Handle note structuring errors"""
        error_data = message.payload
        transcription_id = error_data.get("original_request", {}).get("transcription_id")
        
        if transcription_id and transcription_id in self.active_transcriptions:
            transcription_data = self.active_transcriptions[transcription_id]
            transcription_data["status"] = TranscriptionStatus.ERROR
            transcription_data["errors"].append({
                "stage": "note_structuring",
                "error": error_data.get("error"),
                "timestamp": error_data.get("timestamp")
            })
            
    async def _handle_note_completed(self, message: AgentMessage):
        """Handle completed note structuring"""
        result_data = message.payload
        transcription_id = result_data.get("transcription_id")
        
        if transcription_id and transcription_id in self.active_transcriptions:
            transcription_data = self.active_transcriptions[transcription_id]
            
            # Update status
            transcription_data["status"] = TranscriptionStatus.COMPLETED
            transcription_data["current_stage"] = "completed"
            transcription_data["progress"] = 100
            transcription_data["completed_at"] = datetime.utcnow().isoformat()
            
            # Store final results
            transcription_data["results"] = result_data
            
            logger.info(f"Transcription {transcription_id} completed successfully")
            
    def cleanup_old_transcriptions(self, hours: int = 24):
        """Clean up old transcription records"""
        cutoff_time = datetime.utcnow()
        transcriptions_to_remove = []
        
        for transcription_id, data in self.active_transcriptions.items():
            started_at = datetime.fromisoformat(data["started_at"])
            age_hours = (cutoff_time - started_at).total_seconds() / 3600
            
            if age_hours > hours:
                transcriptions_to_remove.append(transcription_id)
                
        for transcription_id in transcriptions_to_remove:
            del self.active_transcriptions[transcription_id]
            
        logger.info(f"Cleaned up {len(transcriptions_to_remove)} old transcriptions")
        
    async def shutdown(self):
        """Shutdown the supervisor and all agents"""
        await self.orchestrator.stop()
        logger.info("Medical Scribe Supervisor shutdown complete")


# Singleton instance
_supervisor_instance: Optional[BatchMedicalScribeSupervisor] = None


def get_medical_scribe_supervisor() -> BatchMedicalScribeSupervisor:
    """Get or create the medical scribe supervisor instance"""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = BatchMedicalScribeSupervisor()
    return _supervisor_instance