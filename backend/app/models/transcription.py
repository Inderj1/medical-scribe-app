from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.db.base import Base


class TranscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(Base):
    __tablename__ = "transcriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"))
    audio_file_path = Column(Text)
    audio_duration_seconds = Column(Integer)
    file_size_bytes = Column(BigInteger)
    transcript = Column(Text)
    partial_transcript = Column(Text)
    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    processing_metadata = Column(JSONB)  # whisper settings, processing times
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    encounter = relationship("Encounter", backref="transcriptions")