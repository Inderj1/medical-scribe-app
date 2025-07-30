from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base import Base


class Encounter(Base):
    __tablename__ = "encounters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    ehr_encounter_id = Column(String)
    chief_complaint = Column(Text)
    encounter_date = Column(DateTime, default=datetime.utcnow)
    encounter_type = Column(String)  # office_visit, emergency, telehealth
    status = Column(String, default="ACTIVE")  # ACTIVE, PAUSED, COMPLETED, SIGNED, CANCELLED
    provider_name = Column(String)
    location = Column(String)
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", backref="encounters")
    user = relationship("User", backref="encounters")