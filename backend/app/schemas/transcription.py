"""Transcription schemas for API responses"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class TranscriptionBase(BaseModel):
    """Base transcription schema"""
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    status: str = "pending"
    word_count: int = 0
    speaker_count: int = 0
    format_preference: str = "soap"


class TranscriptionCreate(TranscriptionBase):
    """Schema for creating transcription"""
    encounter_id: Optional[str] = None
    patient_id: Optional[str] = None


class TranscriptionUpdate(TranscriptionBase):
    """Schema for updating transcription"""
    pass


class TranscriptionResponse(TranscriptionBase):
    """Schema for transcription response"""
    id: str
    user_id: str
    encounter_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sections: Optional[Dict[str, Any]] = None
    qa_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class TranscriptionListResponse(BaseModel):
    """Schema for list of transcriptions"""
    transcriptions: List[TranscriptionResponse]
    total: int
    page: int
    page_size: int


class TranscriptionStatusResponse(BaseModel):
    """Schema for transcription status"""
    id: str
    status: str
    progress: int
    message: Optional[str] = None
    sections_completed: List[str] = []
    current_stage: Optional[str] = None