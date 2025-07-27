"""Batch Note Structuring Agent for organizing clinical documentation"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class NoteFormat(Enum):
    """Supported note formats"""
    SOAP = "soap"
    NARRATIVE = "narrative"
    BULLET = "bullet"
    EPIC_TEMPLATE = "epic_template"


class ClinicalSection(Enum):
    """Clinical note sections"""
    CHIEF_COMPLAINT = "chief_complaint"
    HISTORY_PRESENT_ILLNESS = "history_present_illness"
    PAST_MEDICAL_HISTORY = "past_medical_history"
    MEDICATIONS = "medications"
    ALLERGIES = "allergies"
    SOCIAL_HISTORY = "social_history"
    FAMILY_HISTORY = "family_history"
    REVIEW_OF_SYSTEMS = "review_of_systems"
    VITAL_SIGNS = "vital_signs"
    PHYSICAL_EXAMINATION = "physical_examination"
    ASSESSMENT = "assessment"
    PLAN = "plan"


class BatchNoteStructuringAgent(BaseAgent):
    """Structures clinical notes from analyzed transcriptions"""
    
    def __init__(self):
        super().__init__(
            name="NoteStructuringAgent",
            description="Structures and formats clinical notes from analyzed content"
        )
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Format templates
        self._init_format_templates()
        
    def _init_format_templates(self):
        """Initialize format templates"""
        self.soap_template = {
            "subjective": ["chief_complaint", "history_present_illness", "review_of_systems"],
            "objective": ["vital_signs", "physical_examination"],
            "assessment": ["assessment"],
            "plan": ["plan", "medications", "follow_up"]
        }
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "handoff:structure_note":
            return await self._structure_clinical_note(message)
        elif message.message_type == "format_note":
            return await self._format_existing_note(message)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
            
    async def _structure_clinical_note(self, message: AgentMessage) -> AgentMessage:
        """Structure the clinical analysis into formatted note"""
        try:
            analysis_data = message.payload
            transcription_id = analysis_data.get("transcription_id")
            encounter_id = analysis_data.get("encounter_id")
            clinical_sections = analysis_data.get("clinical_sections", {})
            suggested_sections = analysis_data.get("suggested_sections", [])
            
            # Default format (can be overridden by user preference)
            note_format = NoteFormat.SOAP
            
            # Structure content into sections
            structured_sections = self._organize_content_by_sections(
                clinical_sections,
                suggested_sections
            )
            
            # Format according to chosen format
            formatted_note = await self._format_note(
                structured_sections,
                note_format
            )
            
            # Generate section-specific updates for progressive UI updates
            section_updates = self._generate_section_updates(structured_sections)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_note_quality(structured_sections)
            
            result = {
                "transcription_id": transcription_id,
                "encounter_id": encounter_id,
                "structured_sections": structured_sections,
                "formatted_note": formatted_note,
                "format": note_format.value,
                "section_updates": section_updates,
                "quality_metrics": quality_metrics,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            # Return result (no handoff needed - this is the final agent)
            return AgentMessage(
                agent_id=self.name,
                message_type="note_structured",
                payload=result
            )
            
        except Exception as e:
            logger.error(f"Note structuring error: {str(e)}")
            return self._create_error_response(message, str(e))
            
    def _organize_content_by_sections(
        self, 
        clinical_sections: Dict[str, Any],
        suggested_sections: List[str]
    ) -> Dict[str, Any]:
        """Organize content into standard clinical sections"""
        organized = {}
        
        # Map content to standard sections
        section_mapping = {
            "chief_complaint": ClinicalSection.CHIEF_COMPLAINT,
            "history_of_present_illness": ClinicalSection.HISTORY_PRESENT_ILLNESS,
            "past_medical_history": ClinicalSection.PAST_MEDICAL_HISTORY,
            "medications": ClinicalSection.MEDICATIONS,
            "allergies": ClinicalSection.ALLERGIES,
            "social_history": ClinicalSection.SOCIAL_HISTORY,
            "family_history": ClinicalSection.FAMILY_HISTORY,
            "review_of_systems": ClinicalSection.REVIEW_OF_SYSTEMS,
            "vital_signs": ClinicalSection.VITAL_SIGNS,
            "physical_examination": ClinicalSection.PHYSICAL_EXAMINATION,
            "assessment": ClinicalSection.ASSESSMENT,
            "plan": ClinicalSection.PLAN
        }
        
        for section_key, section_enum in section_mapping.items():
            if section_key in clinical_sections and clinical_sections[section_key]:
                content = clinical_sections[section_key]
                
                # Process content based on section type
                if section_enum == ClinicalSection.MEDICATIONS:
                    organized[section_enum.value] = self._process_medications(content)
                elif section_enum == ClinicalSection.VITAL_SIGNS:
                    organized[section_enum.value] = self._process_vital_signs(content)
                elif section_enum == ClinicalSection.HISTORY_PRESENT_ILLNESS:
                    organized[section_enum.value] = self._process_hpi(content)
                else:
                    organized[section_enum.value] = self._process_generic_section(content)
                    
        return organized
        
    def _process_medications(self, medications: Any) -> Dict[str, Any]:
        """Process medications into structured format"""
        if isinstance(medications, list):
            return {
                "items": medications,
                "count": len(medications),
                "formatted": self._format_medication_list(medications)
            }
        elif isinstance(medications, str):
            # Parse string into list if possible
            med_list = [m.strip() for m in medications.split(",") if m.strip()]
            return {
                "items": med_list,
                "count": len(med_list),
                "formatted": medications
            }
        else:
            return {
                "items": [],
                "count": 0,
                "formatted": "No current medications"
            }
            
    def _format_medication_list(self, medications: List[Any]) -> str:
        """Format medication list for display"""
        formatted_meds = []
        for med in medications:
            if isinstance(med, dict):
                med_str = med.get("name", "")
                if med.get("dose"):
                    med_str += f" {med['dose']}"
                if med.get("frequency"):
                    med_str += f" {med['frequency']}"
                formatted_meds.append(med_str)
            else:
                formatted_meds.append(str(med))
                
        return "\n".join([f"• {med}" for med in formatted_meds])
        
    def _process_vital_signs(self, vitals: Any) -> Dict[str, Any]:
        """Process vital signs into structured format"""
        if isinstance(vitals, dict):
            return {
                "values": vitals,
                "formatted": self._format_vital_signs(vitals),
                "abnormal_flags": self._check_abnormal_vitals(vitals)
            }
        else:
            return {
                "values": {},
                "formatted": str(vitals) if vitals else "Vital signs not documented",
                "abnormal_flags": []
            }
            
    def _format_vital_signs(self, vitals: Dict[str, Any]) -> str:
        """Format vital signs for display"""
        vital_parts = []
        
        vital_mapping = {
            "blood_pressure": "BP",
            "heart_rate": "HR",
            "respiratory_rate": "RR",
            "temperature": "Temp",
            "oxygen_saturation": "SpO2",
            "weight": "Weight",
            "height": "Height",
            "bmi": "BMI"
        }
        
        for key, label in vital_mapping.items():
            if key in vitals and vitals[key]:
                vital_parts.append(f"{label}: {vitals[key]}")
                
        return ", ".join(vital_parts) if vital_parts else "Vital signs not documented"
        
    def _check_abnormal_vitals(self, vitals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for abnormal vital signs"""
        abnormal = []
        
        # Define normal ranges
        normal_ranges = {
            "heart_rate": (60, 100),
            "systolic_bp": (90, 140),
            "diastolic_bp": (60, 90),
            "respiratory_rate": (12, 20),
            "oxygen_saturation": (95, 100),
            "temperature": (97.0, 99.0)
        }
        
        # Check blood pressure
        if "blood_pressure" in vitals:
            bp = vitals["blood_pressure"]
            if isinstance(bp, str) and "/" in bp:
                try:
                    systolic, diastolic = map(int, bp.split("/"))
                    if systolic < normal_ranges["systolic_bp"][0] or systolic > normal_ranges["systolic_bp"][1]:
                        abnormal.append({"vital": "systolic_bp", "value": systolic, "status": "abnormal"})
                    if diastolic < normal_ranges["diastolic_bp"][0] or diastolic > normal_ranges["diastolic_bp"][1]:
                        abnormal.append({"vital": "diastolic_bp", "value": diastolic, "status": "abnormal"})
                except:
                    pass
                    
        # Check other vitals
        for vital, (low, high) in normal_ranges.items():
            if vital in vitals:
                try:
                    value = float(vitals[vital])
                    if value < low or value > high:
                        abnormal.append({"vital": vital, "value": value, "status": "abnormal"})
                except:
                    pass
                    
        return abnormal
        
    def _process_hpi(self, hpi_content: Any) -> Dict[str, Any]:
        """Process history of present illness"""
        if isinstance(hpi_content, str):
            return {
                "narrative": hpi_content,
                "symptoms_mentioned": self._extract_symptoms(hpi_content),
                "timeline_mentioned": self._extract_timeline(hpi_content)
            }
        else:
            return {
                "narrative": str(hpi_content) if hpi_content else "",
                "symptoms_mentioned": [],
                "timeline_mentioned": []
            }
            
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptoms from HPI text"""
        symptom_keywords = [
            "pain", "ache", "fever", "cough", "nausea", "vomiting",
            "dizziness", "fatigue", "weakness", "shortness of breath",
            "headache", "chest pain", "abdominal pain", "swelling"
        ]
        
        found_symptoms = []
        text_lower = text.lower()
        for symptom in symptom_keywords:
            if symptom in text_lower:
                found_symptoms.append(symptom)
                
        return found_symptoms
        
    def _extract_timeline(self, text: str) -> List[str]:
        """Extract timeline references from HPI"""
        import re
        
        timeline_patterns = [
            r'\b\d+\s*(?:days?|weeks?|months?|years?)\s*ago\b',
            r'\b(?:yesterday|today|last\s+(?:week|month|year))\b',
            r'\b(?:since|for\s+the\s+past)\s+\d+\s*(?:days?|weeks?|months?)\b'
        ]
        
        timeline_refs = []
        for pattern in timeline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            timeline_refs.extend(matches)
            
        return timeline_refs
        
    def _process_generic_section(self, content: Any) -> Dict[str, Any]:
        """Process generic section content"""
        if isinstance(content, str):
            return {
                "content": content,
                "word_count": len(content.split()),
                "formatted": content
            }
        elif isinstance(content, list):
            return {
                "content": content,
                "item_count": len(content),
                "formatted": "\n".join([f"• {item}" for item in content])
            }
        else:
            return {
                "content": content,
                "formatted": str(content) if content else ""
            }
            
    async def _format_note(
        self,
        structured_sections: Dict[str, Any],
        note_format: NoteFormat
    ) -> str:
        """Format the structured sections according to chosen format"""
        if note_format == NoteFormat.SOAP:
            return self._format_soap_note(structured_sections)
        elif note_format == NoteFormat.BULLET:
            return self._format_bullet_note(structured_sections)
        elif note_format == NoteFormat.NARRATIVE:
            return await self._format_narrative_note(structured_sections)
        elif note_format == NoteFormat.EPIC_TEMPLATE:
            return self._format_epic_template(structured_sections)
        else:
            return self._format_soap_note(structured_sections)
            
    def _format_soap_note(self, sections: Dict[str, Any]) -> str:
        """Format as SOAP note"""
        soap_parts = []
        
        # Subjective
        subjective_content = []
        if "chief_complaint" in sections:
            subjective_content.append(f"Chief Complaint: {sections['chief_complaint']['formatted']}")
        if "history_present_illness" in sections:
            subjective_content.append(f"HPI: {sections['history_present_illness']['narrative']}")
        if "review_of_systems" in sections:
            subjective_content.append(f"ROS: {sections['review_of_systems']['formatted']}")
            
        if subjective_content:
            soap_parts.append("**SUBJECTIVE:**\n" + "\n".join(subjective_content))
            
        # Objective
        objective_content = []
        if "vital_signs" in sections:
            objective_content.append(f"Vital Signs: {sections['vital_signs']['formatted']}")
        if "physical_examination" in sections:
            objective_content.append(f"Physical Exam: {sections['physical_examination']['formatted']}")
            
        if objective_content:
            soap_parts.append("**OBJECTIVE:**\n" + "\n".join(objective_content))
            
        # Assessment
        if "assessment" in sections:
            soap_parts.append(f"**ASSESSMENT:**\n{sections['assessment']['formatted']}")
            
        # Plan
        plan_content = []
        if "plan" in sections:
            plan_content.append(sections['plan']['formatted'])
        if "medications" in sections:
            plan_content.append(f"Medications:\n{sections['medications']['formatted']}")
            
        if plan_content:
            soap_parts.append("**PLAN:**\n" + "\n".join(plan_content))
            
        return "\n\n".join(soap_parts)
        
    def _format_bullet_note(self, sections: Dict[str, Any]) -> str:
        """Format as bullet point note"""
        bullet_parts = []
        
        section_order = [
            ("Chief Complaint", "chief_complaint"),
            ("History of Present Illness", "history_present_illness"),
            ("Past Medical History", "past_medical_history"),
            ("Medications", "medications"),
            ("Allergies", "allergies"),
            ("Vital Signs", "vital_signs"),
            ("Physical Exam", "physical_examination"),
            ("Assessment", "assessment"),
            ("Plan", "plan")
        ]
        
        for title, key in section_order:
            if key in sections and sections[key]:
                bullet_parts.append(f"**{title}:**")
                content = sections[key].get('formatted', '')
                if not content.startswith('•'):
                    # Convert to bullet format if not already
                    lines = content.split('\n')
                    content = '\n'.join([f"• {line}" for line in lines if line.strip()])
                bullet_parts.append(content)
                
        return "\n\n".join(bullet_parts)
        
    async def _format_narrative_note(self, sections: Dict[str, Any]) -> str:
        """Format as narrative note using GPT-4"""
        try:
            # Prepare section content for GPT-4
            section_content = json.dumps(sections, indent=2)
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical scribe. Convert the structured clinical data into a flowing narrative clinical note. Use proper medical terminology and maintain a professional tone."
                    },
                    {
                        "role": "user",
                        "content": f"Convert this structured data into a narrative clinical note:\n{section_content}"
                    }
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error formatting narrative note: {str(e)}")
            # Fallback to SOAP format
            return self._format_soap_note(sections)
            
    def _format_epic_template(self, sections: Dict[str, Any]) -> str:
        """Format for Epic EHR template"""
        # Epic-specific formatting
        template_parts = []
        
        # Epic uses specific field markers
        if "chief_complaint" in sections:
            template_parts.append(f".chiefcomplaint\n{sections['chief_complaint']['formatted']}")
            
        if "history_present_illness" in sections:
            template_parts.append(f".hpi\n{sections['history_present_illness']['narrative']}")
            
        if "medications" in sections:
            template_parts.append(f".medications\n{sections['medications']['formatted']}")
            
        if "assessment" in sections:
            template_parts.append(f".assessment\n{sections['assessment']['formatted']}")
            
        if "plan" in sections:
            template_parts.append(f".plan\n{sections['plan']['formatted']}")
            
        return "\n\n".join(template_parts)
        
    def _generate_section_updates(self, structured_sections: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate progressive section updates for UI"""
        updates = []
        
        for section_key, section_data in structured_sections.items():
            update = {
                "section": section_key,
                "content": section_data.get("formatted", ""),
                "metadata": {
                    "word_count": section_data.get("word_count", 0),
                    "confidence": 0.95,  # Placeholder
                    "requires_review": False
                }
            }
            
            # Flag sections that may need review
            if section_key == "medications" and section_data.get("count", 0) > 10:
                update["metadata"]["requires_review"] = True
                update["metadata"]["review_reason"] = "Large number of medications"
                
            if section_key == "vital_signs" and section_data.get("abnormal_flags"):
                update["metadata"]["requires_review"] = True
                update["metadata"]["review_reason"] = "Abnormal vital signs detected"
                
            updates.append(update)
            
        return updates
        
    def _calculate_note_quality(self, structured_sections: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality metrics for the note"""
        total_sections = len(ClinicalSection)
        populated_sections = len(structured_sections)
        
        # Calculate word count
        total_words = 0
        for section_data in structured_sections.values():
            if "word_count" in section_data:
                total_words += section_data["word_count"]
            elif "formatted" in section_data:
                total_words += len(section_data["formatted"].split())
                
        # Check for required sections
        required_sections = ["chief_complaint", "assessment", "plan"]
        missing_required = [s for s in required_sections if s not in structured_sections]
        
        quality = {
            "completeness_score": populated_sections / total_sections,
            "populated_sections": populated_sections,
            "total_sections": total_sections,
            "word_count": total_words,
            "missing_required_sections": missing_required,
            "has_vital_signs": "vital_signs" in structured_sections,
            "has_medications": "medications" in structured_sections,
            "quality_grade": self._calculate_quality_grade(populated_sections, total_sections, missing_required)
        }
        
        return quality
        
    def _calculate_quality_grade(
        self,
        populated: int,
        total: int,
        missing_required: List[str]
    ) -> str:
        """Calculate overall quality grade"""
        completeness = populated / total
        
        if missing_required:
            return "C"  # Missing required sections
        elif completeness >= 0.8:
            return "A"  # Excellent
        elif completeness >= 0.6:
            return "B"  # Good
        else:
            return "C"  # Needs improvement
            
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create error response message"""
        return AgentMessage(
            agent_id=self.name,
            message_type="note_structuring_error",
            payload={
                "error": error,
                "original_request": original_message.payload,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    async def _format_existing_note(self, message: AgentMessage) -> AgentMessage:
        """Format an existing note in a different format"""
        try:
            note_data = message.payload.get("note_data")
            target_format = message.payload.get("format", "soap")
            
            formatted_note = await self._format_note(
                note_data,
                NoteFormat(target_format)
            )
            
            return AgentMessage(
                agent_id=self.name,
                message_type="note_reformatted",
                payload={
                    "formatted_note": formatted_note,
                    "format": target_format,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error reformatting note: {str(e)}")
            return self._create_error_response(message, str(e))


# Agent factory function
def create_batch_note_structuring_agent() -> BatchNoteStructuringAgent:
    """Create and return a batch note structuring agent instance"""
    return BatchNoteStructuringAgent()