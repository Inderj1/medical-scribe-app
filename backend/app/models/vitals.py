from sqlalchemy import Column, Integer, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Vitals(Base):
    __tablename__ = "vitals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    measurement_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # Vital signs
    blood_pressure_systolic = Column(Integer)  # mmHg
    blood_pressure_diastolic = Column(Integer)  # mmHg
    heart_rate = Column(Integer)  # bpm
    respiratory_rate = Column(Integer)  # breaths per minute
    temperature = Column(Numeric(4, 1))  # Fahrenheit
    oxygen_saturation = Column(Integer)  # percentage
    pain_level = Column(Integer)  # 0-10 scale
    
    # Additional measurements
    weight = Column(Numeric(5, 1))  # pounds
    height = Column(Numeric(4, 1))  # inches
    bmi = Column(Numeric(4, 1))  # calculated BMI
    
    # Metadata
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes = Column(String(255))
    
    # Relationships
    encounter = relationship("Encounter", back_populates="vitals")
    recorded_by_user = relationship("User")