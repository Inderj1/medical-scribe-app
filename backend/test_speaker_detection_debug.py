#!/usr/bin/env python3
"""Debug test script for speaker detection"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import time
import logging
from app.services.speaker_diarization import RealtimeSpeakerDetector

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_test_audio(duration_seconds: float, sample_rate: int = 16000, 
                       speaker_id: int = 0) -> np.ndarray:
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


def test_speaker_change_debug():
    """Debug speaker change detection"""
    print("\n=== Debug Speaker Change Detection ===")
    
    detector = RealtimeSpeakerDetector({
        "sample_rate": 16000,
        "vad_aggressiveness": 2,
        "min_speech_duration_ms": 200,
        "speaker_change_threshold": 0.5,  # Lower threshold for testing
        "max_embeddings_per_speaker": 5  # Limit embeddings to see updates
    })
    
    # Generate speech from two different speakers
    print("\nGenerating test audio...")
    audio1 = generate_test_audio(2.0, speaker_id=0)  # Speaker 0 for 2 seconds
    silence = np.zeros(int(16000 * 0.5))  # 0.5 second silence
    audio2 = generate_test_audio(2.0, speaker_id=1)  # Speaker 1 for 2 seconds
    
    print(f"Audio1 stats: mean={np.mean(audio1):.4f}, std={np.std(audio1):.4f}, max={np.max(np.abs(audio1)):.4f}")
    print(f"Audio2 stats: mean={np.mean(audio2):.4f}, std={np.std(audio2):.4f}, max={np.max(np.abs(audio2)):.4f}")
    
    # Compute embeddings directly for comparison
    from app.services.speaker_diarization.utils import AudioProcessor
    
    # Get embeddings for each audio segment
    if hasattr(detector, '_prev_spectrum'):
        delattr(detector, '_prev_spectrum')  # Clear if exists
    embedding1 = detector._compute_embedding([audio1[:4800]])  # First 300ms
    
    if hasattr(detector, '_prev_spectrum'):
        delattr(detector, '_prev_spectrum')  # Clear if exists
    embedding2 = detector._compute_embedding([audio2[:4800]])  # First 300ms
    
    similarity = np.dot(embedding1, embedding2)
    print(f"\nDirect embedding similarity: {similarity:.4f}")
    print(f"Embedding1 first 10 values: {embedding1[:10]}")
    print(f"Embedding2 first 10 values: {embedding2[:10]}")
    
    # Concatenate and process
    full_audio = np.concatenate([audio1, silence, audio2])
    
    print(f"\nProcessing {len(full_audio) / 16000:.2f} seconds of audio...")
    
    # Process
    chunk_size = 480
    segments = []
    speaker_changes = 0
    last_speaker = None
    chunk_count = 0
    speech_chunks = 0
    
    for i in range(0, len(full_audio) - chunk_size, chunk_size):
        chunk = full_audio[i:i + chunk_size]
        chunk_count += 1
        
        # Check if chunk has speech
        is_speech = detector._is_speech(chunk)
        if is_speech:
            speech_chunks += 1
        
        time_pos = i / 16000
        
        # Log important transitions
        if chunk_count == 1:
            print(f"  Starting processing...")
        elif 2.0 < time_pos < 2.1:  # Around silence gap
            print(f"  At silence gap: {time_pos:.2f}s, speech={is_speech}")
        elif 2.5 < time_pos < 2.6:  # After silence, new speaker
            print(f"  After silence: {time_pos:.2f}s, speech={is_speech}, buffer_len={len(detector.speech_buffer)}")
        
        segment = detector.process_audio_chunk(chunk, 16000)
        
        if segment:
            segments.append(segment)
            print(f"  Segment returned: {segment.speaker_id} at {segment.start_time:.2f}s")
            if last_speaker and segment.speaker_id != last_speaker:
                speaker_changes += 1
                print(f"*** Speaker change detected: {last_speaker} -> {segment.speaker_id} at {segment.start_time:.2f}s")
            last_speaker = segment.speaker_id
    
    stats = detector.get_speaker_statistics()
    print(f"\nDetected {stats['total_speakers']} speakers")
    print(f"Speaker statistics: {stats}")
    print(f"Total segments: {len(segments)}")
    print(f"Speech chunks: {speech_chunks}/{chunk_count}")
    
    if stats["total_speakers"] < 2:
        print("\nDEBUG: Only one speaker detected. Checking speaker profiles...")
        for speaker_id, profile in detector.speaker_profiles.items():
            print(f"  {speaker_id}: {len(profile.voice_embeddings)} embeddings")
            if profile.voice_embeddings:
                avg_emb = np.mean(profile.voice_embeddings, axis=0)
                print(f"    Avg embedding first 10: {avg_emb[:10]}")


if __name__ == "__main__":
    test_speaker_change_debug()