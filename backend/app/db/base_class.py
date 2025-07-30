# Import all models so they're registered with Base
from app.db.base import Base
from app.models.user import User
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote

# This ensures all models are imported when creating tables
__all__ = ["Base", "User", "Patient", "Encounter", "Transcription", "ClinicalNote"]