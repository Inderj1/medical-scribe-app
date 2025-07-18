from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.session import Base


class EncounterStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    SIGNED = "signed"
    CANCELLED = "cancelled"


class Encounter(Base):
    __tablename__ = "encounters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    encounter_date = Column(DateTime(timezone=True), server_default=func.now())
    chief_complaint = Column(Text)
    status = Column(Enum(EncounterStatus), default=EncounterStatus.ACTIVE)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    location = Column(String(100))
    encounter_type = Column(String(50))  # "new_patient", "follow_up", "urgent", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    signed_at = Column(DateTime(timezone=True))
    
    # Relationships
    patient = relationship("Patient", backref="encounters")
    provider = relationship("User", backref="encounters")
    transcriptions = relationship("Transcription", back_populates="encounter", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="encounter", cascade="all, delete-orphan")
    vitals = relationship("Vitals", back_populates="encounter", cascade="all, delete-orphan")