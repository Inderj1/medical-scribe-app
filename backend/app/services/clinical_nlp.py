import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import anthropic
from anthropic import Anthropic

from app.core.config import settings
from app.models.clinical_note import NoteSection

logger = logging.getLogger(__name__)


@dataclass
class ClinicalEntity:
    entity_type: str  # symptom, diagnosis, medication, procedure, etc.
    text: str
    context: str
    confidence: float
    attributes: Dict[str, Any]


@dataclass
class ClinicalData:
    section: NoteSection
    content: Dict[str, Any]
    entities: List[ClinicalEntity]
    raw_text: str
    timestamp: datetime


class ClinicalNLPService:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
        self.medical_patterns = self._initialize_patterns()
        
    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for medical terms"""
        return {
            "blood_pressure": re.compile(r'\b(\d{2,3})/(\d{2,3})\s*(?:mmHg)?\b'),
            "temperature": re.compile(r'\b(\d{2,3}(?:\.\d)?)\s*(?:°F|degrees?|fahrenheit)\b', re.I),
            "heart_rate": re.compile(r'\b(\d{2,3})\s*(?:bpm|beats per minute|heart rate)\b', re.I),
            "oxygen_saturation": re.compile(r'\b(\d{2})\s*(?:%|percent|O2 sat|oxygen)\b', re.I),
            "pain_scale": re.compile(r'\b(\d{1,2})\s*(?:out of 10|/10|pain)\b', re.I),
            "medications": re.compile(r'\b(?:taking|prescribed|medication|med):\s*([^,\.]+)', re.I),
            "symptoms": re.compile(r'\b(?:complains? of|reports?|experiencing|has been having|symptoms?):\s*([^,\.]+)', re.I),
        }
        
    async def extract_clinical_entities(self, text: str) -> ClinicalData:
        """Extract clinical entities from transcribed text"""
        try:
            # First, try to extract structured data using AI
            if self.client:
                structured_data = await self._extract_with_ai(text)
            else:
                # Fallback to pattern matching
                structured_data = self._extract_with_patterns(text)
                
            # Determine the appropriate section
            section = self._determine_section(text, structured_data)
            
            # Extract entities
            entities = self._extract_entities(text, structured_data)
            
            # Format content for the section
            content = self._format_section_content(section, structured_data)
            
            return ClinicalData(
                section=section,
                content=content,
                entities=entities,
                raw_text=text,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error extracting clinical entities: {e}")
            return ClinicalData(
                section=NoteSection.HISTORY,
                content={},
                entities=[],
                raw_text=text,
                timestamp=datetime.utcnow()
            )
            
    async def _extract_with_ai(self, text: str) -> Dict[str, Any]:
        """Use AI to extract structured clinical data"""
        try:
            prompt = f"""Extract clinical information from this medical transcript and return it as structured JSON.

Transcript: {text}

Return a JSON object with these fields:
- chief_complaint: The main reason for the visit
- symptoms: Array of symptoms with severity and duration
- vital_signs: Object with BP, HR, RR, temp, O2, pain
- medications: Array of current medications
- physical_exam: Key findings from examination
- assessment: Clinical assessment
- plan: Treatment plan
- section_type: One of [history, review_of_systems, physical_exam, assessment, plan]

