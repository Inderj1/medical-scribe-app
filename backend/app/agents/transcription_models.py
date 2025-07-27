"""Data models for transcription agents"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SessionStatus:
    """Status of a transcription session"""
    status: str
    encounter_id: str
    patient_id: str
    session_started: str
    error: Optional[str] = None


@dataclass
class AudioProcessingResult:
    """Result of audio processing"""
    status: str
    bytes: int
    error: Optional[str] = None


@dataclass
class SessionEndResult:
    """Result of ending a session"""
    status: str
    session_ended: str


@dataclass
class MedicalEntity:
    """A medical entity extracted from text"""
    type: str
    name: str
    dose: Optional[str] = None
    unit: Optional[str] = None
    systolic: Optional[str] = None
    diastolic: Optional[str] = None


@dataclass
class ClinicalAnalysis:
    """Clinical analysis of transcribed text"""
    text: str
    chief_complaint: Optional[str] = None
    symptoms: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    vital_signs: Optional[str] = None
    physical_exam: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    timestamp: Optional[str] = None