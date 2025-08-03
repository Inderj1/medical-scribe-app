"""Main orchestrator for medical scribe workflow using OpenAI Agents SDK"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from agents import run_sync, run_async, RunConfig
from agents.models import LLMModel
from agents.extensions import handoff_filters

from app.agents_v2.base_agents import medical_scribe_agents
from app.agents_v2.models import SessionContext, TranscriptionData
from app.core.config import settings
from app.core.sse_manager import sse_manager

logger = logging.getLogger(__name__)


class MedicalScribeOrchestrator:
    """Orchestrates the medical scribe workflow with OpenAI Agents SDK"""
    
    def __init__(self):
        self.agents = medical_scribe_agents
        self.default_config = RunConfig(
            model=LLMModel.GPT_4,
            handoff_input_filter=handoff_filters.remove_all_tools,
            tracing_enabled=settings.ENABLE_AGENT_TRACING if hasattr(settings, 'ENABLE_AGENT_TRACING') else True,
            max_turns=20,
            temperature=0.3
        )
    
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
            
            # Run the agent workflow starting with transcription
            result = await run_async(
                agent=self.agents.transcription_agent,
                messages=[{
                    "role": "user",
                    "content": f"Process the audio file at {audio_path} for medical transcription. "
                               f"Format preference is {format_preference}."
                }],
                config=self.default_config,
                session_data=session_data
            )
            
            # Extract final results
            final_agent = result.agent.name if result.agent else "unknown"
            final_message = result.messages[-1].content if result.messages else ""
            
            # Send completion event
            await sse_manager.publish(
                f"transcription_{transcription_id}",
                {
                    "type": "processing_complete",
                    "data": {
                        "final_agent": final_agent,
                        "message": "Processing complete"
                    }
                }
            )
            
            logger.info(f"Completed audio processing for transcription {transcription_id}")
            
            return {
                "success": True,
                "transcription_id": transcription_id,
                "session_id": session_id,
                "final_agent": final_agent,
                "clinical_note": final_message,
                "trace": result.trace if self.default_config.tracing_enabled else None
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
            
            # Prepare session data
            session_data = {
                "session_id": session_id,
                "transcription_id": transcription_id,
                "format_preference": format_preference,
                "patient_context": patient_context
            }
            
            # Run the agent workflow
            result = await run_async(
                agent=self.agents.transcription_agent,
                messages=[{
                    "role": "user",
                    "content": f"Complete the transcription for session {session_id} and proceed with clinical analysis. "
                               f"Format preference is {format_preference}."
                }],
                config=self.default_config,
                session_data=session_data
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "transcription_id": transcription_id,
                "final_agent": result.agent.name if result.agent else "unknown"
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
        
        # This is now handled directly by the agent tools
        # The actual processing happens when we call the agents
        
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
            "status": "active"
        }
    
    async def _cleanup_session(self, session_id: str, delay: int = 300):
        """Clean up session after delay"""
        await asyncio.sleep(delay)
        
        if session_id in self.agents.session_contexts:
            del self.agents.session_contexts[session_id]
            logger.info(f"Cleaned up session {session_id}")


# Global orchestrator instance
orchestrator = MedicalScribeOrchestrator()