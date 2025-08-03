"""Test script for OpenAI Agents SDK implementation"""
import asyncio
import logging
from datetime import datetime
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress some verbose logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


async def test_agent_initialization():
    """Test that agents are properly initialized"""
    logger.info("Testing agent initialization...")
    
    try:
        from app.agents_v2.base_agents_simple import medical_scribe_agents
        
        # Check all agents exist
        assert hasattr(medical_scribe_agents, 'transcription_agent')
        assert hasattr(medical_scribe_agents, 'clinical_analysis_agent')
        assert hasattr(medical_scribe_agents, 'note_structuring_agent')
        assert hasattr(medical_scribe_agents, 'qa_agent')
        
        logger.info("✓ All agents initialized successfully")
        
        # Check handoffs
        assert len(medical_scribe_agents.transcription_agent.handoffs) > 0
        assert len(medical_scribe_agents.clinical_analysis_agent.handoffs) > 0
        assert len(medical_scribe_agents.note_structuring_agent.handoffs) > 0
        
        logger.info("✓ Agent handoffs configured")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {str(e)}")
        return False


async def test_orchestrator():
    """Test orchestrator functionality"""
    logger.info("Testing orchestrator...")
    
    try:
        from app.agents_v2.orchestrator import orchestrator
        
        # Test session management
        test_session_id = "test_session_123"
        test_transcription_id = "test_trans_123"
        
        # Create a test context
        from app.agents_v2.models import SessionContext
        
        test_context = SessionContext(
            session_id=test_session_id,
            transcription_id=test_transcription_id,
            patient_context={"test": "data"}
        )
        
        orchestrator.agents.session_contexts[test_session_id] = test_context
        
        # Get session status
        status = orchestrator.get_session_status(test_session_id)
        assert status["status"] != "not_found"
        
        logger.info("✓ Orchestrator session management working")
        
        # Clean up
        del orchestrator.agents.session_contexts[test_session_id]
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Orchestrator test failed: {str(e)}")
        return False


async def test_agent_tools():
    """Test individual agent tools"""
    logger.info("Testing agent tools...")
    
    try:
        from app.agents_v2.base_agents_simple import medical_scribe_agents
        
        # Create mock session data
        session_data = {"session_id": "test_123", "transcription_id": "trans_123"}
        
        # Test speaker role identification
        roles = await medical_scribe_agents.identify_speaker_roles(session_data)
        assert isinstance(roles, dict)
        assert len(roles) > 0
        
        logger.info("✓ Agent tools working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Agent tools test failed: {str(e)}")
        return False


async def test_data_models():
    """Test data model validation"""
    logger.info("Testing data models...")
    
    try:
        from app.agents_v2.models import (
            TranscriptionData, ClinicalData, StructuredNote, QAReport
        )
        
        # Test TranscriptionData
        trans_data = TranscriptionData(
            session_id="test_session",
            transcription_id="test_trans",
            transcript="Test medical transcript",
            speaker_segments=[],
            word_count=3
        )
        assert trans_data.word_count == 3
        
        # Test ClinicalData
        clinical_data = ClinicalData(
            session_id="test_session",
            transcription_id="test_trans",
            chief_complaint="Test complaint"
        )
        assert clinical_data.chief_complaint == "Test complaint"
        
        # Test StructuredNote
        note = StructuredNote(
            session_id="test_session",
            transcription_id="test_trans",
            note_content="Test SOAP note"
        )
        assert note.format_type == "soap"  # default value
        
        # Test QAReport
        qa_report = QAReport(
            session_id="test_session",
            transcription_id="test_trans",
            overall_score=0.85
        )
        assert qa_report.overall_score == 0.85
        assert qa_report.approved == False  # default
        
        logger.info("✓ All data models validated successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Data model test failed: {str(e)}")
        return False


async def test_simple_agent_flow():
    """Test a simple agent flow without actual API calls"""
    logger.info("Testing simple agent flow...")
    
    try:
        from app.agents_v2.base_agents_simple import medical_scribe_agents
        from app.agents_v2.models import ClinicalData, StructuredNote
        
        # Create session data
        session_data = {
            "session_id": "test_flow",
            "transcription_id": "test_trans"
        }
        
        # Test note formatting
        test_clinical_data = ClinicalData(
            session_id="test_flow",
            transcription_id="test_trans",
            chief_complaint="Patient reports headache",
            assessment="Likely tension headache",
            plan="Rest and OTC pain relief"
        )
        
        # Format as SOAP note
        note = await medical_scribe_agents.format_soap_note(session_data, test_clinical_data)
        
        assert isinstance(note, StructuredNote)
        assert "S (Subjective):" in note.note_content
        assert "Chief Complaint: Patient reports headache" in note.note_content
        assert note.format_type == "soap"
        
        logger.info("✓ Simple agent flow completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Simple agent flow failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all tests"""
    logger.info("Starting OpenAI Agents SDK implementation tests...\n")
    
    tests = [
        ("Agent Initialization", test_agent_initialization),
        ("Orchestrator", test_orchestrator),
        ("Agent Tools", test_agent_tools),
        ("Data Models", test_data_models),
        ("Simple Agent Flow", test_simple_agent_flow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {str(e)}")
            results.append((test_name, False))
        
        await asyncio.sleep(0.5)  # Brief pause between tests
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! The OpenAI Agents SDK implementation is working correctly.")
    else:
        logger.warning(f"\n⚠️  {total - passed} tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)