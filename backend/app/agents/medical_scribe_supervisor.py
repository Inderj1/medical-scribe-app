"""Medical Scribe Supervisor Agent for orchestration"""
import logging
import asyncio
from typing import Dict, Any, Optional
import uuid
from swarm import Swarm, Agent
from openai import OpenAI

from app.agents.context_manager import handoff_context
from app.agents.transcription_agent import transcription_agent
from app.agents.clinical_analysis_agent import clinical_analysis_agent
from app.agents.note_structuring_agent import note_structuring_agent
from app.agents.quality_assurance_agent import quality_assurance_agent
from app.core.config import settings

logger = logging.getLogger(__name__)


class MedicalScribeSupervisor:
    """Orchestrates the medical scribe agent workflow"""
    
    def __init__(self):
        # Initialize OpenAI client with API key from settings
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.swarm = Swarm(client=client)
        self.supervisor_agent = self._create_supervisor_agent()
        
    def _create_supervisor_agent(self) -> Agent:
        """Create the supervisor agent"""
        return Agent(
            name="MedicalScribeSupervisor",
            instructions="""You are the medical scribe supervisor orchestrating the documentation workflow.
            
Your workflow:
1. Start with TranscriptionAgent for audio processing
2. Hand off to ClinicalAnalysisAgent for medical content extraction
3. Hand off to NoteStructuringAgent for formatting
4. Hand off to QualityAssuranceAgent for validation
5. Monitor progress and handle any errors

Guide the conversation to ensure smooth handoffs between agents.
Always start by asking which agent to begin with based on the task.
""",
            functions=[]
        )
    
    def process_audio(self, session_id: str) -> Dict[str, Any]:
        """Process audio through agent pipeline (synchronous for Swarm)"""
        
        try:
            logger.info(f"Starting agent processing for session {session_id}")
            
            # Get initial context
            context = handoff_context.get_context(session_id)
            if not context:
                raise ValueError(f"Session {session_id} not found")
            
            # Start with transcription agent
            messages = [
                {
                    "role": "user",
                    "content": f"Process the audio file for session {session_id}"
                }
            ]
            
            # Run the swarm with transcription agent as starting point
            response = self.swarm.run(
                agent=transcription_agent,
                messages=messages,
                context_variables={"session_id": session_id},
                max_turns=20,
                debug=False
            )
            
            # Get final context
            final_context = handoff_context.get_context(session_id)
            
            # Check for errors
            if final_context.get("error"):
                logger.error(f"Agent processing error: {final_context['error']}")
                return {"error": final_context["error"]}
            
            logger.info(f"Completed agent processing for session {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "final_agent": response.agent.name if response.agent else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Error in process_audio: {str(e)}")
            handoff_context.update_context(session_id, {"error": str(e)})
            raise
    
    def _process_streaming_transcript_sync(self, session_id: str) -> Dict[str, Any]:
        """Process streaming transcript through agent pipeline (synchronous for Swarm)"""
        
        try:
            logger.info(f"Starting streaming transcript processing for session {session_id}")
            
            # Get context
            context = handoff_context.get_context(session_id)
            if not context:
                raise ValueError(f"Session {session_id} not found")
            
            # Start with transcription agent for text processing
            messages = [
                {
                    "role": "user",
                    "content": f"Complete the transcription for session {session_id} and proceed with clinical analysis"
                }
            ]
            
            # Run the swarm
            response = self.swarm.run(
                agent=transcription_agent,
                messages=messages,
                context_variables={"session_id": session_id},
                max_turns=20,
                debug=False
            )
            
            # Get final context
            final_context = handoff_context.get_context(session_id)
            
            # Check for errors
            if final_context.get("error"):
                logger.error(f"Streaming processing error: {final_context['error']}")
                return {"error": final_context["error"]}
            
            logger.info(f"Completed streaming processing for session {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "final_agent": response.agent.name if response.agent else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Error in process_streaming_transcript: {str(e)}")
            handoff_context.update_context(session_id, {"error": str(e)})
            raise
    
    async def process_streaming_transcript(self, session_id: str) -> Dict[str, Any]:
        """Async wrapper for streaming transcript processing"""
        return await asyncio.to_thread(self._process_streaming_transcript_sync, session_id)
    
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
        
        # Initialize context
        handoff_context.create_session(session_id, {
            "transcription_id": transcription_id,
            "audio_path": audio_path,
            "patient_context": patient_context,
            "format_preference": format_preference,
            "language": language,
            "encounter_date": patient_context.get("encounter_date", ""),
            "encounter_id": patient_context.get("encounter_id", "")
        })
        
        try:
            logger.info(f"Starting agent processing for transcription {transcription_id}")
            
            # Start with supervisor and initial message
            messages = [
                {
                    "role": "user",
                    "content": f"I need to process an audio file for medical transcription. "
                               f"Session ID: {session_id}, Audio path: {audio_path}. "
                               f"Please start with the transcription process."
                }
            ]
            
            # Run the swarm
            response = self.swarm.run(
                agent=self.supervisor_agent,
                messages=messages,
                context_variables={
                    "session_id": session_id,
                    "starting_agent": transcription_agent
                },
                max_turns=20,
                debug=True
            )
            
            # Get final results from context
            final_results = handoff_context.get_from_context(session_id, "final_results")
            
            if not final_results:
                # Build results from context if not already compiled
                final_results = {
                    "transcript": handoff_context.get_from_context(session_id, "transcript"),
                    "clinical_data": handoff_context.get_from_context(session_id, "clinical_data"),
                    "final_note": handoff_context.get_from_context(session_id, "final_note"),
                    "qa_report": handoff_context.get_from_context(session_id, "qa_report"),
                    "format_type": format_preference,
                    "session_id": session_id
                }
            
            logger.info(f"Completed agent processing for transcription {transcription_id}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in agent processing: {str(e)}")
            
            # Update context with error
            handoff_context.update_context(session_id, {
                "processing_status": "failed",
                "error": str(e)
            })
            
            raise
        
        finally:
            # Clean up context after processing
            # In production, might want to persist this for audit
            pass
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a processing session"""
        context = handoff_context.get_context(session_id)
        
        if not context:
            return {"status": "not_found"}
        
        return {
            "session_id": session_id,
            "transcription_status": context.get("transcription_status", "unknown"),
            "analysis_status": context.get("analysis_status", "unknown"),
            "structuring_status": context.get("structuring_status", "unknown"),
            "qa_status": context.get("qa_status", "unknown"),
            "processing_status": context.get("processing_status", "in_progress"),
            "has_transcript": bool(context.get("transcript")),
            "has_clinical_data": bool(context.get("clinical_data")),
            "has_final_note": bool(context.get("final_note")),
            "quality_score": context.get("qa_quality_score", 0)
        }


# Global supervisor instance
medical_scribe_supervisor = MedicalScribeSupervisor()