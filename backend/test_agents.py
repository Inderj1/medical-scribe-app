"""Test script for agent-based transcription system"""
import asyncio
import logging
from agents import Runner, Session
from app.agents.transcription_agent import (
    transcription_agent,
    clinical_analysis_agent,
    note_formatting_agent
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_system():
    """Test the agent system with a sample medical conversation"""
    
    print("🚀 Testing Medical Scribe Agent System")
    print("=" * 50)
    
    # Create a session
    session = Session()
    
    # Test 1: Start transcription session
    print("\n1️⃣ Testing transcription session start...")
    result = await Runner.run(
        transcription_agent,
        "Start transcription session for encounter ENC123 and patient PAT456",
        session=session
    )
    print(f"Result: {result.final_output}")
    
    # Test 2: Analyze sample medical text
    print("\n2️⃣ Testing clinical analysis...")
    sample_text = """
    Patient presents with severe headache for the past 3 days. 
    Blood pressure is 140/90. Temperature 98.6 degrees.
    Started on ibuprofen 400mg three times daily.
    Follow up in one week if symptoms persist.
    """
    
    result = await Runner.run(
        clinical_analysis_agent,
        f"Analyze this medical transcription: {sample_text}",
        session=session
    )
    print(f"Analysis: {result.final_output}")
    
    # Test 3: Format clinical note
    print("\n3️⃣ Testing note formatting...")
    analysis = {
        "chief_complaint": "Severe headache",
        "symptoms": ["headache for 3 days", "elevated blood pressure"],
        "vital_signs": "BP: 140/90, Temp: 98.6°F",
        "medications": ["Ibuprofen 400mg TID"],
        "plan": "Follow up in one week if symptoms persist"
    }
    
    # Test SOAP format
    result = await Runner.run(
        note_formatting_agent,
        f"Format this clinical data in SOAP format: {analysis}",
        session=session
    )
    print(f"\nSOAP Note:\n{result.final_output}")
    
    # Test 4: End session
    print("\n4️⃣ Testing session end...")
    result = await Runner.run(
        transcription_agent,
        "End the current transcription session",
        session=session
    )
    print(f"Result: {result.final_output}")
    
    print("\n✅ All tests completed!")


async def test_agent_handoff():
    """Test agent handoff functionality"""
    
    print("\n🔄 Testing Agent Handoff")
    print("=" * 50)
    
    session = Session()
    
    # Start with transcription agent and hand off to clinical analysis
    sample_transcription = "Patient has diabetes and takes metformin 500mg twice daily"
    
    result = await Runner.run(
        transcription_agent,
        f"I have this transcription that needs clinical analysis: {sample_transcription}. Please hand it off to the clinical analysis agent.",
        session=session
    )
    
    print(f"Handoff result: {result.final_output}")
    
    # The result should show the clinical analysis from the handoff
    print(f"Full conversation history: {len(session.messages)} messages")


async def main():
    """Run all tests"""
    try:
        await test_agent_system()
        await test_agent_handoff()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())