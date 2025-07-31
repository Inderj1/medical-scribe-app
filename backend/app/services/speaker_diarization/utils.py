"""Utilities for speaker diarization"""
import numpy as np
from typing import Tuple, List, Optional
import struct
import logging
from scipy.signal import butter, filtfilt
import io

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Utilities for audio processing"""
    
    @staticmethod
    def bytes_to_numpy(audio_bytes: bytes, sample_width: int = 2) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        if sample_width == 2:
            dtype = np.int16
            fmt = 'h'
        elif sample_width == 4:
            dtype = np.int32
            fmt = 'i'
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
        
        # Unpack audio bytes
        audio_data = struct.unpack(f"{len(audio_bytes) // sample_width}{fmt}", audio_bytes)
        return np.array(audio_data, dtype=dtype)
    
    @staticmethod
    def normalize_audio(audio: np.ndarray) -> np.ndarray:
        """Normalize audio to [-1, 1] range"""
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        elif audio.dtype != np.float32 and audio.dtype != np.float64:
            audio = audio.astype(np.float32)
        
        # Ensure values are in [-1, 1]
        audio = np.clip(audio, -1.0, 1.0)
        return audio
    
    @staticmethod
    def apply_bandpass_filter(audio: np.ndarray, sample_rate: int, 
                            low_freq: int = 80, high_freq: int = 3000) -> np.ndarray:
        """Apply bandpass filter to focus on human speech frequencies"""
        nyquist = sample_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # Design butterworth bandpass filter
        b, a = butter(4, [low, high], btype='band')
        filtered = filtfilt(b, a, audio)
        return filtered
    
    @staticmethod
    def compute_energy(audio: np.ndarray, frame_size: int = 480) -> float:
        """Compute energy of audio signal"""
        if len(audio) < frame_size:
            # Pad if necessary
            audio = np.pad(audio, (0, frame_size - len(audio)), mode='constant')
        
        # Take central frame
        start = (len(audio) - frame_size) // 2
        frame = audio[start:start + frame_size]
        
        # Compute RMS energy
        energy = np.sqrt(np.mean(frame ** 2))
        return energy
    
    @staticmethod
    def split_into_frames(audio: np.ndarray, frame_size: int, hop_size: int) -> List[np.ndarray]:
        """Split audio into overlapping frames"""
        frames = []
        for i in range(0, len(audio) - frame_size + 1, hop_size):
            frames.append(audio[i:i + frame_size])
        return frames


class SpeakerEmbedding:
    """Manage speaker embeddings and similarity computation"""
    
    def __init__(self, embedding_size: int = 64):
        self.embedding_size = embedding_size
    
    @staticmethod
    def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1_norm = embedding1 / norm1
        embedding2_norm = embedding2 / norm2
        
        # Compute cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)
        return float(similarity)
    
    @staticmethod
    def compute_average_embedding(embeddings: List[np.ndarray]) -> np.ndarray:
        """Compute average of multiple embeddings"""
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        avg_embedding = np.mean(embeddings, axis=0)
        # Normalize
        norm = np.linalg.norm(avg_embedding)
        if norm > 0:
            avg_embedding = avg_embedding / norm
        
        return avg_embedding
    
    def create_dummy_embedding(self, speaker_id: str) -> np.ndarray:
        """Create a dummy embedding for testing (replace with real model later)"""
        # For testing: create deterministic embeddings based on speaker_id
        np.random.seed(hash(speaker_id) % 2**32)
        embedding = np.random.randn(self.embedding_size)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding


class VoiceActivityDetector:
    """Simple voice activity detection"""
    
    def __init__(self, energy_threshold: float = 0.01, 
                 zero_crossing_threshold: int = 50):
        self.energy_threshold = energy_threshold
        self.zero_crossing_threshold = zero_crossing_threshold
        self.speech_buffer = []
        self.is_speaking = False
        
    def detect_speech(self, audio_frame: np.ndarray) -> Tuple[bool, float]:
        """Detect if frame contains speech"""
        # Compute energy
        energy = AudioProcessor.compute_energy(audio_frame)
        
        # Compute zero crossing rate
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_frame))) > 0) / 2
        
        # Simple VAD logic
        is_speech = (energy > self.energy_threshold and 
                    zero_crossings > self.zero_crossing_threshold)
        
        confidence = min(1.0, energy / (self.energy_threshold * 10))
        
        return is_speech, confidence