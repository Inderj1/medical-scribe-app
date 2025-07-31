#!/usr/bin/env python3
"""Test script for real-time speaker detection"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import time
import logging
from app.services.speaker_diarization import RealtimeSpeakerDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_test_audio(duration_seconds: float, sample_rate: int = 16000, 
                       frequency: float = 440.0, speaker_id: int = 0) -> np.ndarray:
    """Generate test audio with different characteristics for different speakers"""
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    
    # Different frequency patterns for different speakers
    if speaker_id == 0:
        # Speaker 0: Lower voice (male-like) - around 120Hz fundamental
        base_freq = 120.0
        audio = 0.3 * np.sin(2 * np.pi * base_freq * t)
        audio += 0.2 * np.sin(2 * np.pi * (base_freq * 2) * t)  # 2nd harmonic
        audio += 0.15 * np.sin(2 * np.pi * (base_freq * 3) * t)  # 3rd harmonic
        audio += 0.1 * np.sin(2 * np.pi * (base_freq * 4) * t)   # 4th harmonic
        
        # Add formants typical of male voice
        audio += 0.05 * np.sin(2 * np.pi * 700 * t)   # F1
        audio += 0.05 * np.sin(2 * np.pi * 1220 * t)  # F2
    else:
        # Speaker 1: Higher voice (female-like) - around 220Hz fundamental
        base_freq = 220.0
        audio = 0.3 * np.sin(2 * np.pi * base_freq * t)
        audio += 0.25 * np.sin(2 * np.pi * (base_freq * 2) * t)  # 2nd harmonic
        audio += 0.2 * np.sin(2 * np.pi * (base_freq * 3) * t)   # 3rd harmonic
        audio += 0.15 * np.sin(2 * np.pi * (base_freq * 4) * t)  # 4th harmonic
        
        # Add formants typical of female voice
        audio += 0.05 * np.sin(2 * np.pi * 860 * t)   # F1
        audio += 0.05 * np.sin(2 * np.pi * 2050 * t)  # F2
    
    # Add some colored noise (different for each speaker)
    np.random.seed(speaker_id)
    noise = np.random.normal(0, 0.01, len(audio))
    # Apply different filtering to noise for each speaker
    if speaker_id == 0:
        # Low-pass filter for male voice
        for i in range(1, len(noise)):
            noise[i] = 0.7 * noise[i] + 0.3 * noise[i-1]
    else:
        # Less filtering for female voice
        for i in range(1, len(noise)):
            noise[i] = 0.9 * noise[i] + 0.1 * noise[i-1]
    
    audio += noise
    
    # Add amplitude variation (different patterns for each speaker)
    if speaker_id == 0:
        envelope = 0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t)
    else:
        envelope = 0.7 + 0.3 * np.sin(2 * np.pi * 0.5 * t + np.pi/4)
    
    audio *= envelope
    
    # Ensure audio is in proper range
    audio = np.clip(audio, -1.0, 1.0)
    
    return audio.astype(np.float32)


def test_single_speaker():
    """Test with single speaker"""
    print("\n=== Testing Single Speaker Detection ===")
    
    detector = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "vad_aggressiveness": 2,
        "min_speech_duration_ms": 200
    })
    
    # Generate 3 seconds of speech from one speaker
    audio = generate_test_audio(3.0, speaker_id=0)
    
    # Process in chunks (simulating real-time)
    chunk_size = 480  # 30ms at 16kHz
    segments = []
    
    for i in range(0, len(audio) - chunk_size, chunk_size):
        chunk = audio[i:i + chunk_size]
        segment = detector.process_audio_chunk(chunk, 16000)
        
        if segment:
            segments.append(segment)
            print(f"Speaker segment detected: {segment.speaker_id} "
                  f"({segment.start_time:.2f}s - {segment.end_time:.2f}s)")
    
    # Get statistics
    stats = detector.get_speaker_statistics()
    print(f"\nSpeaker statistics: {stats}")
    
    perf_stats = detector.get_performance_stats()
    print(f"Performance: Avg processing time: {perf_stats['avg_processing_time_ms']:.2f}ms")
    
    assert stats["total_speakers"] >= 1, "Should detect at least one speaker"
    print("✓ Single speaker test passed")


def test_speaker_change():
    """Test speaker change detection"""
    print("\n=== Testing Speaker Change Detection ===")
    
    detector = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "vad_aggressiveness": 2,
        "min_speech_duration_ms": 200,
        "speaker_change_threshold": 0.65  # Match the updated default
    })
    
    # Generate speech from two different speakers
    audio1 = generate_test_audio(2.0, speaker_id=0)  # Speaker 0 for 2 seconds
    silence = np.zeros(int(16000 * 0.5))  # 0.5 second silence
    audio2 = generate_test_audio(2.0, speaker_id=1)  # Speaker 1 for 2 seconds
    
    # Concatenate
    full_audio = np.concatenate([audio1, silence, audio2])
    
    # Process
    chunk_size = 480
    segments = []
    speaker_changes = 0
    last_speaker = None
    speaker_timeline = []
    
    for i in range(0, len(full_audio) - chunk_size, chunk_size):
        chunk = full_audio[i:i + chunk_size]
        segment = detector.process_audio_chunk(chunk, 16000)
        
        if segment:
            segments.append(segment)
            if last_speaker and segment.speaker_id != last_speaker:
                speaker_changes += 1
                print(f"Speaker change detected: {last_speaker} -> {segment.speaker_id} at {segment.start_time:.2f}s")
            last_speaker = segment.speaker_id
            speaker_timeline.append((segment.start_time, segment.speaker_id))
    
    stats = detector.get_speaker_statistics()
    print(f"\nDetected {stats['total_speakers']} speakers")
    print(f"Speaker statistics: {stats}")
    print(f"Speaker changes: {speaker_changes}")
    
    # Print speaker timeline
    if speaker_timeline:
        print("\nSpeaker timeline:")
        for time, speaker in speaker_timeline[:10]:  # Show first 10 entries
            print(f"  {time:.2f}s: {speaker}")
        if len(speaker_timeline) > 10:
            print(f"  ... and {len(speaker_timeline) - 10} more entries")
    
    assert stats["total_speakers"] >= 2, "Should detect at least two speakers"
    print("✓ Speaker change test passed")


def test_realtime_performance():
    """Test real-time performance"""
    print("\n=== Testing Real-time Performance ===")
    
    detector = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "vad_aggressiveness": 3,
        "frame_duration_ms": 30
    })
    
    # Simulate real-time streaming
    chunk_duration_ms = 30
    chunk_size = int(16000 * chunk_duration_ms / 1000)
    
    # Process 10 seconds of audio in real-time
    start_time = time.time()
    chunks_processed = 0
    
    for i in range(333):  # ~10 seconds worth of 30ms chunks
        # Generate chunk
        audio_chunk = generate_test_audio(chunk_duration_ms / 1000, speaker_id=i % 2)
        
        # Process
        process_start = time.time()
        segment = detector.process_audio_chunk(audio_chunk, 16000)
        process_time = (time.time() - process_start) * 1000
        
        chunks_processed += 1
        
        # Check if processing is fast enough for real-time
        if process_time > chunk_duration_ms:
            logger.warning(f"Processing too slow: {process_time:.2f}ms > {chunk_duration_ms}ms")
    
    total_time = time.time() - start_time
    perf_stats = detector.get_performance_stats()
    
    print(f"\nProcessed {chunks_processed} chunks in {total_time:.2f}s")
    print(f"Average processing time: {perf_stats['avg_processing_time_ms']:.2f}ms")
    print(f"P95 processing time: {perf_stats['p95_processing_time_ms']:.2f}ms")
    print(f"Real-time factor: {10.0 / total_time:.2f}x")
    
    assert perf_stats['avg_processing_time_ms'] < chunk_duration_ms, \
        "Average processing time should be less than chunk duration for real-time"
    print("✓ Real-time performance test passed")


def test_silence_handling():
    """Test handling of silence and non-speech"""
    print("\n=== Testing Silence Handling ===")
    
    detector = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "vad_aggressiveness": 3
    })
    
    # Generate audio with speech and silence
    speech = generate_test_audio(1.0, speaker_id=0)
    silence = np.zeros(int(16000 * 2.0))  # 2 seconds silence
    
    full_audio = np.concatenate([silence, speech, silence])
    
    # Process
    chunk_size = 480
    speech_detected = False
    
    for i in range(0, len(full_audio) - chunk_size, chunk_size):
        chunk = full_audio[i:i + chunk_size]
        segment = detector.process_audio_chunk(chunk, 16000)
        
        if segment:
            speech_detected = True
            print(f"Speech detected at {segment.start_time:.2f}s")
    
    assert speech_detected, "Should detect speech in the middle"
    print("✓ Silence handling test passed")


if __name__ == "__main__":
    print("Testing Real-time Speaker Detection")
    print("===================================")
    
    try:
        test_single_speaker()
        test_speaker_change()
        test_realtime_performance()
        test_silence_handling()
        
        print("\n✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()