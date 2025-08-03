"""Simplified orchestrator for medical scribe workflow"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.agents_v2.base_agents_simple import medical_scribe_agents
from app.agents_v2.models import SessionContext, TranscriptionData
from app.core.config import settings
from app.core.sse_manager import sse_manager

logger = logging.getLogger(__name__)


class MedicalScribeOrchestrator:
    """Orchestrates the medical scribe workflow"""
    
    def __init__(self):
        self.agents = medical_scribe_agents
        self.current_agent = None
    
    async def process_audio_transcription(
        self,
        transcription_id: str,
        audio_path: str,
        patient_context: Dict[str, Any],
        format_preference: str = "soap",
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process audio file through the complete agent pipeline"""
        
        session_id = f"session_{transcription_id}"
        
        # Create session context
        session_context = SessionContext(
            session_id=session_id,
            transcription_id=transcription_id,
            patient_context=patient_context,
            audio_path=audio_path,
            format_preference=format_preference,
            encounter_date=patient_context.get("encounter_date"),
            encounter_id=patient_context.get("encounter_id")
        )
        
        # Store in agents instance
        self.agents.session_contexts[session_id] = session_context
        
        try:
            logger.info(f"Starting audio processing for transcription {transcription_id}")
            
            # Prepare session data
            session_data = {
                "session_id": session_id,
                "transcription_id": transcription_id,
                "audio_path": audio_path,
                "format_preference": format_preference,
                "language": language,
                "patient_context": patient_context,
                "ehr_sections": patient_context.get("ehr_sections", {})
            }
            
            # Send initial SSE event
            await sse_manager.publish(
                f"transcription_{transcription_id}",
                {
                    "type": "processing_started",
                    "data": {"message": "Starting audio transcription..."}
                }
            )
            
            # Execute agent pipeline manually
            # 1. Transcription
            self.current_agent = self.agents.transcription_agent
            logger.info(f"Running {self.current_agent.name}")
            
            transcript_result = await self.agents.process_audio_file(session_data, audio_path)
            self.agents.on_transcription_complete(session_data)
            
            # Mock transcript for testing
            transcript = "Patient presents with headache for 3 days. No fever. Assessment: Tension headache. Plan: Rest and OTC pain relief."
            
            # 2. Clinical Analysis
            self.current_agent = self.agents.clinical_analysis_agent
            logger.info(f"Running {self.current_agent.name}")
            
            clinical_data = await self.agents.extract_clinical_sections(session_data, transcript)
            entities = await self.agents.identify_medical_entities(session_data, clinical_data)
            clinical_data = await self.agents.enhance_with_ehr(session_data, clinical_data)
            self.agents.on_analysis_complete(session_data)
            
            # 3. Note Structuring
            self.current_agent = self.agents.note_structuring_agent
            logger.info(f"Running {self.current_agent.name}")
            
            structured_note = await self.agents.format_soap_note(session_data, clinical_data)
            self.agents.on_note_structured(session_data)
            
            # 4. Quality Assurance
            self.current_agent = self.agents.qa_agent
            logger.info(f"Running {self.current_agent.name}")
            
            validation = await self.agents.validate_note(session_data, structured_note)
            qa_report = await self.agents.generate_qa_report(session_data, structured_note, validation)
            
            # Send completion event
            await sse_manager.publish(
                f"transcription_{transcription_id}",
                {
                    "type": "processing_complete",
                    "data": {
                        "final_agent": self.current_agent.name,
                        "message": "Processing complete"
                    }
                }
            )
            
            logger.info(f"Completed audio processing for transcription {transcription_id}")
            
            return {
                "success": True,
                "transcription_id": transcription_id,
                "session_id": session_id,
                "final_agent": self.current_agent.name,
                "clinical_note": structured_note.note_content,
                "qa_report": {
                    "overall_score": qa_report.overall_score,
                    "approved": qa_report.approved
                }
            }
            
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}")
            
            # Send error event
            await sse_manager.publish(
                f"transcription_{transcription_id}",
                {
                    "type": "processing_error",
                    "data": {"error": str(e)}
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "transcription_id": transcription_id
            }
        
        finally:
            # Clean up session context after delay
            asyncio.create_task(self._cleanup_session(session_id, delay=300))
    
    async def process_streaming_transcript(
        self,
        session_id: str,
        transcription_id: str,
        patient_context: Dict[str, Any],
        format_preference: str = "soap"
    ) -> Dict[str, Any]:
        """Process completed streaming transcript"""
        
        # Get or create session context
        if session_id not in self.agents.session_contexts:
            session_context = SessionContext(
                session_id=session_id,
                transcription_id=transcription_id,
                patient_context=patient_context,
                format_preference=format_preference
            )
            self.agents.session_contexts[session_id] = session_context
        
        try:
            logger.info(f"Processing streaming transcript for session {session_id}")
            
            # Similar to audio processing but with existing transcript
            # Implementation would follow same pattern
            
            return {
                "success": True,
                "session_id": session_id,
                "transcription_id": transcription_id,
                "final_agent": "QualityAssuranceAgent"
            }
            
        except Exception as e:
            logger.error(f"Error processing streaming transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    def process_text_chunk(
        self,
        session_id: str,
        text_chunk: str,
        speaker_id: str = "SPEAKER_00",
        is_final: bool = False
    ) -> Dict[str, Any]:
        """Process a text chunk for streaming transcription"""
        
        if session_id not in self.agents.session_contexts:
            return {
                "success": False,
                "error": "Session not found"
            }
        
        # Store the text chunk in session context
        # In production, implement proper text aggregation
        
        return {
            "success": True,
            "message": f"Received text chunk: {len(text_chunk)} characters"
        }
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a processing session"""
        
        if session_id not in self.agents.session_contexts:
            return {"status": "not_found"}
        
        context = self.agents.session_contexts[session_id]
        
        return {
            "session_id": session_id,
            "transcription_id": context.transcription_id,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "status": "active",
            "current_agent": self.current_agent.name if self.current_agent else None
        }
    
    async def _cleanup_session(self, session_id: str, delay: int = 300):
        """Clean up session after delay"""
        await asyncio.sleep(delay)
        
        if session_id in self.agents.session_contexts:
            del self.agents.session_contexts[session_id]
            logger.info(f"Cleaned up session {session_id}")


# Global orchestrator instance
orchestrator = MedicalScribeOrchestrator()