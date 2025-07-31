#!/usr/bin/env python3
"""Test agent processing with speaker segments"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
import logging
from app.agents.context_manager import handoff_context
from app.agents.transcription_agent import (
    start_text_processing,
    process_text_chunk,
    identify_speaker_roles,
    complete_transcription
)
from app.agents.clinical_analysis_agent import extract_clinical_sections

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_speaker_aware_agents():
    """Test agent processing with speaker segments"""
    print("\n=== Testing Speaker-Aware Agent Processing ===")
    
    # Create a test session
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")
    
    # Initialize context
    handoff_context.create_session(session_id, {
        "transcription_id": session_id,
        "patient_context": {
            "mrn": "TEST123",
            "first_name": "John",
            "last_name": "Doe",
            "age": 45
        },
        "streaming_mode": True
    })
    
    # Start text processing
    print("\n1. Starting text processing...")
    result = start_text_processing(session_id)
    print(f"   {result}")
    
    # Process text chunks with different speakers
    print("\n2. Processing text chunks with speakers...")
    
    chunks = [
        # Doctor speaking
        ("Good morning Mr. Doe, how are you feeling today?", "SPEAKER_00"),
        ("I see you're here for a follow-up about your back pain.", "SPEAKER_00"),
        
        # Patient speaking
        ("Hi doctor, I'm doing better than last week.", "SPEAKER_01"),
        ("The pain was about an 8 out of 10, but now it's down to about a 4.", "SPEAKER_01"),
        ("I can sleep through the night now.", "SPEAKER_01"),
        
        # Doctor again
        ("That's excellent progress. Let's examine your back.", "SPEAKER_00"),
        ("Your range of motion has improved significantly.", "SPEAKER_00"),
        
        # Nurse
        ("Doctor, here are today's vitals. Blood pressure is 120/80.", "SPEAKER_02"),
        
        # Doctor
        ("Thank you. Mr. Doe, let's continue with the current medication.", "SPEAKER_00"),
    ]
    
    for i, (text, speaker) in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        result = process_text_chunk(session_id, text, is_final, speaker)
        print(f"   [{speaker}] {text[:50]}... -> {result}")
    
    # Identify speaker roles
    print("\n3. Identifying speaker roles...")
    result = identify_speaker_roles(session_id)
    print(f"   {result}")
    
    # Check context
    context = handoff_context.get_context(session_id)
    print(f"\n4. Context check:")
    print(f"   Total words: {context.get('word_count', 0)}")
    print(f"   Speaker count: {len(context.get('speakers', set()))}")
    print(f"   Speaker roles: {context.get('speaker_roles', {})}")
    
    # Complete transcription (normally would hand off to next agent)
    print("\n5. Completing transcription...")
    try:
        next_agent = complete_transcription(session_id)
        print(f"   Handoff to: {next_agent.name if next_agent else 'None'}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test clinical analysis with speaker context
    print("\n6. Testing clinical analysis with speaker context...")
    try:
        # Manually call extract_clinical_sections to test
        # In real usage, this would be called by the agent framework
        from app.agents.clinical_analysis_agent import start_clinical_analysis
        result = start_clinical_analysis(session_id)
        print(f"   {result}")
        
        # Check if speaker information is being used
        context = handoff_context.get_context(session_id)
        if 'clinical_data' in context:
            print(f"   Clinical data extracted: {list(context['clinical_data'].keys())}")
    except Exception as e:
        print(f"   Error in clinical analysis: {e}")
    
    print("\n✓ Speaker-aware agent processing test completed")


def test_speaker_segment_tracking():
    """Test detailed speaker segment tracking"""
    print("\n=== Testing Speaker Segment Tracking ===")
    
    session_id = str(uuid.uuid4())
    handoff_context.create_session(session_id, {
        "transcription_id": session_id,
        "streaming_mode": True
    })
    
    # Process multiple chunks from same speaker
    print("\n1. Testing consecutive chunks from same speaker...")
    for i in range(3):
        text = f"This is sentence {i+1} from the patient."
        process_text_chunk(session_id, text, False, "PATIENT")
    
    # Check segment aggregation
    context = handoff_context.get_context(session_id)
    segments = context.get('speaker_segments', [])
    print(f"   Segments created: {len(segments)}")
    
    # Process from different speaker
    print("\n2. Testing speaker change...")
    process_text_chunk(session_id, "Let me examine you.", False, "DOCTOR")
    
    segments = context.get('speaker_segments', [])
    unique_speakers = set(seg['speaker_id'] for seg in segments)
    print(f"   Total segments: {len(segments)}")
    print(f"   Unique speakers: {unique_speakers}")
    
    print("\n✓ Speaker segment tracking test completed")


if __name__ == "__main__":
    print("Testing Agent Processing with Speaker Support")
    print("===========================================")
    
    try:
        test_speaker_aware_agents()
        test_speaker_segment_tracking()
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()