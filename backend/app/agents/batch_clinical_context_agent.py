"""Batch Clinical Context Agent for medical understanding and entity extraction"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from app.services.clinical_nlp import ClinicalNLPService
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class BatchClinicalContextAgent(BaseAgent):
    """Processes transcriptions for medical context and entity extraction"""
    
    def __init__(self):
        super().__init__(
            name="ClinicalContextAgent",
            description="Extracts medical entities and clinical context from transcriptions"
        )
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.clinical_nlp = ClinicalNLPService()
        
        # Medical entity patterns
        self._init_medical_patterns()
        
    def _init_medical_patterns(self):
        """Initialize regex patterns for medical entity detection"""
        self.patterns = {
            "medications": re.compile(
                r'\b(\w+)\s+(\d+\.?\d*)\s*(mg|mcg|ml|units?|tablets?|capsules?)\b',
                re.IGNORECASE
            ),
            "vitals": re.compile(
                r'\b(blood pressure|bp|heart rate|hr|pulse|temperature|temp|oxygen|spo2|weight|height|bmi)\s*:?\s*(\d+\.?\d*)(?:/(\d+\.?\d*))?',
                re.IGNORECASE
            ),
            "symptoms": re.compile(
                r'\b(pain|ache|fever|cough|nausea|vomiting|dizziness|fatigue|shortness of breath|headache|chest pain|abdominal pain)\b',
                re.IGNORECASE
            ),
            "diagnoses": re.compile(
                r'\b(?:diagnosis|diagnosed with|impression|assessment):\s*([^.]+)',
                re.IGNORECASE
            )
        }
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "handoff:analyze_transcription":
            return await self._analyze_transcription(message)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
            
    async def _analyze_transcription(self, message: AgentMessage) -> AgentMessage:
        """Analyze transcription for medical context"""
        try:
            transcription_data = message.payload
            text = transcription_data.get("text", "")
            transcription_id = transcription_data.get("transcription_id")
            encounter_id = transcription_data.get("encounter_id")
            
            # Extract medical entities using patterns
            basic_entities = self._extract_basic_entities(text)
            
            # Extract entities using clinical NLP
            nlp_entities = await self.clinical_nlp.extract_entities(text)
            
            # Enhance with GPT-4 for deeper understanding
            enhanced_analysis = await self._enhance_with_gpt4(text, basic_entities, nlp_entities)
            
            # Combine all analyses
            final_analysis = {
                "transcription_id": transcription_id,
                "encounter_id": encounter_id,
                "original_text": text,
                "basic_entities": basic_entities,
                "nlp_entities": nlp_entities,
                "clinical_sections": enhanced_analysis,
                "suggested_sections": self._suggest_sections(enhanced_analysis),
                "medical_terms": self._extract_medical_terms(text),
                "timestamp": datetime.utcnow().isoformat(),
                "confidence_scores": self._calculate_confidence_scores(enhanced_analysis)
            }
            
            # Create handoff to note structuring agent
            return AgentHandoff.create_handoff_message(
                from_agent=self.name,
                to_agent="NoteStructuringAgent",
                data=final_analysis,
                handoff_type="structure_note"
            )
            
        except Exception as e:
            logger.error(f"Clinical analysis error: {str(e)}")
            return self._create_error_response(message, str(e))
            
    def _extract_basic_entities(self, text: str) -> Dict[str, List[Any]]:
        """Extract basic medical entities using regex patterns"""
        entities = {
            "medications": [],
            "vital_signs": [],
            "symptoms": [],
            "diagnoses": []
        }
        
        # Extract medications
        for match in self.patterns["medications"].finditer(text):
            entities["medications"].append({
                "name": match.group(1),
                "dose": match.group(2),
                "unit": match.group(3)
            })
            
        # Extract vital signs
        for match in self.patterns["vitals"].finditer(text):
            vital_type = match.group(1).lower()
            value = match.group(2)
            
            vital_entry = {
                "type": vital_type,
                "value": value
            }
            
            # Handle blood pressure (has two values)
            if match.group(3) and vital_type in ["blood pressure", "bp"]:
                vital_entry["systolic"] = value
                vital_entry["diastolic"] = match.group(3)
                
            entities["vital_signs"].append(vital_entry)
            
        # Extract symptoms
        symptoms = self.patterns["symptoms"].findall(text)
        entities["symptoms"] = list(set(symptoms))  # Remove duplicates
        
        # Extract diagnoses
        for match in self.patterns["diagnoses"].finditer(text):
            diagnosis = match.group(1).strip()
            if diagnosis:
                entities["diagnoses"].append(diagnosis)
                
        return entities
        
    async def _enhance_with_gpt4(self, text: str, basic_entities: Dict, nlp_entities: Dict) -> Dict[str, Any]:
        """Use GPT-4 to enhance clinical understanding"""
        try:
            system_prompt = """You are a medical scribe AI assistant. Analyze the transcribed medical conversation and extract information for the following clinical note sections:

