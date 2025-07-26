"""Note Structuring Agent for organizing clinical documentation"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from app.agents.base import AgentOrchestrator

logger = logging.getLogger(__name__)


class NoteFormat(Enum):
    """Supported note formats"""
    LONG = "long"
    SHORT = "short"
    BULLET = "bullet"


class ClinicalSection(Enum):
    """Clinical note sections"""
    CHIEF_COMPLAINT = "chief_complaint"
    PRESENT_ILLNESS = "present_illness"
    PAST_MEDICAL_HISTORY = "past_medical_history"
    MEDICATIONS = "medications"
    ALLERGIES = "allergies"
    SOCIAL_HISTORY = "social_history"
    FAMILY_HISTORY = "family_history"
    REVIEW_OF_SYSTEMS = "review_of_systems"
    VITAL_SIGNS = "vital_signs"
    PHYSICAL_EXAM = "physical_exam"
    ASSESSMENT_PLAN = "assessment_plan"


class NoteStructuringAgent(BaseAgent):
    """Routes transcribed content to appropriate clinical note sections"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        super().__init__(
            name="NoteStructuringAgent",
            description="Structures clinical notes from analyzed transcriptions"
        )
        self.orchestrator = orchestrator
        
        # Session notes storage
        self.session_notes: Dict[str, Dict[str, Any]] = {}
        
        # Format preferences per session
        self.format_preferences: Dict[str, NoteFormat] = {}
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "handoff:clinical_analysis":
            # Process clinical analysis from context agent
            structured_note = await self._structure_clinical_note(message.payload)
            
            # Send structured note back to audio stream agent for client
            await self.orchestrator.send_message(
                "AudioStreamAgent",
                AgentMessage(
                    agent_id=self.name,
                    message_type="clinical:analysis",
                    payload=structured_note
                )
            )
            
        elif message.message_type == "format:update":
            # Update format preference
            session_id = message.payload.get("session_id")
            format_pref = message.payload.get("format", "long")
            self.format_preferences[session_id] = NoteFormat(format_pref)
            
        elif message.message_type == "encounter:started":
            # Initialize note structure for new encounter
            self._init_encounter_note(message.payload)
            
        elif message.message_type == "encounter:ended":
            # Finalize and clean up encounter notes
            await self._finalize_encounter_note(message.payload)
            
        return None
        
    async def _structure_clinical_note(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Structure the clinical analysis into appropriate note sections"""
        session_id = analysis_data.get("session_id")
        clinical_analysis = analysis_data.get("clinical_analysis", {})
        suggested_sections = analysis_data.get("suggested_sections", [])
        
        # Get or create session note
        if session_id not in self.session_notes:
            self._init_session_note(session_id)
            
        note = self.session_notes[session_id]
        format_pref = self.format_preferences.get(session_id, NoteFormat.LONG)
        
        # Update relevant sections based on analysis
        updates = {}
        
        # Chief Complaint
        if "chief_complaint" in suggested_sections and clinical_analysis.get("chief_complaint"):
            updates["chief_complaint"] = self._format_content(
                clinical_analysis["chief_complaint"],
                ClinicalSection.CHIEF_COMPLAINT,
                format_pref
            )
            
        # History of Present Illness
        if "present_illness" in suggested_sections and clinical_analysis.get("symptoms"):
            hpi_content = self._build_hpi(clinical_analysis["symptoms"], format_pref)
            updates["present_illness"] = hpi_content
            
        # Medications
        if "medications" in suggested_sections and clinical_analysis.get("medications"):
            med_content = self._format_medications(clinical_analysis["medications"], format_pref)
            updates["medications"] = med_content
            
        # Vital Signs
        if "vital_signs" in suggested_sections and clinical_analysis.get("vital_signs"):
            vitals_content = self._format_vital_signs(clinical_analysis["vital_signs"], format_pref)
            updates["vital_signs"] = vitals_content
            
        # Physical Exam
        if "physical_exam" in suggested_sections and clinical_analysis.get("physical_exam"):
            exam_content = self._format_content(
                clinical_analysis["physical_exam"],
                ClinicalSection.PHYSICAL_EXAM,
                format_pref
            )
            updates["physical_exam"] = exam_content
            
        # Assessment & Plan
        if "assessment_plan" in suggested_sections:
            ap_content = self._build_assessment_plan(
                clinical_analysis.get("assessment", ""),
                clinical_analysis.get("plan", ""),
                format_pref
            )
            updates["assessment_plan"] = ap_content
            
        # Apply updates to note
        for section, content in updates.items():
            self._update_section(session_id, section, content)
            
        return {
            "session_id": session_id,
            "sections_updated": list(updates.keys()),
            "updates": updates,
            "full_note": self._get_formatted_note(session_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _format_content(self, content: str, section: ClinicalSection, format_pref: NoteFormat) -> str:
        """Format content based on preference"""
        if not content:
            return ""
            
        if format_pref == NoteFormat.BULLET:
            # Convert to bullet points
            lines = content.split('. ')
            return "\n".join([f"• {line.strip()}" for line in lines if line.strip()])
            
        elif format_pref == NoteFormat.SHORT:
            # Truncate to key points
            sentences = content.split('. ')
            return '. '.join(sentences[:2]) + '.' if len(sentences) > 2 else content
            
        else:  # LONG format
            return content
            
    def _build_hpi(self, symptoms: List[Any], format_pref: NoteFormat) -> str:
        """Build History of Present Illness section"""
        if not symptoms:
            return ""
            
        if format_pref == NoteFormat.BULLET:
            hpi_lines = []
            for symptom in symptoms:
                if isinstance(symptom, dict):
                    line = f"• {symptom.get('name', '')}"
                    if symptom.get('onset'):
                        line += f" - Onset: {symptom['onset']}"
                    if symptom.get('severity'):
                        line += f" - Severity: {symptom['severity']}"
                    hpi_lines.append(line)
                else:
                    hpi_lines.append(f"• {symptom}")
            return "\n".join(hpi_lines)
            
        else:
            # Narrative format
            symptom_descriptions = []
            for symptom in symptoms:
                if isinstance(symptom, dict):
                    desc = symptom.get('name', '')
                    if symptom.get('onset'):
                        desc += f" starting {symptom['onset']}"
                    if symptom.get('severity'):
                        desc += f" ({symptom['severity']} severity)"
                    symptom_descriptions.append(desc)
                else:
                    symptom_descriptions.append(str(symptom))
                    
            return f"Patient presents with {', '.join(symptom_descriptions)}."
            
    def _format_medications(self, medications: List[Any], format_pref: NoteFormat) -> str:
        """Format medications list"""
        if not medications:
            return "No current medications."
            
        if format_pref == NoteFormat.BULLET or format_pref == NoteFormat.SHORT:
            med_lines = []
            for med in medications:
                if isinstance(med, dict):
                    line = f"• {med.get('name', '')}"
                    if med.get('dose'):
                        line += f" {med['dose']}"
                    if med.get('frequency'):
                        line += f" {med['frequency']}"
                    med_lines.append(line)
                else:
                    med_lines.append(f"• {med}")
            return "\n".join(med_lines)
            
        else:  # LONG format
            med_descriptions = []
            for med in medications:
                if isinstance(med, dict):
                    desc = f"{med.get('name', '')}"
                    if med.get('dose'):
                        desc += f" {med['dose']}"
                    if med.get('frequency'):
                        desc += f" {med['frequency']}"
                    if med.get('indication'):
                        desc += f" for {med['indication']}"
                    med_descriptions.append(desc)
                else:
                    med_descriptions.append(str(med))
                    
            return "Current medications include: " + "; ".join(med_descriptions) + "."
            
    def _format_vital_signs(self, vitals: Dict[str, Any], format_pref: NoteFormat) -> str:
        """Format vital signs"""
        if not vitals:
            return ""
            
        vital_parts = []
        
        if "blood_pressure" in vitals:
            vital_parts.append(f"BP: {vitals['blood_pressure']}")
        if "heart_rate" in vitals:
            vital_parts.append(f"HR: {vitals['heart_rate']}")
        if "temperature" in vitals:
            vital_parts.append(f"Temp: {vitals['temperature']}")
        if "respiratory_rate" in vitals:
            vital_parts.append(f"RR: {vitals['respiratory_rate']}")
        if "oxygen_saturation" in vitals:
            vital_parts.append(f"SpO2: {vitals['oxygen_saturation']}")
            
        if format_pref == NoteFormat.BULLET:
            return "\n".join([f"• {v}" for v in vital_parts])
        else:
            return ", ".join(vital_parts)
            
    def _build_assessment_plan(self, assessment: str, plan: str, format_pref: NoteFormat) -> str:
        """Build Assessment & Plan section"""
        content = []
        
        if assessment:
            content.append(f"Assessment: {assessment}")
            
        if plan:
            if format_pref == NoteFormat.BULLET:
                plan_items = plan.split('. ')
                plan_formatted = "\n".join([f"• {item.strip()}" for item in plan_items if item.strip()])
                content.append(f"Plan:\n{plan_formatted}")
            else:
                content.append(f"Plan: {plan}")
                
        return "\n\n".join(content)
        
    def _update_section(self, session_id: str, section: str, content: str):
        """Update a specific section of the note"""
        if session_id not in self.session_notes:
            self._init_session_note(session_id)
            
        note = self.session_notes[session_id]
        
        # Append or replace content based on section type
        if section in ["chief_complaint", "vital_signs"]:
            # Replace for these sections
            note["sections"][section] = content
        else:
            # Append for cumulative sections
            if section not in note["sections"]:
                note["sections"][section] = ""
            if note["sections"][section]:
                note["sections"][section] += "\n" + content
            else:
                note["sections"][section] = content
                
        note["last_updated"] = datetime.utcnow().isoformat()
        
    def _get_formatted_note(self, session_id: str) -> str:
        """Get the complete formatted note"""
        if session_id not in self.session_notes:
            return ""
            
        note = self.session_notes[session_id]
        sections = note["sections"]
        
        # Build formatted note
        formatted_parts = []
        
        # Order sections appropriately
        section_order = [
            ("Chief Complaint", "chief_complaint"),
            ("History of Present Illness", "present_illness"),
            ("Past Medical History", "past_medical_history"),
            ("Medications", "medications"),
            ("Allergies", "allergies"),
            ("Social History", "social_history"),
            ("Family History", "family_history"),
            ("Review of Systems", "review_of_systems"),
            ("Vital Signs", "vital_signs"),
            ("Physical Examination", "physical_exam"),
            ("Assessment & Plan", "assessment_plan")
        ]
        
        for title, key in section_order:
            if key in sections and sections[key]:
                formatted_parts.append(f"**{title}:**\n{sections[key]}")
                
        return "\n\n".join(formatted_parts)
        
    def _init_session_note(self, session_id: str):
        """Initialize a new session note"""
        self.session_notes[session_id] = {
            "sections": {},
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    def _init_encounter_note(self, encounter_data: Dict[str, Any]):
        """Initialize note for new encounter"""
        session_id = encounter_data.get("session_id")
        self._init_session_note(session_id)
        
        # Set default format
        self.format_preferences[session_id] = NoteFormat.LONG
        
    async def _finalize_encounter_note(self, encounter_data: Dict[str, Any]):
        """Finalize note when encounter ends"""
        session_id = encounter_data.get("session_id")
        
        if session_id in self.session_notes:
            # Log final note
            final_note = self._get_formatted_note(session_id)
            logger.info(f"Final note for session {session_id}:\n{final_note}")
            
            # Clean up
            del self.session_notes[session_id]
            
        if session_id in self.format_preferences:
            del self.format_preferences[session_id]