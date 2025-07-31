"""Pyannote-based speaker diarization refinement service"""
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
import tempfile
import soundfile as sf
import os

# Optional imports
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
try:
    from pyannote.audio import Pipeline
    from pyannote.audio.pipelines.speaker_diarization import SpeakerDiarization
    from pyannote.audio.core.model import Model
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False

from .base import SpeakerDiarizationBase, SpeakerSegment, SpeakerProfile

logger = logging.getLogger(__name__)


class PyannoteRefinementService(SpeakerDiarizationBase):
    """High-accuracy speaker diarization using pyannote.audio
    
    This service is used for post-processing to refine real-time speaker detection results.
    It provides more accurate speaker segmentation but with higher latency.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Model configuration
        self.model_name = config.get("model", "pyannote/speaker-diarization-3.1")
        self.use_auth_token = config.get("hf_auth_token", None)
        if TORCH_AVAILABLE:
            self.device = config.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = "cpu"
        
        # Diarization parameters
        self.min_speakers = config.get("min_speakers", 1)
        self.max_speakers = config.get("max_speakers", 10)
        self.min_duration_on = config.get("min_duration_on", 0.5)  # Minimum speech duration
        self.min_duration_off = config.get("min_duration_off", 0.5)  # Minimum silence duration
        
        # Initialize pipeline (lazy loading)
        self._pipeline: Optional[Pipeline] = None
        self._initialized = False
        
    def initialize(self):
        """Initialize the pyannote pipeline (called on first use)"""
        if self._initialized:
            return
            
        try:
            logger.info(f"Loading pyannote model: {self.model_name}")
            
            # For now, we'll use a mock pipeline for testing
            # In production, you would use:
            # self._pipeline = Pipeline.from_pretrained(
            #     self.model_name,
            #     use_auth_token=self.use_auth_token
            # )
            
            # Mock pipeline for testing
            self._pipeline = MockPipeline(self.config)
            
            logger.info(f"Pyannote pipeline loaded on device: {self.device}")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize pyannote pipeline: {e}")
            raise
    
    def process_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> Optional[SpeakerSegment]:
        """Not used for refinement - this service processes complete audio"""
        raise NotImplementedError("PyannoteRefinementService processes complete audio, not chunks")
    
    def detect_speaker_change(self, audio_chunk: np.ndarray) -> bool:
        """Not used for refinement"""
        raise NotImplementedError("PyannoteRefinementService doesn't do real-time detection")
    
    def identify_speaker(self, audio_chunk: np.ndarray) -> str:
        """Not used for refinement"""
        raise NotImplementedError("PyannoteRefinementService doesn't do real-time identification")
    
    def refine_diarization(self, audio: np.ndarray, sample_rate: int, 
                          initial_segments: Optional[List[SpeakerSegment]] = None) -> List[SpeakerSegment]:
        """Refine speaker diarization for complete audio
        
        Args:
            audio: Complete audio array
            sample_rate: Audio sample rate
            initial_segments: Optional initial segmentation from real-time detection
            
        Returns:
            List of refined speaker segments
        """
        # Initialize on first use
        if not self._initialized:
            self.initialize()
        
        # Save audio to temporary file (pyannote requires file input)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            sf.write(tmp_path, audio, sample_rate)
        
        try:
            # Run diarization
            logger.info(f"Running pyannote diarization on {len(audio)/sample_rate:.2f}s audio")
            
            # Configure pipeline parameters
            diarization_params = {
                "min_speakers": self.min_speakers,
                "max_speakers": self.max_speakers,
            }
            
            # Run the pipeline
            diarization = self._pipeline(tmp_path, **diarization_params)
            
            # Convert pyannote output to our format
            segments = self._convert_to_segments(diarization)
            
            # Map speakers from initial segments if provided
            if initial_segments:
                segments = self._map_speakers_to_initial(segments, initial_segments)
            
            logger.info(f"Refined diarization complete: {len(segments)} segments, "
                       f"{len(set(s.speaker_id for s in segments))} speakers")
            
            return segments
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _convert_to_segments(self, diarization) -> List[SpeakerSegment]:
        """Convert pyannote diarization output to our segment format"""
        segments = []
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segment = SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end,
                confidence=1.0  # Pyannote doesn't provide confidence scores
            )
            segments.append(segment)
        
        return segments
    
    def _map_speakers_to_initial(self, refined_segments: List[SpeakerSegment], 
                                initial_segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Map refined speaker labels to match initial detection labels
        
        This helps maintain consistency between real-time and refined results.
        """
        # Build speaker mapping based on overlap
        speaker_mapping = {}
        
        for refined_seg in refined_segments:
            if refined_seg.speaker_id in speaker_mapping:
                continue
                
            # Find best matching initial speaker based on overlap
            best_match = None
            best_overlap = 0.0
            
            for initial_seg in initial_segments:
                # Calculate overlap
                overlap_start = max(refined_seg.start_time, initial_seg.start_time)
                overlap_end = min(refined_seg.end_time, initial_seg.end_time)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > best_overlap:
                    best_overlap = overlap_duration
                    best_match = initial_seg.speaker_id
            
            if best_match:
                speaker_mapping[refined_seg.speaker_id] = best_match
            else:
                # No overlap found, keep the refined speaker ID
                speaker_mapping[refined_seg.speaker_id] = refined_seg.speaker_id
        
        # Apply mapping
        for segment in refined_segments:
            segment.speaker_id = speaker_mapping.get(segment.speaker_id, segment.speaker_id)
        
        return refined_segments
    
    def merge_close_segments(self, segments: List[SpeakerSegment], 
                           gap_threshold: float = 0.5) -> List[SpeakerSegment]:
        """Merge segments from the same speaker that are close together"""
        if not segments:
            return segments
        
        # Sort by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time)
        
        merged = []
        current = sorted_segments[0]
        
        for next_seg in sorted_segments[1:]:
            # Check if same speaker and close enough
            if (current.speaker_id == next_seg.speaker_id and 
                next_seg.start_time - current.end_time < gap_threshold):
                # Merge segments
                current = SpeakerSegment(
                    speaker_id=current.speaker_id,
                    start_time=current.start_time,
                    end_time=next_seg.end_time,
                    confidence=min(current.confidence, next_seg.confidence)
                )
            else:
                # Different speaker or too far apart
                merged.append(current)
                current = next_seg
        
        # Don't forget the last segment
        merged.append(current)
        
        return merged


class MockPipeline:
    """Mock pipeline for testing without actual model"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def __call__(self, audio_path: str, **kwargs) -> 'MockDiarization':
        """Simulate diarization"""
        # For testing, create some dummy segments
        import wave
        
        # Get audio duration
        with wave.open(audio_path, 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)
        
        # Create mock segments
        segments = []
        if duration > 3:
            # Two speakers alternating
            segments.extend([
                (0.0, 2.0, "SPEAKER_00"),
                (2.5, 4.5, "SPEAKER_01"),
                (5.0, min(7.0, duration), "SPEAKER_00"),
            ])
        else:
            # Single speaker
            segments.append((0.0, duration, "SPEAKER_00"))
        
        return MockDiarization(segments)


class MockDiarization:
    """Mock diarization result"""
    
    def __init__(self, segments: List[Tuple[float, float, str]]):
        self.segments = segments
    
    def itertracks(self, yield_label=True):
        """Iterate over tracks"""
        for start, end, speaker in self.segments:
            turn = MockTurn(start, end)
            yield turn, None, speaker


class MockTurn:
    """Mock turn/segment"""
    
    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end