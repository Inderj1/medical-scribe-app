import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from anthropic import Anthropic

from app.core.config import settings
from app.services.enhanced_transcription_service import TranscriptionResult

logger = logging.getLogger(__name__)


@dataclass
class ClinicalAnalysis:
    transcription_id: str
    entities: Dict[str, List]
    suggested_section: Dict[str, Any]
    confidence: float
    contextual_info: Dict
    timestamp: str


class EnhancedAnthropicClient:
    def __init__(self, api_key: str = None):
        self.client = Anthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-haiku-20240307"  # Fast model for real-time processing
        
    async def analyze_clinical_text(self, transcription_result: TranscriptionResult, 
                                  context: List[str] = None,
                                  note_format: str = "long") -> ClinicalAnalysis:
        """Analyze clinical text with enhanced entity extraction"""
        
        context_text = ""
        if context:
            context_text = f"Previous context: {' '.join(context[-3:])}\n\n"  # Last 3 transcriptions
        
        format_instructions = self._get_format_instructions(note_format)
        
        prompt = f"""
        {context_text}Current transcription: "{transcription_result.text}"
        
        As a medical NLP specialist, extract and analyze the following. Format all text outputs according to this preference: {format_instructions}
        
        1. CLINICAL ENTITIES:
           - Symptoms (with severity/duration if mentioned)
           - Medications (with dosages/frequency)
           - Vital signs (with values and units)
           - Procedures (current or planned)
           - Medical conditions (current or historical)
           - Measurements (lab values, physical measurements)
        
        2. SECTION CLASSIFICATION:
           Determine the most appropriate clinical section:
           - chief_complaint: Main reason for visit
           - present_illness: Current symptoms and history
           - medications: Current medications and changes
           - physical_exam: Examination findings
           - assessment_plan: Diagnosis and treatment plans
           - medical_history: Past medical history
        
        3. CONFIDENCE ASSESSMENT:
           Rate confidence (0.0-1.0) for section classification
        
        4. CONTEXTUAL ANALYSIS:
           - Relationships to previous statements
           - Clinical significance
           - Urgency indicators
           - Key insights
        
        Respond in JSON format:
        {{
            "entities": {{
                "symptoms": [{{ "text": "...", "severity": "...", "duration": "...", "formatted_text": "..." }}],
                "medications": [{{ "name": "...", "dosage": "...", "frequency": "...", "formatted_text": "..." }}],
                "vitals": [{{ "type": "...", "value": "...", "unit": "...", "normal_range": "...", "formatted_text": "..." }}],
                "procedures": [{{ "name": "...", "status": "...", "formatted_text": "..." }}],
                "conditions": [{{ "name": "...", "status": "...", "formatted_text": "..." }}],
                "measurements": [{{ "type": "...", "value": "...", "unit": "...", "formatted_text": "..." }}]
            }},
            "section_classification": {{
                "primary_section": "...",
                "confidence": 0.0,
                "reasoning": "...",
                "alternative_sections": ["..."]
            }},
            "contextual_analysis": {{
                "clinical_significance": "low|medium|high",
                "urgency": "routine|urgent|critical",
                "relationships": ["..."],
                "key_insights": ["..."],
                "missing_information": ["..."],
                "follow_up_questions": ["..."]
            }},
            "formatted_content": {{
                "summary": "...",
                "detailed_notes": "..."
            }}
        }}
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            analysis_data = json.loads(response_text)
            
            # Enhance with segment-level analysis if available
            if transcription_result.segments:
                analysis_data = self._enhance_with_segments(
                    analysis_data, 
                    transcription_result.segments
                )
            
            return ClinicalAnalysis(
                transcription_id=transcription_result.id,
                entities=analysis_data["entities"],
                suggested_section=analysis_data["section_classification"],
                confidence=analysis_data["section_classification"]["confidence"],
                contextual_info=analysis_data["contextual_analysis"],
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Clinical analysis failed for {transcription_result.id}: {str(e)}")
            # Return fallback analysis
            return self._create_fallback_analysis(transcription_result)
    
    def _get_format_instructions(self, note_format: str) -> str:
        """Get format instructions based on user preference"""
        format_map = {
            'long': 'Write detailed, complete sentences with comprehensive information. Include all relevant details and context.',
            'short': 'Write concise sentences with key information only. Be brief but clear.',
            'bullet': 'Use bullet points for each item. Start each point with a dash (-).'
        }
        return format_map.get(note_format, format_map['long'])
    
    def _enhance_with_segments(self, analysis_data: Dict, segments: List[Dict]) -> Dict:
        """Enhance analysis with segment-level information"""
        # Add timestamp information to entities
        for entity_type, entities in analysis_data["entities"].items():
            for entity in entities:
                # Find which segment contains this entity
                entity_text = entity.get("text", "").lower()
                for segment in segments:
                    if entity_text in segment["text"].lower():
                        entity["segment_start"] = segment["start"]
                        entity["segment_end"] = segment["end"]
                        entity["segment_confidence"] = segment["confidence"]
                        break
        
        return analysis_data
    
    def _create_fallback_analysis(self, transcription_result: TranscriptionResult) -> ClinicalAnalysis:
        """Create fallback analysis when AI fails"""
        return ClinicalAnalysis(
            transcription_id=transcription_result.id,
            entities={
                "symptoms": [], 
                "medications": [], 
                "vitals": [], 
                "procedures": [], 
                "conditions": [], 
                "measurements": []
            },
            suggested_section={
                "primary_section": "present_illness",
                "confidence": 0.5,
                "reasoning": "Fallback classification due to analysis error",
                "alternative_sections": []
            },
            confidence=0.5,
            contextual_info={
                "clinical_significance": "medium",
                "urgency": "routine",
                "relationships": [],
                "key_insights": [],
                "missing_information": [],
                "follow_up_questions": []
            },
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def generate_clinical_summary(self, analyses: List[ClinicalAnalysis], 
                                      note_format: str = "long") -> Dict[str, Any]:
        """Generate a comprehensive clinical summary from multiple analyses"""
        if not analyses:
            return {"summary": "", "sections": {}}
        
        # Aggregate entities across all analyses
        all_entities = {
            "symptoms": [],
            "medications": [],
            "vitals": [],
            "procedures": [],
            "conditions": [],
            "measurements": []
        }
        
        for analysis in analyses:
            for entity_type, entities in analysis.entities.items():
                all_entities[entity_type].extend(entities)
        
        format_instructions = self._get_format_instructions(note_format)
        
        prompt = f"""
        Based on the following clinical entities extracted from a medical consultation, 
        generate a comprehensive clinical note. Format according to: {format_instructions}
        
        Entities:
        {json.dumps(all_entities, indent=2)}
        
        Generate a structured clinical note with these sections:
        1. Chief Complaint
        2. History of Present Illness
        3. Review of Systems
        4. Physical Examination
        5. Assessment
        6. Plan
        
        Respond in JSON format:
        {{
            "summary": "Brief overview of the encounter",
            "sections": {{
                "chief_complaint": "...",
                "history_present_illness": "...",
                "review_of_systems": "...",
                "physical_examination": "...",
                "assessment": "...",
                "plan": "..."
            }},
            "key_findings": ["..."],
            "action_items": ["..."]
        }}
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary_data = json.loads(response.content[0].text)
            return summary_data
            
        except Exception as e:
            logger.error(f"Failed to generate clinical summary: {str(e)}")
            return {"summary": "Error generating summary", "sections": {}}