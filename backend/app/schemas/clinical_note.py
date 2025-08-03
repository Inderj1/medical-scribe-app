"""Clinical note schemas for API responses"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel


class ClinicalNoteBase(BaseModel):
    """Base clinical note schema"""
    format_type: str = "soap"
    content: str
    sections: Dict[str, Any] = {}


class ClinicalNoteCreate(ClinicalNoteBase):
    """Schema for creating clinical note"""
    transcription_id: str


class ClinicalNoteResponse(ClinicalNoteBase):
    """Schema for clinical note response"""
    id: str
    transcription_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class QAReportResponse(BaseModel):
    """Schema for QA report response"""
    id: str
    transcription_id: str
    overall_score: float
    completeness_score: float
    accuracy_score: float
    clarity_score: float
    missing_sections: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    approved: bool
    created_at: datetime
    
    class Config:
        from_attributes = True