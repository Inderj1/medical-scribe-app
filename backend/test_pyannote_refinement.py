#!/usr/bin/env python3
"""Test script for pyannote refinement service"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import logging
from app.services.speaker_diarization import (
    RealtimeSpeakerDetector, 
    PyannoteRefinementService,
    SpeakerSegment
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_multi_speaker_audio(sample_rate: int = 16000) -> np.ndarray:
    """Generate test audio with multiple speakers"""
    # Total duration: 10 seconds
    duration = 10.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    audio = np.zeros_like(t)
    
    # Speaker 1: 0-3 seconds (lower pitch)
    mask1 = (t >= 0) & (t < 3)
    audio[mask1] = 0.5 * np.sin(2 * np.pi * 150 * t[mask1])
    audio[mask1] += 0.3 * np.sin(2 * np.pi * 300 * t[mask1])
    
    # Silence: 3-3.5 seconds
    
    # Speaker 2: 3.5-6.5 seconds (higher pitch)
    mask2 = (t >= 3.5) & (t < 6.5)
    audio[mask2] = 0.5 * np.sin(2 * np.pi * 250 * t[mask2])
    audio[mask2] += 0.3 * np.sin(2 * np.pi * 500 * t[mask2])
    
    # Silence: 6.5-7 seconds
    
    # Speaker 1 again: 7-9 seconds
    mask3 = (t >= 7) & (t < 9)
    audio[mask3] = 0.5 * np.sin(2 * np.pi * 150 * t[mask3])
    audio[mask3] += 0.3 * np.sin(2 * np.pi * 300 * t[mask3])
    
    # Add some noise
    audio += 0.01 * np.random.randn(len(audio))
    
    return audio.astype(np.float32)


def test_refinement_service():
    """Test the pyannote refinement service"""
    print("\n=== Testing Pyannote Refinement Service ===")
    
    # Create refinement service
    refiner = PyannoteRefinementService({
        "min_speakers": 2,
        "max_speakers": 4
    })
    
    # Generate test audio
    print("\nGenerating test audio...")
    audio = generate_multi_speaker_audio()
    sample_rate = 16000
    duration = len(audio) / sample_rate
    print(f"Audio duration: {duration:.2f} seconds")
    
    # Create some initial segments (simulating real-time detection)
    initial_segments = [
        SpeakerSegment("speaker_0", 0.0, 2.8),
        SpeakerSegment("speaker_1", 3.6, 6.4),
        SpeakerSegment("speaker_0", 7.1, 8.9)
    ]
    
    print("\nInitial segments from real-time detection:")
    for seg in initial_segments:
        print(f"  {seg.speaker_id}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")
    
    # Refine diarization
    print("\nRunning refinement...")
    refined_segments = refiner.refine_diarization(audio, sample_rate, initial_segments)
    
    print(f"\nRefined segments: {len(refined_segments)}")
    for seg in refined_segments:
        print(f"  {seg.speaker_id}: {seg.start_time:.2f}s - {seg.end_time:.2f}s (confidence: {seg.confidence:.2f})")
    
    # Test merging close segments
    print("\nTesting segment merging...")
    merged_segments = refiner.merge_close_segments(refined_segments)
    print(f"Merged segments: {len(merged_segments)}")
    for seg in merged_segments:
        print(f"  {seg.speaker_id}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")
    
    # Verify results
    unique_speakers = set(seg.speaker_id for seg in refined_segments)
    print(f"\nUnique speakers detected: {len(unique_speakers)}")
    print(f"Speaker IDs: {sorted(unique_speakers)}")
    
    assert len(unique_speakers) >= 2, "Should detect at least 2 speakers"
    print("\n✓ Refinement test passed")


def test_real_time_to_refined_pipeline():
    """Test the complete pipeline from real-time to refined"""
    print("\n=== Testing Complete Pipeline ===")
    
    # Create both detectors
    realtime = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "min_speech_duration_ms": 200
    })
    
    refiner = PyannoteRefinementService({
        "min_speakers": 1,
        "max_speakers": 5
    })
    
    # Generate test audio
    audio = generate_multi_speaker_audio()
    sample_rate = 16000
    
    # First pass: Real-time detection
    print("\n1. Running real-time detection...")
    chunk_size = 480  # 30ms chunks
    realtime_segments = []
    
    for i in range(0, len(audio) - chunk_size, chunk_size):
        chunk = audio[i:i + chunk_size]
        segment = realtime.process_audio_chunk(chunk, sample_rate)
        if segment:
            realtime_segments.append(segment)
            print(f"  Real-time: {segment.speaker_id} at {segment.start_time:.2f}s")
    
    # Second pass: Refinement
    print("\n2. Running refinement...")
    refined_segments = refiner.refine_diarization(audio, sample_rate, realtime_segments)
    
    print(f"\nFinal results:")
    print(f"  Real-time segments: {len(realtime_segments)}")
    print(f"  Refined segments: {len(refined_segments)}")
    
    # Compare speakers
    realtime_speakers = set(seg.speaker_id for seg in realtime_segments)
    refined_speakers = set(seg.speaker_id for seg in refined_segments)
    
    print(f"  Real-time speakers: {sorted(realtime_speakers)}")
    print(f"  Refined speakers: {sorted(refined_speakers)}")
    
    print("\n✓ Pipeline test completed")


if __name__ == "__main__":
    print("Testing Pyannote Refinement Service")
    print("===================================")
    
    try:
        test_refinement_service()
        test_real_time_to_refined_pipeline()
        
        print("\n✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()