1. Chief Complaint: The main reason for the visit (1-2 sentences)
2. History of Present Illness: Detailed symptom description, onset, duration, severity, associated symptoms
3. Past Medical History: Previous medical conditions, surgeries, hospitalizations
4. Medications: Current medications with doses and frequencies
5. Allergies: Drug allergies and reactions
6. Social History: Smoking, alcohol, occupation, living situation
7. Family History: Relevant family medical conditions
8. Review of Systems: Other symptoms by body system
9. Physical Examination: Exam findings by body system
10. Vital Signs: BP, HR, RR, Temp, O2, Weight, Height
11. Assessment: Clinical impressions and diagnoses
12. Plan: Treatment plan, medications prescribed, tests ordered, follow-up

Respond in JSON format with these sections as keys. Only include sections that have relevant information from the transcript. Be precise and use proper medical terminology."""

            user_prompt = f"""Transcription: {text}

Basic entities already extracted: {json.dumps(basic_entities, indent=2)}

Additional NLP entities: {json.dumps(nlp_entities, indent=2)}

Please provide a structured clinical analysis."""

            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Error enhancing with GPT-4: {str(e)}")
            # Fallback to basic analysis
            return self._create_basic_analysis(text, basic_entities, nlp_entities)
            
    def _create_basic_analysis(self, text: str, basic_entities: Dict, nlp_entities: Dict) -> Dict[str, Any]:
        """Create basic clinical analysis without GPT-4"""
        analysis = {}
        
        # Try to identify chief complaint (first symptom mentioned)
        if basic_entities.get("symptoms"):
            analysis["chief_complaint"] = f"Patient presents with {basic_entities['symptoms'][0]}"
            
        # Add medications if found
        if basic_entities.get("medications"):
            analysis["medications"] = [
                f"{med['name']} {med['dose']} {med['unit']}" 
                for med in basic_entities["medications"]
            ]
            
        # Add vital signs
        if basic_entities.get("vital_signs"):
            analysis["vital_signs"] = {}
            for vital in basic_entities["vital_signs"]:
                if vital["type"] in ["blood pressure", "bp"] and "systolic" in vital:
                    analysis["vital_signs"]["blood_pressure"] = f"{vital['systolic']}/{vital['diastolic']}"
                else:
                    analysis["vital_signs"][vital["type"]] = vital["value"]
                    
        # Add diagnoses/assessment
        if basic_entities.get("diagnoses"):
            analysis["assessment"] = "; ".join(basic_entities["diagnoses"])
            
        return analysis
        
    def _suggest_sections(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest which sections to populate based on analysis"""
        section_mapping = {
            "chief_complaint": "chief_complaint",
            "history_of_present_illness": "present_illness",
            "medications": "medications",
            "allergies": "allergies",
            "vital_signs": "vital_signs",
            "physical_examination": "physical_exam",
            "assessment": "assessment",
            "plan": "plan"
        }
        
        suggestions = []
        for key, section in section_mapping.items():
            if key in analysis and analysis[key]:
                suggestions.append(section)
                
        return suggestions
        
    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extract medical terminology from text"""
        # Common medical term patterns
        medical_patterns = [
            r'\b(?:hypertension|diabetes|asthma|COPD|CHF|CAD|GERD|UTI)\b',
            r'\b(?:antibiotics?|analgesics?|antihypertensives?|diuretics?)\b',
            r'\b(?:MRI|CT|X-ray|ultrasound|ECG|EKG|labs?|blood work)\b',
            r'\b(?:acute|chronic|bilateral|unilateral|moderate|severe|mild)\b'
        ]
        
        terms = []
        for pattern in medical_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            terms.extend(matches)
            
        return list(set(terms))  # Remove duplicates
        
    def _calculate_confidence_scores(self, analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for each section"""
        scores = {}
        
        for section, content in analysis.items():
            if isinstance(content, str):
                # Higher confidence for longer, more detailed content
                length_score = min(len(content) / 100, 1.0)
                scores[section] = 0.7 + (0.3 * length_score)
            elif isinstance(content, list):
                # Higher confidence for more items
                count_score = min(len(content) / 5, 1.0)
                scores[section] = 0.7 + (0.3 * count_score)
            elif isinstance(content, dict):
                # Higher confidence for more populated fields
                filled_score = len([v for v in content.values() if v]) / max(len(content), 1)
                scores[section] = 0.7 + (0.3 * filled_score)
            else:
                scores[section] = 0.5
                
        return scores
        
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create error response message"""
        return AgentMessage(
            agent_id=self.name,
            message_type="clinical_analysis_error",
            payload={
                "error": error,
                "original_request": original_message.payload,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Agent factory function
def create_batch_clinical_context_agent() -> BatchClinicalContextAgent:
    """Create and return a batch clinical context agent instance"""
    return BatchClinicalContextAgent()