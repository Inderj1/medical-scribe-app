#!/usr/bin/env python3
"""
Integration test for multi-speaker functionality
Tests the core components without external dependencies
"""

import json
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.context_manager import handoff_context
from app.agents.transcription_agent import (
    start_text_processing,
    process_text_chunk, 
    identify_speaker_roles,
    complete_transcription
)


def test_speaker_attribution():
    """Test speaker attribution in transcription agent"""
    print("\n=== Testing Speaker Attribution ===")
    
    session_id = f"test_{int(time.time())}"
    
    # Start processing
    result = start_text_processing(session_id)
    print(f"Started: {result}")
    
    # Process chunks with different speakers
    test_segments = [
        ("Good morning, Mrs. Johnson. How are you feeling today?", "SPEAKER_01"),
        ("I'm doing much better, doctor. The pain has reduced.", "SPEAKER_02"),
        ("That's excellent to hear. Let's check your vitals.", "SPEAKER_01"),
        ("Blood pressure is 120 over 80, temperature is normal.", "SPEAKER_03"),
        ("Perfect. Continue with the current medication.", "SPEAKER_01"),
    ]
    
    for text, speaker_id in test_segments:
        result = process_text_chunk(session_id, text, is_final=False, speaker_id=speaker_id)
        print(f"Processed ({speaker_id}): {result}")
    
    # Identify roles
    result = identify_speaker_roles(session_id)
    print(f"Speaker roles: {result}")
    
    # Get results from context
    context = handoff_context.get_context(session_id)
    speaker_segments = context.get("speaker_segments", [])
    speaker_roles = context.get("speaker_roles", {})
    
    print(f"\nTotal segments: {len(speaker_segments)}")
    print(f"Speaker roles identified: {speaker_roles}")
    
    # Verify results
    unique_speakers = set(seg["speaker_id"] for seg in speaker_segments)
    print(f"Unique speakers: {unique_speakers}")
    
    success = (
        len(speaker_segments) == 5 and
        len(unique_speakers) == 3 and
        len(speaker_roles) > 0
    )
    
    return success


def test_sse_event_generation():
    """Test SSE event generation with speaker info"""
    print("\n=== Testing SSE Event Generation ===")
    
    session_id = f"test_sse_{int(time.time())}"
    
    # Initialize context with transcription ID
    handoff_context.update_context(session_id, {
        "transcription_id": "test_transcription_123"
    })
    
    # Start and process a chunk
    start_text_processing(session_id)
    process_text_chunk(
        session_id,
        "This is a test message from the doctor.",
        is_final=True,
        speaker_id="SPEAKER_01"
    )
    
    # Check for SSE event
    context = handoff_context.get_context(session_id)
    pending_event = context.get("pending_sse_event")
    
    if pending_event:
        print(f"SSE Event Type: {pending_event.get('type')}")
        data = pending_event.get('data', {})
        print(f"Speaker ID in event: {data.get('speaker_id')}")
        print(f"Speaker count: {data.get('speaker_count')}")
        print(f"Text: {data.get('chunk', '')[:50]}...")
        
        success = (
            data.get('speaker_id') == 'SPEAKER_01' and
            data.get('speaker_count', 0) > 0
        )
    else:
        print("No SSE event found")
        success = False
    
    return success


def test_transcript_aggregation():
    """Test that transcript is properly aggregated across speakers"""
    print("\n=== Testing Transcript Aggregation ===")
    
    session_id = f"test_agg_{int(time.time())}"
    
    start_text_processing(session_id)
    
    # Process multiple chunks
    chunks = [
        ("Hello, I'm Dr. Smith.", "SPEAKER_01"),
        ("Nice to meet you, doctor.", "SPEAKER_02"),
        ("How can I help you today?", "SPEAKER_01"),
        ("I've been having headaches.", "SPEAKER_02"),
    ]
    
    for text, speaker in chunks:
        process_text_chunk(session_id, text, speaker_id=speaker)
    
    # Get full transcript
    context = handoff_context.get_context(session_id)
    full_transcript = context.get("transcript", "")
    word_count = context.get("word_count", 0)
    
    print(f"Full transcript: {full_transcript}")
    print(f"Word count: {word_count}")
    
    # Check aggregation
    expected_text = "Hello, I'm Dr. Smith. Nice to meet you, doctor. How can I help you today? I've been having headaches."
    success = (
        full_transcript == expected_text and
        word_count == len(expected_text.split())
    )
    
    return success


def main():
    """Run all integration tests"""
    print("Multi-Speaker Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Speaker Attribution", test_speaker_attribution),
        ("SSE Event Generation", test_sse_event_generation),
        ("Transcript Aggregation", test_transcript_aggregation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n{test_name}: ✗ FAILED with error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())