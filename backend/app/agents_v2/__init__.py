"""Agents v2 module with OpenAI SDK patterns"""

# Export the OpenAI SDK pattern implementations
from app.agents_v2.base_agents_openai import medical_scribe_agents
from app.agents_v2.orchestrator_openai import orchestrator
from app.agents_v2.models import (
    TranscriptionData, ClinicalData, StructuredNote, 
    QAReport, SessionContext, MedicalEntity
)

__all__ = [
    "medical_scribe_agents",
    "orchestrator",
    "TranscriptionData",
    "ClinicalData", 
    "StructuredNote",
    "QAReport",
    "SessionContext",
    "MedicalEntity"
]