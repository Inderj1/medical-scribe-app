#!/usr/bin/env python3
"""
Quick test script to verify the agent-based system components
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def test_speaker_diarization():
    """Quick test of speaker diarization"""
    print("\n=== Testing Speaker Diarization ===")
    try:
        from app.services.speaker_diarization_agent import SpeakerDiarizationAgent
        
        agent = SpeakerDiarizationAgent()
        
        test_phrases = [
            ("Let me check your blood pressure", "Expected: DOCTOR"),
            ("I've been feeling dizzy lately", "Expected: PATIENT"),
            ("The medication is working well", "Expected: Ambiguous")
        ]
        
        for phrase, expected in test_phrases:
            result = await agent.identify_speaker(phrase)
            print(f"\nPhrase: '{phrase}'")
            print(f"{expected}")
            print(f"Result: {result.speaker} (confidence: {result.confidence:.2f})")
            
        print("\n✓ Speaker diarization test completed")
        return True
        
    except Exception as e:
        print(f"\n✗ Speaker diarization test failed: {e}")
        return False

async def test_section_agents():
    """Quick test of section agents"""
    print("\n=== Testing Section Agents ===")
    try:
        from app.services.openai_section_agents import OpenAISectionAgents
        
        agents = OpenAISectionAgents()
        
        # Test chief complaint processing
        result = await agents.process_section(
            section="chief_complaint",
            transcription="I've been having severe headaches for a week",
            speaker="PATIENT",
            format_preference="short"
        )
        
        print(f"\nSection: {result.section}")
        print(f"Content: {result.content[:100]}...")
        print(f"Formats available: {list(result.formatted_content.keys())}")
        print(f"Confidence: {result.confidence:.2f}")
        
        print("\n✓ Section agents test completed")
        return True
        
    except Exception as e:
        print(f"\n✗ Section agents test failed: {e}")
        return False

async def test_agent_orchestrator():
    """Quick test of agent orchestrator"""
    print("\n=== Testing Agent Orchestrator ===")
    try:
        from app.services.agent_orchestrator import AgentOrchestrator
        from app.services.enhanced_transcription_service import TranscriptionResult
        
        orchestrator = AgentOrchestrator()
        
        # Initialize encounter
        encounter_id = "test-encounter-quick"
        patient_id = "test-patient-001"
        await orchestrator.initialize_encounter(encounter_id, patient_id)
        
        # Create test transcription
        transcription = TranscriptionResult(
            id="test-trans-001",
            text="Patient complains of chest pain when breathing deeply",
            confidence=0.95,
            segments=[],
            processing_time=0.5,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Process transcription
        result = await orchestrator.process_transcription(
            transcription,
            encounter_id,
            "long"
        )
        
        print(f"\nSpeaker: {result.speaker_info.speaker}")
        print(f"Primary section: {result.routing_decision.primary_section}")
        print(f"Section updates: {len(result.section_updates)}")
        print(f"Requires resummary: {result.requires_resummary}")
        
        # End encounter
        summary = orchestrator.end_encounter(encounter_id)
        print(f"\nEncounter summary: {summary}")
        
        print("\n✓ Agent orchestrator test completed")
        return True
        
    except Exception as e:
        print(f"\n✗ Agent orchestrator test failed: {e}")
        return False

async def test_context_manager():
    """Quick test of context manager"""
    print("\n=== Testing Context Manager ===")
    try:
        from app.services.context_manager import ContextManager
        import time
        
        manager = ContextManager()
        
        # Add context
        encounter_id = "test-enc-ctx"
        manager.add_to_context(encounter_id, "Headache for 3 days", {"speaker": "PATIENT", "confidence": 0.9})
        manager.add_to_context(encounter_id, "Taking ibuprofen", {"speaker": "PATIENT", "confidence": 0.85})
        
        # Check if complete
        is_complete = manager.is_context_complete(encounter_id)
        print(f"\nContext complete immediately: {is_complete}")
        
        # Get conversation summary
        summary = manager.get_conversation_summary(encounter_id)
        print(f"Total utterances: {summary['total_utterances']}")
        print(f"Speakers: {dict(summary['speaker_counts'])}")
        
        print("\n✓ Context manager test completed")
        return True
        
    except Exception as e:
        print(f"\n✗ Context manager test failed: {e}")
        return False

async def main():
    """Run all quick tests"""
    print("=== Quick Test Suite for Agent-Based Medical Scribe ===")
    print(f"Started at: {datetime.now()}")
    
    tests = [
        test_speaker_diarization,
        test_section_agents,
        test_agent_orchestrator,
        test_context_manager
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(tests) - sum(results)}")
    
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)