import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


# Define output schemas for each section type
class ChiefComplaintOutput(BaseModel):
    """Output schema for chief complaint section"""
    chief_complaint: str = Field(description="The primary reason for the visit")
    onset: Optional[str] = Field(description="When the symptom started")
    duration: Optional[str] = Field(description="How long it has been present")
    severity: Optional[str] = Field(description="Severity of the symptom")
    triggers: Optional[str] = Field(description="What triggers or worsens it")
    
class MedicationsOutput(BaseModel):
    """Output schema for medications section"""
    current_medications: List[Dict[str, str]] = Field(description="List of current medications with dosage")
    compliance: Optional[str] = Field(description="Patient's medication adherence")
    allergies: Optional[List[str]] = Field(description="Drug allergies")
    
class PhysicalExamOutput(BaseModel):
    """Output schema for physical exam section"""
    vital_signs: Optional[Dict[str, str]] = Field(description="Vital signs if mentioned")
    findings: List[str] = Field(description="Examination findings")
    pertinent_negatives: Optional[List[str]] = Field(description="Important negative findings")

class AssessmentPlanOutput(BaseModel):
    """Output schema for assessment and plan section"""
    assessment: str = Field(description="Clinical assessment")
    diagnoses: Optional[List[str]] = Field(description="Differential diagnoses")
    plan_items: List[str] = Field(description="Treatment plan items")
    follow_up: Optional[str] = Field(description="Follow-up instructions")


@dataclass
class SectionResult:
    """Result from processing a section"""
    section: str
    content: str
    formatted_content: Dict[str, str]  # long, short, bullet versions
    confidence: float
    entities: List[Dict[str, Any]]
    timestamp: str
    
    def to_dict(self):
        return {
            "section": self.section,
            "content": self.content,
            "formatted_content": self.formatted_content,
            "confidence": self.confidence,
            "entities": self.entities,
            "timestamp": self.timestamp
        }


class OpenAISectionAgents:
    """
    Manages OpenAI API calls for each clinical documentation section.
    Each section has specialized prompts and structured output.
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.contexts = {}  # encounter_id -> {section: context}
        self.section_prompts = self._initialize_prompts()
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialize specialized prompts for each section"""
        return {
            "chief_complaint": """You are a medical documentation specialist focused on chief complaints.
            Extract and document the primary reason for the patient's visit.
            
            Focus on:
            - Main symptom or concern
            - Duration and onset
            - Severity (if mentioned)
            - What prompted the visit today
            
            Always provide content in three formats:
            1. Long: Detailed professional medical documentation
            2. Short: Concise medical notes
            3. Bullet: Bullet-point format
            
            Write from the medical provider's perspective using proper medical terminology.""",
            
            "medications": """You are a medical documentation specialist focused on medications.
            Document current medications, dosages, and compliance.
            
            Focus on:
            - Current medications with dosages
            - Medication adherence/compliance
            - Recent changes to medications
            - Drug allergies
            
            Provide three formats as specified.""",
            
            "physical_exam": """You are a medical documentation specialist focused on physical examination.
            Document examination findings professionally.
            
            Focus on:
            - Vital signs
            - System-specific findings
            - Pertinent positives and negatives
            - Clinical observations
            
            Provide three formats as specified.""",
            
            "assessment_plan": """You are a medical documentation specialist focused on assessment and plan.
            Document clinical assessment and treatment plan.
            
            Focus on:
            - Clinical assessment/impression
            - Differential diagnoses
            - Treatment plan
            - Follow-up recommendations
            
            Provide three formats as specified.""",
            
            "history_present_illness": """You are a medical documentation specialist focused on history of present illness.
            Create a comprehensive narrative of the patient's current condition.
            
            Focus on:
            - Chronological progression
            - Associated symptoms
            - Alleviating/aggravating factors
            - Previous treatments tried
            
            Provide three formats as specified.""",
            
            "review_of_systems": """You are a medical documentation specialist focused on review of systems.
            Document systematic review of symptoms.
            
            Focus on:
            - Constitutional symptoms
            - System-specific symptoms
            - Pertinent positives and negatives
            
            Provide three formats as specified."""
        }
    
    async def process_section(
        self,
        section: str,
        transcription: str,
        speaker: str,
        format_preference: str = "long",
        previous_content: Optional[Dict[str, str]] = None
    ) -> SectionResult:
        """Process transcription for a specific section using OpenAI API"""
        
        if section not in self.section_prompts:
            raise ValueError(f"Unknown section: {section}")
        
        try:
            # Build context from previous content
            context = ""
            if previous_content:
                context = "Previous context:\n"
                for sect, content in previous_content.items():
                    context += f"{sect}: {content}\n"
                context += "\n"
            
            # Create the prompt
            system_prompt = self.section_prompts[section]
            
            user_prompt = f"""{context}Speaker: {speaker}
Transcription: {transcription}

Based on this transcription, create documentation for the {section} section.

Provide the output in JSON format with three versions:
{{
    "long": "Detailed professional medical documentation",
    "short": "Concise medical notes",
    "bullet": "Bullet-point format",
    "entities": [
        {{"type": "symptom/medication/condition/etc", "text": "entity text", "value": "normalized value"}}
    ],
    "confidence": 0.0-1.0
}}"""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result_data = json.loads(response.choices[0].message.content)
            
            # Create formatted content
            formatted_content = {
                "long": result_data.get("long", ""),
                "short": result_data.get("short", ""),
                "bullet": result_data.get("bullet", "")
            }
            
            # Select content based on format preference
            content = formatted_content.get(format_preference, formatted_content["long"])
            
            return SectionResult(
                section=section,
                content=content,
                formatted_content=formatted_content,
                confidence=result_data.get("confidence", 0.8),
                entities=result_data.get("entities", []),
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error processing section {section}: {str(e)}")
            # Return a basic result on error
            return SectionResult(
                section=section,
                content=transcription,
                formatted_content={
                    "long": transcription,
                    "short": transcription,
                    "bullet": f"• {transcription}"
                },
                confidence=0.5,
                entities=[],
                timestamp=datetime.utcnow().isoformat()
            )
    
    def add_to_context(self, encounter_id: str, section: str, content: str):
        """Add processed content to context for future reference"""
        if encounter_id not in self.contexts:
            self.contexts[encounter_id] = {}
        self.contexts[encounter_id][section] = content
    
    def get_context(self, encounter_id: str) -> Dict[str, str]:
        """Get all context for an encounter"""
        return self.contexts.get(encounter_id, {})
    
    def clear_context(self, encounter_id: str):
        """Clear context for an encounter"""
        if encounter_id in self.contexts:
            del self.contexts[encounter_id]


# For backward compatibility
SectionAgents = OpenAISectionAgents