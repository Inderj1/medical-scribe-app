"""Simplified Medical Transcription Agent for testing"""
import asyncio
import logging
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents import Agent, Runner, SQLiteSession, set_default_openai_key
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create simple agents without complex type annotations
transcription_agent = Agent(
    name="TranscriptionAgent",
    instructions="""You are a medical transcription specialist. 
    Process audio and return transcribed text."""
)

clinical_analysis_agent = Agent(
    name="ClinicalAnalysisAgent", 
    instructions="""You are a clinical analysis specialist.
    Analyze medical transcriptions and extract:
    - Chief complaint
    - Symptoms
    - Medications
    - Vital signs
    - Assessment and plan
    
    Return structured information."""
)

note_formatting_agent = Agent(
    name="NoteFormattingAgent",
    instructions="""You are a clinical note formatter.
    Format medical information into SOAP notes or other formats.
    
    SOAP format includes:
    - Subjective
    - Objective
    - Assessment
    - Plan"""
)

# Simple function to test the agents
async def test_simple_agents():
    # Set OpenAI API key
    set_default_openai_key(settings.OPENAI_API_KEY)
    """Test the simplified agent system"""
    session = SQLiteSession(":memory:")
    
    # Test transcription
    print("Testing transcription agent...")
    result = await Runner.run(
        transcription_agent,
        "Process this audio: Patient has headache for 3 days, blood pressure 140/90",
        session=session
    )
    print(f"Transcription: {result.final_output}")
    
    # Test analysis
    print("\nTesting clinical analysis...")
    result = await Runner.run(
        clinical_analysis_agent,
        f"Analyze: {result.final_output}",
        session=session
    )
    print(f"Analysis: {result.final_output}")
    
    # Test formatting
    print("\nTesting note formatting...")
    result = await Runner.run(
        note_formatting_agent,
        f"Format in SOAP: {result.final_output}",
        session=session
    )
    print(f"Formatted note: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(test_simple_agents())