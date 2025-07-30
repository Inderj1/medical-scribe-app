from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base import Base


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"))
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"))
    
    # SOAP Format
    subjective = Column(Text)
    objective = Column(Text)
    assessment = Column(Text)
    plan = Column(Text)
    
    # Detailed Sections
    chief_complaint = Column(Text)
    history_present_illness = Column(Text)
    review_of_systems = Column(Text)
    past_medical_history = Column(Text)
    past_surgical_history = Column(Text)
    medications = Column(Text)
    allergies = Column(Text)
    social_history = Column(Text)
    family_history = Column(Text)
    physical_exam = Column(Text)
    diagnostic_results = Column(Text)
    additional_notes = Column(Text)
    care_coordination = Column(Text)
    
    # Metadata
    format_type = Column(String, default="soap")  # soap, bullet, narrative
    quality_score = Column(Float)
    ehr_composition_id = Column(String)
    ai_confidence_scores = Column(JSONB)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transcription = relationship("Transcription", backref="clinical_notes")
    encounter = relationship("Encounter", backref="clinical_notes")