from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Transcription(Base):
    __tablename__ = "transcriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    audio_url = Column(Text)  # URL to stored audio file
    audio_file_path = Column(Text)  # Path to uploaded audio file
    audio_duration = Column(Integer)  # Duration in seconds
    raw_text = Column(Text)  # Raw transcribed text
    transcription_text = Column(Text)  # Complete transcription text
    processed_text = Column(JSONB)  # Structured clinical data
    clinical_note = Column(Text)  # Formatted clinical note
    status = Column(String(50), default="pending")  # pending, processing, completed, error, cancelled
    format_preference = Column(String(50), default="soap")  # soap, bullet, narrative, epic_template
    confidence_score = Column(Integer)  # Transcription confidence 0-100
    is_final = Column(Boolean, default=False)  # Whether transcription is final or partial
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    speaker_id = Column(String(50))  # To identify different speakers
    language = Column(String(10), default="en")
    
    # Relationships
    encounter = relationship("Encounter", back_populates="transcriptions")