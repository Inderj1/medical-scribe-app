"""Data models for agent communication and typed contexts"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime


class SpeakerSegment(BaseModel):
    """Represents a speaker segment in the transcript"""
    speaker_id: str
    text: str
    start_index: int
    end_index: int
    timestamp: Optional[float] = None


class TranscriptionData(BaseModel):
    """Data passed from transcription agent to clinical analysis"""
    session_id: str
    transcription_id: str
    transcript: str
    speaker_segments: List[SpeakerSegment] = Field(default_factory=list)
    speaker_roles: Dict[str, str] = Field(default_factory=dict)
    word_count: int
    language: str = "en"
    audio_duration: Optional[float] = None


class MedicalEntity(BaseModel):
    """Represents a medical entity extracted from text"""
    type: str  # symptom, diagnosis, medication, procedure, lab_value
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    section: Optional[str] = None


class ClinicalSection(BaseModel):
    """Represents a section of clinical documentation"""
    name: str
    content: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    entities: List[MedicalEntity] = Field(default_factory=list)


class ClinicalData(BaseModel):
    """Data passed from clinical analysis to note structuring"""
    session_id: str
    transcription_id: str
    chief_complaint: Optional[str] = None
    history_present_illness: Optional[str] = None
    review_of_systems: Optional[Dict[str, Any]] = None
    past_medical_history: Optional[str] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    social_history: Optional[str] = None
    family_history: Optional[str] = None
    physical_examination: Optional[Dict[str, Any]] = None
    vital_signs: Optional[Dict[str, Any]] = None
    diagnostic_results: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    additional_notes: Optional[str] = None
    care_coordination: Optional[str] = None
    medical_entities: List[MedicalEntity] = Field(default_factory=list)
    sections: List[ClinicalSection] = Field(default_factory=list)


class StructuredNote(BaseModel):
    """Data passed from note structuring to QA"""
    session_id: str
    transcription_id: str
    format_type: str = "soap"  # soap, bullet, narrative
    note_content: str
    sections: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QAReport(BaseModel):
    """Quality assurance report"""
    session_id: str
    transcription_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    accuracy_score: float = Field(ge=0.0, le=1.0)
    clarity_score: float = Field(ge=0.0, le=1.0)
    missing_sections: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    approved: bool = False


class SessionContext(BaseModel):
    """Complete session context"""
    session_id: str
    transcription_id: str
    patient_context: Dict[str, Any] = Field(default_factory=dict)
    encounter_id: Optional[str] = None
    encounter_date: Optional[datetime] = None
    provider_id: Optional[str] = None
    ehr_sections: Dict[str, Any] = Field(default_factory=dict)
    audio_path: Optional[str] = None
    format_preference: str = "soap"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)