"""Base classes for speaker diarization"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """Represents a segment of speech from a specific speaker"""
    speaker_id: str
    start_time: float
    end_time: float
    text: Optional[str] = None
    confidence: float = 1.0
    embedding: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "speaker_id": self.speaker_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "confidence": self.confidence
        }


@dataclass
class SpeakerProfile:
    """Profile for a detected speaker"""
    speaker_id: str
    speaker_label: str  # SPEAKER_00, SPEAKER_01, etc.
    assigned_role: Optional[str] = None  # Doctor, Patient, Other
    voice_embeddings: List[np.ndarray] = None
    confidence_score: float = 0.0
    first_detected_at: float = 0.0
    
    def __post_init__(self):
        if self.voice_embeddings is None:
            self.voice_embeddings = []


class SpeakerDiarizationBase(ABC):
    """Abstract base class for speaker diarization implementations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.speaker_profiles: Dict[str, SpeakerProfile] = {}
        self.current_speaker: Optional[str] = None
        self.last_speech_time: float = 0.0
        
    @abstractmethod
    def process_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> Optional[SpeakerSegment]:
        """Process an audio chunk and return speaker information"""
        pass
    
    @abstractmethod
    def detect_speaker_change(self, audio_chunk: np.ndarray) -> bool:
        """Detect if the speaker has changed"""
        pass
    
    @abstractmethod
    def identify_speaker(self, audio_chunk: np.ndarray) -> str:
        """Identify which speaker is talking"""
        pass
    
    def add_speaker_profile(self, speaker_id: str, embedding: np.ndarray) -> None:
        """Add or update a speaker profile"""
        if speaker_id not in self.speaker_profiles:
            label = f"SPEAKER_{len(self.speaker_profiles):02d}"
            self.speaker_profiles[speaker_id] = SpeakerProfile(
                speaker_id=speaker_id,
                speaker_label=label,
                first_detected_at=self.last_speech_time
            )
        
        profile = self.speaker_profiles[speaker_id]
        profile.voice_embeddings.append(embedding)
        
        # Keep only the last N embeddings to manage memory
        max_embeddings = self.config.get("max_embeddings_per_speaker", 50)
        if len(profile.voice_embeddings) > max_embeddings:
            profile.voice_embeddings = profile.voice_embeddings[-max_embeddings:]
    
    def assign_speaker_role(self, speaker_id: str, role: str) -> None:
        """Assign a role (Doctor/Patient/Other) to a speaker"""
        if speaker_id in self.speaker_profiles:
            self.speaker_profiles[speaker_id].assigned_role = role
            logger.info(f"Assigned role '{role}' to speaker {speaker_id}")
    
    def get_speaker_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected speakers"""
        stats = {
            "total_speakers": len(self.speaker_profiles),
            "speakers": {}
        }
        
        for speaker_id, profile in self.speaker_profiles.items():
            stats["speakers"][speaker_id] = {
                "label": profile.speaker_label,
                "role": profile.assigned_role,
                "confidence": profile.confidence_score,
                "embedding_count": len(profile.voice_embeddings)
            }
        
        return stats
    
    def reset(self) -> None:
        """Reset the diarization state"""
        self.speaker_profiles.clear()
        self.current_speaker = None
        self.last_speech_time = 0.0
        logger.info("Speaker diarization state reset")