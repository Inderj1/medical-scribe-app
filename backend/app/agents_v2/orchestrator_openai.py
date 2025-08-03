"""Orchestrator for medical scribe workflow using OpenAI Agents SDK patterns"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from app.agents_v2.base_agents_openai import (
    medical_scribe_agents, Agent, RunContext, RunResult, HandoffInputData
)
from app.agents_v2.models import SessionContext, TranscriptionData
from app.core.config import settings
from app.core.sse_manager import sse_manager

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    """Configuration for agent execution"""
    model: str = "gpt-4"
    temperature: float = 0.3
    max_turns: int = 20
    tracing_enabled: bool = True
    handoff_input_filter: Optional[callable] = None
    guardrails: List[callable] = field(default_factory=list)


class AgentExecutor:
    """Executes agents with handoffs"""
    
    def __init__(self, config: RunConfig):
        self.config = config
        self.execution_trace = []
    
    async def execute_agent(self, agent: Agent, context: RunContext) -> Any:
        """Execute a single agent"""
        self.execution_trace.append({
            "agent": agent.name,
            "timestamp": datetime.utcnow().isoformat(),
            "turn": len(self.execution_trace) + 1
        })
        
        # Simulate agent processing based on agent type
        if agent.name == "TranscriptionAgent":
            # Process audio transcription
            if context.session_data.get("audio_path"):
                result = await agent.execute_tool(
                    "process_audio_file",
                    context,
                    audio_path=context.session_data["audio_path"]
                )
                return result
        
        elif agent.name == "ClinicalAnalysisAgent":
            # Extract clinical sections
            result = await agent.execute_tool("extract_clinical_sections", context)
            
            # Identify medical entities
            await agent.execute_tool("identify_medical_entities", context)
            
            # Enhance with EHR if available
            await agent.execute_tool("enhance_with_ehr", context)
            
            return {"status": "success", "message": "Clinical analysis complete"}
        
        elif agent.name == "NoteStructuringAgent":
            # Format based on preference
            format_pref = context.session_data.get("format_preference", "soap")
            
            if format_pref == "soap":
                result = await agent.execute_tool("format_soap_note", context)
            elif format_pref == "bullet":
                result = await agent.execute_tool("format_bullet_points", context)
            else:
                result = await agent.execute_tool("format_narrative", context)
            
            return {"status": "success", "message": f"Note formatted as {format_pref}"}
        
        elif agent.name == "QualityAssuranceAgent":
            # Validate note
            validation = await agent.execute_tool("validate_note", context)
            
            # Generate QA report
            qa_report = await agent.execute_tool("generate_qa_report", context)
            
            return {
                "status": "success",
                "message": "Quality assurance complete",
                "qa_report": qa_report
            }
        
        return {"status": "error", "message": f"Unknown agent: {agent.name}"}
    
    async def execute_handoff(self, current_agent: Agent, next_agent: Agent, 
                            context: RunContext, handoff_config) -> None:
        """Execute handoff between agents"""
        # Apply input filter if configured
        if handoff_config.input_filter:
            input_data = HandoffInputData(
                messages=context.messages,
                context=context.session_data
            )
            filtered_data = handoff_config.input_filter(input_data)
            context.messages = filtered_data.messages
        
        # Execute handoff callback if configured
        if handoff_config.on_handoff:
            handoff_config.on_handoff(context, input_data)
        
        logger.info(f"Handoff from {current_agent.name} to {next_agent.name}")
    
    async def run_agent_chain(self, start_agent: Agent, initial_context: RunContext) -> RunResult:
        """Run the agent chain with handoffs"""
        current_agent = start_agent
        context = initial_context
        turns = 0
        
        while current_agent and turns < self.config.max_turns:
            context.current_agent = current_agent
            
            # Execute current agent
            logger.info(f"Executing agent: {current_agent.name}")
            result = await self.execute_agent(current_agent, context)
            
            # Add result to messages
            context.messages.append({
                "role": "assistant",
                "content": str(result),
                "agent": current_agent.name
            })
            
            # Check for handoffs
            next_agent = None
            handoff_config = None
            
            if current_agent.handoffs:
                # For simplicity, take the first handoff
                # In production, this would be based on agent decision
                handoff_config = current_agent.handoffs[0]
                next_agent = handoff_config.agent
            
            if next_agent:
                await self.execute_handoff(current_agent, next_agent, context, handoff_config)
                current_agent = next_agent
            else:
                # No more handoffs, chain complete
                break
            
            turns += 1
        
        return RunResult(
            agent=current_agent,
            messages=context.messages,
            trace=self.execution_trace,
            session_data=context.session_data
        )


async def run_async(agent: Agent, messages: List[Dict[str, Any]], 
                   config: RunConfig, session_data: Dict[str, Any]) -> RunResult:
    """Run agent workflow asynchronously"""
    executor = AgentExecutor(config)
    context = RunContext(
        session_data=session_data,
        messages=messages,
        current_agent=agent
    )
    
    return await executor.run_agent_chain(agent, context)


def run_sync(agent: Agent, messages: List[Dict[str, Any]], 
             config: RunConfig, session_data: Dict[str, Any]) -> RunResult:
    """Run agent workflow synchronously"""
    return asyncio.run(run_async(agent, messages, config, session_data))


class MedicalScribeOrchestrator:
    """Orchestrates the medical scribe workflow with OpenAI Agents SDK patterns"""
    
    def __init__(self):
        self.agents = medical_scribe_agents
        self.default_config = RunConfig(
            model="gpt-4",
            temperature=0.3,
            max_turns=20,
            tracing_enabled=True
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
            qa_report = result.session_data.get("qa_report")
            structured_note = result.session_data.get("structured_note")
            
            # Send completion event
            await sse_manager.publish(
                f"transcription_{transcription_id}",
                {
                    "type": "processing_complete",
                    "data": {
                        "final_agent": final_agent,
                        "message": "Processing complete",
                        "qa_approved": qa_report.approved if qa_report else False
                    }
                }
            )
            
            logger.info(f"Completed audio processing for transcription {transcription_id}")
            
            return {
                "success": True,
                "transcription_id": transcription_id,
                "session_id": session_id,
                "final_agent": final_agent,
                "clinical_note": structured_note.note_content if structured_note else None,
                "qa_report": {
                    "overall_score": qa_report.overall_score if qa_report else 0,
                    "approved": qa_report.approved if qa_report else False,
                    "suggestions": qa_report.suggestions if qa_report else []
                } if qa_report else None,
                "trace": result.trace if self.default_config.tracing_enabled else None
            }
            
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}", exc_info=True)
            
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
        transcript: str,
        patient_context: Dict[str, Any],
        format_preference: str = "soap"
    ) -> Dict[str, Any]:
        """Process completed streaming transcript"""
        
        # Create or update session context
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
            
            # Create TranscriptionData for the transcript
            transcription_data = TranscriptionData(
                session_id=session_id,
                transcription_id=transcription_id,
                transcript=transcript,
                word_count=len(transcript.split()),
                speaker_segments=[],  # Would be populated from streaming data
                speaker_roles={"SPEAKER_00": "Healthcare Provider", "SPEAKER_01": "Patient"}
            )
            
            # Prepare session data
            session_data = {
                "session_id": session_id,
                "transcription_id": transcription_id,
                "format_preference": format_preference,
                "patient_context": patient_context,
                "transcription_data": transcription_data
            }
            
            # Start with clinical analysis since transcription is complete
            result = await run_async(
                agent=self.agents.clinical_analysis_agent,
                messages=[{
                    "role": "user",
                    "content": f"Analyze the completed transcript and proceed with clinical documentation. "
                               f"Format preference is {format_preference}."
                }],
                config=self.default_config,
                session_data=session_data
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "transcription_id": transcription_id,
                "final_agent": result.agent.name if result.agent else "unknown",
                "clinical_note": result.session_data.get("structured_note", {}).get("note_content")
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
                "error": "Session not found. Please initialize session first."
            }
        
        # In production, implement proper text aggregation and speaker tracking
        # For now, just acknowledge receipt
        
        return {
            "success": True,
            "message": f"Received text chunk: {len(text_chunk)} characters from {speaker_id}",
            "is_final": is_final
        }
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a processing session"""
        
        if session_id not in self.agents.session_contexts:
            return {"status": "not_found"}
        
        context = self.agents.session_contexts[session_id]
        
        # Check what data is available
        has_transcription = "transcription_data" in context.__dict__
        has_clinical = "clinical_data" in context.__dict__
        has_note = "structured_note" in context.__dict__
        has_qa = "qa_report" in context.__dict__
        
        # Determine current stage
        if has_qa:
            stage = "complete"
        elif has_note:
            stage = "quality_assurance"
        elif has_clinical:
            stage = "note_structuring"
        elif has_transcription:
            stage = "clinical_analysis"
        else:
            stage = "transcription"
        
        return {
            "session_id": session_id,
            "transcription_id": context.transcription_id,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "status": "active",
            "stage": stage,
            "has_transcription": has_transcription,
            "has_clinical_data": has_clinical,
            "has_structured_note": has_note,
            "has_qa_report": has_qa
        }
    
    async def _cleanup_session(self, session_id: str, delay: int = 300):
        """Clean up session after delay"""
        await asyncio.sleep(delay)
        
        if session_id in self.agents.session_contexts:
            del self.agents.session_contexts[session_id]
            logger.info(f"Cleaned up session {session_id}")


# Global orchestrator instance
orchestrator = MedicalScribeOrchestrator()