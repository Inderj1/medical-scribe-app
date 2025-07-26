"""Clinical Context Agent for medical understanding and entity extraction"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

from app.agents.base import BaseAgent, AgentMessage, AgentHandoff
from app.agents.base import AgentOrchestrator
from app.services.clinical_nlp import ClinicalNLP
from anthropic import AsyncAnthropic
from app.core.config import settings

logger = logging.getLogger(__name__)


class ClinicalContextAgent(BaseAgent):
    """Processes transcriptions for medical context and entity extraction"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        super().__init__(
            name="ClinicalContextAgent",
            description="Extracts medical entities and maintains clinical context"
        )
        self.orchestrator = orchestrator
        self.clinical_nlp = ClinicalNLP()
        self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Session context storage
        self.session_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Medical entity patterns
        self._init_medical_patterns()
        
    def _init_medical_patterns(self):
        """Initialize regex patterns for medical entity detection"""
        self.patterns = {
            "medications": re.compile(
                r'\b(?:mg|mcg|ml|tablet|capsule|injection|dose|daily|twice|three times)\b',
                re.IGNORECASE
            ),
            "vitals": re.compile(
                r'\b(?:blood pressure|bp|heart rate|pulse|temperature|temp|oxygen|spo2|weight|height)\b',
                re.IGNORECASE
            ),
            "symptoms": re.compile(
                r'\b(?:pain|ache|fever|cough|nausea|vomiting|dizziness|fatigue|shortness of breath)\b',
                re.IGNORECASE
            ),
            "diagnoses": re.compile(
                r'\b(?:diagnosis|diagnosed|condition|disease|disorder|syndrome)\b',
                re.IGNORECASE
            )
        }
        
    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "transcription:complete":
            # Process complete transcription
            analysis = await self._analyze_transcription(message.payload)
            
            # Send analysis to note structuring agent
            return AgentHandoff.create_handoff_message(
                from_agent=self.name,
                to_agent="NoteStructuringAgent",
                data=analysis,
                handoff_type="clinical_analysis"
            )
            
        elif message.message_type == "encounter:started":
            # Initialize context for new encounter
            self._init_encounter_context(message.payload)
            
        elif message.message_type == "encounter:ended":
            # Clean up encounter context
            self._cleanup_encounter_context(message.payload)
            
        return None
        
    async def _analyze_transcription(self, transcription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze transcription for medical context"""
        text = transcription_data.get("text", "")
        session_id = transcription_data.get("session_id")
        
        # Get or create session context
        context = self.session_contexts.get(session_id, {})
        
        # Extract medical entities using NLP
        entities = await self.clinical_nlp.extract_entities(text)
        
        # Enhance with Claude for deeper understanding
        enhanced_analysis = await self._enhance_with_claude(text, entities, context)
        
        # Update session context
        self._update_context(session_id, enhanced_analysis)
        
        return {
            "session_id": session_id,
            "original_text": text,
            "entities": entities,
            "clinical_analysis": enhanced_analysis,
            "suggested_sections": self._suggest_sections(enhanced_analysis),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _enhance_with_claude(self, text: str, entities: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude to enhance clinical understanding"""
        try:
            # Build context prompt
            context_prompt = self._build_context_prompt(context)
            
            response = await self.anthropic.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                temperature=0.3,
                system="""You are a medical scribe AI assistant. Analyze the transcribed medical conversation and extract:
                1. Chief complaint
                2. Symptoms with onset and severity
                3. Medications mentioned (name, dose, frequency)
                4. Vital signs
                5. Physical exam findings
                6. Assessment and plan
                7. Follow-up instructions
                
                Respond in JSON format with these sections. Be precise and use medical terminology appropriately.""",
                messages=[
                    {
                        "role": "user",
                        "content": f"{context_prompt}\n\nTranscription: {text}\n\nExtracted entities: {entities}"
                    }
                ]
            )
            
            # Parse Claude's response
            import json
            analysis = json.loads(response.content[0].text)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error enhancing with Claude: {str(e)}")
            # Fallback to basic analysis
            return self._basic_analysis(text, entities)
            
    def _build_context_prompt(self, context: Dict[str, Any]) -> str:
        """Build context prompt for Claude"""
        if not context:
            return "This is a new medical encounter."
            
        prompt_parts = ["Previous context from this encounter:"]
        
        if "chief_complaint" in context:
            prompt_parts.append(f"Chief complaint: {context['chief_complaint']}")
            
        if "medications" in context:
            prompt_parts.append(f"Current medications: {', '.join(context['medications'])}")
            
        if "diagnoses" in context:
            prompt_parts.append(f"Working diagnoses: {', '.join(context['diagnoses'])}")
            
        return "\n".join(prompt_parts)
        
    def _basic_analysis(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback basic analysis without Claude"""
        analysis = {
            "chief_complaint": "",
            "symptoms": [],
            "medications": entities.get("medications", []),
            "vital_signs": {},
            "physical_exam": "",
            "assessment": "",
            "plan": "",
            "follow_up": ""
        }
        
        # Use regex patterns to identify sections
        text_lower = text.lower()
        
        # Look for symptoms
        if self.patterns["symptoms"].search(text_lower):
            symptoms = self.patterns["symptoms"].findall(text_lower)
            analysis["symptoms"] = list(set(symptoms))
            
        # Look for vital signs
        if self.patterns["vitals"].search(text_lower):
            # Extract vital sign mentions
            vital_matches = self.patterns["vitals"].findall(text_lower)
            analysis["vital_signs"]["mentioned"] = list(set(vital_matches))
            
        return analysis
        
    def _suggest_sections(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest which sections to update based on analysis"""
        suggestions = []
        
        if analysis.get("chief_complaint"):
            suggestions.append("chief_complaint")
            
        if analysis.get("symptoms"):
            suggestions.append("present_illness")
            
        if analysis.get("medications"):
            suggestions.append("medications")
            
        if analysis.get("vital_signs"):
            suggestions.append("vital_signs")
            
        if analysis.get("physical_exam"):
            suggestions.append("physical_exam")
            
        if analysis.get("assessment") or analysis.get("plan"):
            suggestions.append("assessment_plan")
            
        return suggestions
        
    def _update_context(self, session_id: str, analysis: Dict[str, Any]):
        """Update session context with new information"""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {}
            
        context = self.session_contexts[session_id]
        
        # Update chief complaint if found
        if analysis.get("chief_complaint"):
            context["chief_complaint"] = analysis["chief_complaint"]
            
        # Accumulate medications
        if "medications" not in context:
            context["medications"] = []
        context["medications"].extend(analysis.get("medications", []))
        context["medications"] = list(set(context["medications"]))  # Deduplicate
        
        # Update diagnoses
        if "diagnoses" not in context:
            context["diagnoses"] = []
        if analysis.get("assessment"):
            context["diagnoses"].append(analysis["assessment"])
            
    def _init_encounter_context(self, encounter_data: Dict[str, Any]):
        """Initialize context for a new encounter"""
        session_id = encounter_data.get("session_id")
        self.session_contexts[session_id] = {
            "encounter_id": encounter_data.get("encounter_id"),
            "patient_id": encounter_data.get("patient_id"),
            "encounter_type": encounter_data.get("encounter_type", "general"),
            "start_time": datetime.utcnow().isoformat(),
            "transcription_count": 0
        }
        
    def _cleanup_encounter_context(self, encounter_data: Dict[str, Any]):
        """Clean up context when encounter ends"""
        session_id = encounter_data.get("session_id")
        if session_id in self.session_contexts:
            # Log final context for debugging
            logger.info(f"Final context for session {session_id}: {self.session_contexts[session_id]}")
            del self.session_contexts[session_id]