Only include fields that are mentioned in the transcript."""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            json_text = response.content[0].text
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', json_text)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {}
                
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return {}
            
    def _extract_with_patterns(self, text: str) -> Dict[str, Any]:
        """Fallback pattern-based extraction"""
        data = {
            "vital_signs": {},
            "symptoms": [],
            "medications": []
        }
        
        # Extract vital signs
        for pattern_name, pattern in self.medical_patterns.items():
            matches = pattern.findall(text)
            if matches:
                if pattern_name == "blood_pressure" and matches:
                    data["vital_signs"]["blood_pressure"] = f"{matches[0][0]}/{matches[0][1]}"
                elif pattern_name == "temperature" and matches:
                    data["vital_signs"]["temperature"] = float(matches[0])
                elif pattern_name == "heart_rate" and matches:
                    data["vital_signs"]["heart_rate"] = int(matches[0])
                elif pattern_name == "oxygen_saturation" and matches:
                    data["vital_signs"]["oxygen_saturation"] = int(matches[0])
                elif pattern_name == "pain_scale" and matches:
                    data["vital_signs"]["pain_level"] = int(matches[0])
                elif pattern_name == "symptoms" and matches:
                    data["symptoms"] = [{"description": match.strip()} for match in matches]
                elif pattern_name == "medications" and matches:
                    data["medications"] = [{"name": match.strip()} for match in matches]
                    
        return data
        
    def _determine_section(self, text: str, data: Dict[str, Any]) -> NoteSection:
        """Determine which section this text belongs to"""
        text_lower = text.lower()
        
        # Check for explicit section type from AI
        if "section_type" in data:
            section_map = {
                "history": NoteSection.HISTORY,
                "review_of_systems": NoteSection.REVIEW_OF_SYSTEMS,
                "physical_exam": NoteSection.PHYSICAL_EXAM,
                "assessment": NoteSection.ASSESSMENT,
                "plan": NoteSection.PLAN
            }
            return section_map.get(data["section_type"], NoteSection.HISTORY)
            
        # Pattern-based section detection
        if any(word in text_lower for word in ["chief complaint", "presents with", "complains of", "history"]):
            return NoteSection.HISTORY
        elif any(word in text_lower for word in ["examination", "exam reveals", "on exam", "auscultation"]):
            return NoteSection.PHYSICAL_EXAM
        elif any(word in text_lower for word in ["assessment", "diagnosis", "impression"]):
            return NoteSection.ASSESSMENT
        elif any(word in text_lower for word in ["plan", "recommend", "prescribe", "follow up"]):
            return NoteSection.PLAN
        elif any(word in text_lower for word in ["review of systems", "ros", "denies", "no fever"]):
            return NoteSection.REVIEW_OF_SYSTEMS
        else:
            return NoteSection.HISTORY
            
    def _extract_entities(self, text: str, data: Dict[str, Any]) -> List[ClinicalEntity]:
        """Extract clinical entities from the data"""
        entities = []
        
        # Extract symptom entities
        for symptom in data.get("symptoms", []):
            entities.append(ClinicalEntity(
                entity_type="symptom",
                text=symptom.get("description", ""),
                context=text[:100],
                confidence=0.8,
                attributes={
                    "severity": symptom.get("severity", "moderate"),
                    "duration": symptom.get("duration", "unknown")
                }
            ))
            
        # Extract vital sign entities
        for vital_name, vital_value in data.get("vital_signs", {}).items():
            entities.append(ClinicalEntity(
                entity_type="vital_sign",
                text=f"{vital_name}: {vital_value}",
                context=text[:100],
                confidence=0.9,
                attributes={
                    "name": vital_name,
                    "value": vital_value,
                    "abnormal": self._is_vital_abnormal(vital_name, vital_value)
                }
            ))
            
        # Extract medication entities
        for med in data.get("medications", []):
            entities.append(ClinicalEntity(
                entity_type="medication",
                text=med.get("name", ""),
                context=text[:100],
                confidence=0.7,
                attributes={
                    "dosage": med.get("dosage", ""),
                    "frequency": med.get("frequency", "")
                }
            ))
            
        return entities
        
    def _format_section_content(self, section: NoteSection, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format content based on section type"""
        if section == NoteSection.HISTORY:
            return {
                "chief_complaint": data.get("chief_complaint", ""),
                "present_illness": data.get("symptoms", []),
                "duration": "See transcript"
            }
        elif section == NoteSection.PHYSICAL_EXAM:
            return {
                "general": data.get("physical_exam", {}).get("general", ""),
                "vitals": data.get("vital_signs", {}),
                "systems": data.get("physical_exam", {}).get("systems", {})
            }
        elif section == NoteSection.ASSESSMENT:
            return {
                "diagnoses": data.get("assessment", []),
                "differential": data.get("differential", [])
            }
        elif section == NoteSection.PLAN:
            return {
                "medications": data.get("medications", []),
                "procedures": data.get("procedures", []),
                "follow_up": data.get("follow_up", "")
            }
        else:
            return data
            
    def _is_vital_abnormal(self, vital_name: str, value: Any) -> bool:
        """Check if a vital sign is abnormal"""
        normal_ranges = {
            "blood_pressure": {"systolic": (90, 140), "diastolic": (60, 90)},
            "heart_rate": (60, 100),
            "temperature": (97.0, 99.5),
            "oxygen_saturation": (95, 100),
            "respiratory_rate": (12, 20)
        }
        
        try:
            if vital_name == "blood_pressure" and isinstance(value, str):
                systolic, diastolic = map(int, value.split("/"))
                return not (normal_ranges["blood_pressure"]["systolic"][0] <= systolic <= normal_ranges["blood_pressure"]["systolic"][1] and
                           normal_ranges["blood_pressure"]["diastolic"][0] <= diastolic <= normal_ranges["blood_pressure"]["diastolic"][1])
            elif vital_name in normal_ranges:
                num_value = float(value)
                range_min, range_max = normal_ranges[vital_name]
                return not (range_min <= num_value <= range_max)
        except:
            pass
            
        return False