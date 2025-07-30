"""Transcription Agent for processing text input"""
import os
import logging
from typing import Dict, Any, Optional
from swarm import Agent
import asyncio

from app.core.config import settings
from app.core.sse_manager import sse_manager
from app.agents.context_manager import handoff_context

logger = logging.getLogger(__name__)


def start_text_processing(session_id: str, initial_text: str = "") -> str:
    """Start processing text input for a session"""
    logger.info(f"Starting text processing for session {session_id}")
    
    # Update context
    handoff_context.update_context(session_id, {
        "transcription_mode": "streaming_text",
        "transcription_status": "started",
        "transcript": initial_text,
        "word_count": len(initial_text.split()) if initial_text else 0
    })
    
    return f"Started text processing for session {session_id}"


def process_text_chunk(session_id: str, text_chunk: str, is_final: bool = False) -> str:
    """Process a chunk of transcribed text"""
    try:
        # Get existing transcript
        existing_transcript = handoff_context.get_from_context(
            session_id, "transcript", ""
        )
        
        # Append new text
        if existing_transcript:
            full_transcript = existing_transcript + " " + text_chunk.strip()
        else:
            full_transcript = text_chunk.strip()
        
        # Update context
        word_count = len(full_transcript.split())
        handoff_context.update_context(session_id, {
            "transcript": full_transcript,
            "word_count": word_count,
            "last_chunk": text_chunk,
            "is_final_chunk": is_final
        })
        
        # Send SSE update
        transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
        if transcription_id:
            asyncio.create_task(
                sse_manager.publish(
                    f"transcription:{transcription_id}",
                    {
                        "type": "transcription_update",
                        "data": {
                            "chunk": text_chunk,
                            "total_transcript": full_transcript,
                            "word_count": word_count,
                            "is_final": is_final
                        }
                    }
                )
            )
        
        return f"Processed text chunk: {len(text_chunk)} characters, total: {word_count} words"
        
    except Exception as e:
        logger.error(f"Error processing text chunk: {str(e)}")
        return f"Error processing text chunk: {str(e)}"


def analyze_partial_transcript(session_id: str) -> str:
    """Analyze partial transcript for early insights"""
    try:
        transcript = handoff_context.get_from_context(session_id, "transcript", "")
        word_count = handoff_context.get_from_context(session_id, "word_count", 0)
        
        if word_count < 30:
            return "Not enough text for analysis yet"
        
        # Mark sections that might be forming
        sections_identified = []
        
        # Simple heuristic analysis
        lower_transcript = transcript.lower()
        if "chief complaint" in lower_transcript or "presents with" in lower_transcript:
            sections_identified.append("chief_complaint")
        if "history" in lower_transcript or "past medical" in lower_transcript:
            sections_identified.append("history")
        if "exam" in lower_transcript or "vital" in lower_transcript:
            sections_identified.append("examination")
        if "assessment" in lower_transcript or "diagnosis" in lower_transcript:
            sections_identified.append("assessment")
        if "plan" in lower_transcript or "prescrib" in lower_transcript:
            sections_identified.append("plan")
        
        handoff_context.update_context(session_id, {
            "partial_sections_identified": sections_identified,
            "partial_analysis_complete": True
        })
        
        return f"Identified potential sections: {', '.join(sections_identified)}"
        
    except Exception as e:
        logger.error(f"Error in partial analysis: {str(e)}")
        return f"Error in partial analysis: {str(e)}"


def complete_transcription(session_id: str) -> Agent:
    """Complete the transcription and hand off to clinical analysis"""
    try:
        transcript = handoff_context.get_from_context(session_id, "transcript", "")
        word_count = handoff_context.get_from_context(session_id, "word_count", 0)
        
        if not transcript:
            raise ValueError("No transcript found in context")
        
        # Update final status
        handoff_context.update_context(session_id, {
            "transcription_status": "completed",
            "final_word_count": word_count,
            "streaming_mode": handoff_context.get_from_context(session_id, "streaming_mode", False)
        })
        
        logger.info(f"Completed transcription for session {session_id}: {word_count} words")
        
        # Send completion event
        transcription_id = handoff_context.get_from_context(session_id, "transcription_id")
        if transcription_id:
            asyncio.create_task(
                sse_manager.publish(
                    f"transcription:{transcription_id}",
                    {
                        "type": "transcription_complete", 
                        "data": {
                            "transcript": transcript,
                            "word_count": word_count
                        }
                    }
                )
            )
        
        # Hand off to clinical analysis
        return clinical_analysis_agent
        
    except Exception as e:
        logger.error(f"Error completing transcription: {str(e)}")
        handoff_context.update_context(session_id, {
            "transcription_status": "failed",
            "error": str(e)
        })
        raise


# Create the transcription agent
transcription_agent = Agent(
    name="TranscriptionAgent",
    instructions="""You are a medical transcription specialist processing real-time text input.
    
Your responsibilities:
1. Receive streaming text input from speech recognition
2. Aggregate text chunks into a complete transcript
3. Perform partial analysis to identify emerging sections
4. Maintain accurate word count and progress tracking
5. Send real-time updates via SSE
6. Hand off completed transcripts to clinical analysis

Available functions:
- start_text_processing(session_id, initial_text) - Initialize text processing
- process_text_chunk(session_id, text_chunk, is_final) - Process incoming text
- analyze_partial_transcript(session_id) - Analyze partial transcript
- complete_transcription(session_id) - Complete and hand off to next agent

Always ensure accurate text aggregation and proper handoff to the clinical analysis agent.
""",
    functions=[
        start_text_processing,
        process_text_chunk,
        analyze_partial_transcript,
        complete_transcription
    ]
)


# Import at the bottom to avoid circular import
from app.agents.clinical_analysis_agent import clinical_analysis_agent