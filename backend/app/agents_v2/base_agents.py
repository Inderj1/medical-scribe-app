"""Base agent definitions using OpenAI Agents SDK"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from agents import Agent, handoff, RunContextWrapper, HandoffInputData
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from app.agents_v2.models import (
    TranscriptionData, ClinicalData, StructuredNote, QAReport, SessionContext,
    MedicalEntity
)
from app.core.sse_manager import sse_manager
from app.db.session import SessionLocal
from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote

logger = logging.getLogger(__name__)


class MedicalScribeAgents:
    """Manages all medical scribe agents with proper handoffs"""
    
    def __init__(self):
        self.session_contexts: Dict[str, SessionContext] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents in reverse order (leaf nodes first)"""
        
        # Quality Assurance Agent - final agent in chain
        self.qa_agent = Agent(
            name="QualityAssuranceAgent",
            instructions=RECOMMENDED_PROMPT_PREFIX + """
You are a medical documentation quality assurance specialist.

Your responsibilities:
1. Validate clinical notes for completeness and accuracy
2. Check for missing critical information
3. Score the documentation quality
4. Provide specific improvement suggestions
5. Flag any potential safety issues

Return a comprehensive quality report to complete the workflow.
""",
            tools=[self.validate_note, self.generate_qa_report]
        )
        
        # Note Structuring Agent - formats clinical data
        self.note_structuring_agent = Agent(
            name="NoteStructuringAgent",
            instructions=RECOMMENDED_PROMPT_PREFIX + """
You are a medical note formatting specialist.

Your responsibilities:
1. Format clinical data into the requested note format (SOAP, bullet points, narrative)
2. Ensure proper medical terminology
3. Organize information logically
4. Maintain consistency in formatting
5. Include all relevant clinical information

When formatting is complete, hand off to the QualityAssuranceAgent for validation.
""",
            tools=[self.format_soap_note, self.format_bullet_points, self.format_narrative],
            handoffs=[
                handoff(
                    self.qa_agent,
                    on_handoff=self._on_note_structured,
                    tool_description_override="Hand off structured note for quality validation"
                )
            ]
        )
        
        # Clinical Analysis Agent - extracts medical information
        self.clinical_analysis_agent = Agent(
            name="ClinicalAnalysisAgent",
            instructions=RECOMMENDED_PROMPT_PREFIX + """
You are a clinical analysis specialist using advanced medical NLP.

Your responsibilities:
1. Extract all medical information from transcripts
2. Identify chief complaint, HPI, ROS, and other clinical sections
3. Extract medications, allergies, and vital signs
4. Identify medical entities (symptoms, diagnoses, procedures)
5. Organize information by clinical relevance

When analysis is complete, hand off to the NoteStructuringAgent for formatting.
""",
            tools=[self.extract_clinical_sections, self.identify_medical_entities, self.enhance_with_ehr],
            handoffs=[
                handoff(
                    self.note_structuring_agent,
                    on_handoff=self._on_analysis_complete,
                    input_filter=self._filter_clinical_data
                )
            ]
        )
        
        # Transcription Agent - processes audio and text
        self.transcription_agent = Agent(
            name="TranscriptionAgent",
            instructions=RECOMMENDED_PROMPT_PREFIX + """
You are a medical transcription specialist.

Your responsibilities:
1. Process audio files using Whisper API
2. Handle streaming text input with speaker attribution
3. Track speaker roles (patient, provider, nurse)
4. Maintain accurate word count and timestamps
5. Ensure transcript completeness

When transcription is complete, hand off to the ClinicalAnalysisAgent for medical content extraction.
""",
            tools=[self.process_audio_file, self.process_text_stream, self.identify_speaker_roles],
            handoffs=[
                handoff(
                    self.clinical_analysis_agent,
                    on_handoff=self._on_transcription_complete,
                    input_filter=handoff_filters.remove_all_tools
                )
            ]
        )
    
    # Tool implementations for Transcription Agent
    async def process_audio_file(self, ctx: RunContextWrapper, audio_path: str) -> str:
        """Process audio file with Whisper API"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Processing audio file for session {session_id}: {audio_path}")
        
        try:
            # Import here to avoid circular dependency
            from app.services.transcription import transcribe_audio_whisper
            
            # Transcribe audio
            transcript_data = await transcribe_audio_whisper(audio_path)
            
            # Store in session context
            if session_id in self.session_contexts:
                context = self.session_contexts[session_id]
                context.updated_at = datetime.utcnow()
            
            # Update database
            transcription_id = ctx.session_data.get("transcription_id")
            if transcription_id:
                await self._update_transcription_status(
                    transcription_id, 
                    "transcribed", 
                    transcript_data
                )
            
            return f"Successfully transcribed audio: {transcript_data['word_count']} words"
            
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise
    
    async def process_text_stream(self, ctx: RunContextWrapper, text_chunk: str, speaker_id: str = "SPEAKER_00") -> str:
        """Process streaming text input"""
        session_id = ctx.session_data.get("session_id")
        
        # Get or create session context
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = SessionContext(
                session_id=session_id,
                transcription_id=ctx.session_data.get("transcription_id", "")
            )
        
        context = self.session_contexts[session_id]
        
        # Append to transcript (simplified for now)
        # In production, implement proper text aggregation
        
        return f"Processed text chunk: {len(text_chunk)} characters"
    
    async def identify_speaker_roles(self, ctx: RunContextWrapper) -> Dict[str, str]:
        """Identify roles of different speakers"""
        # Simplified implementation
        return {
            "SPEAKER_00": "Healthcare Provider",
            "SPEAKER_01": "Patient"
        }
    
    # Tool implementations for Clinical Analysis Agent
    async def extract_clinical_sections(self, ctx: RunContextWrapper, transcript: str) -> ClinicalData:
        """Extract clinical sections using GPT-4"""
        logger.info("Extracting clinical sections from transcript")
        
        try:
            from openai import OpenAI
            from app.core.config import settings
            
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Call GPT-4 for extraction
            response = client.chat.completions.create(
                model=settings.GPT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract clinical information from the medical transcript."
                    },
                    {
                        "role": "user",
                        "content": transcript
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse and return clinical data
            data = response.choices[0].message.content
            
            return ClinicalData(
                session_id=ctx.session_data.get("session_id"),
                transcription_id=ctx.session_data.get("transcription_id"),
                **data
            )
            
        except Exception as e:
            logger.error(f"Error extracting clinical sections: {str(e)}")
            raise
    
    async def identify_medical_entities(self, ctx: RunContextWrapper, clinical_data: ClinicalData) -> List[MedicalEntity]:
        """Identify medical entities from clinical data"""
        # Simplified implementation
        entities = []
        
        if clinical_data.chief_complaint:
            entities.append(MedicalEntity(
                type="symptom",
                value=clinical_data.chief_complaint,
                confidence=0.9,
                section="chief_complaint"
            ))
        
        return entities
    
    async def enhance_with_ehr(self, ctx: RunContextWrapper, clinical_data: ClinicalData) -> ClinicalData:
        """Enhance clinical data with EHR information"""
        # Get EHR sections from context
        ehr_sections = ctx.session_data.get("ehr_sections", {})
        
        # Merge with clinical data
        if ehr_sections.get("medications") and not clinical_data.medications:
            clinical_data.medications = ehr_sections["medications"]
        
        if ehr_sections.get("allergies") and not clinical_data.allergies:
            clinical_data.allergies = ehr_sections["allergies"]
        
        return clinical_data
    
    # Tool implementations for Note Structuring Agent
    async def format_soap_note(self, ctx: RunContextWrapper, clinical_data: ClinicalData) -> StructuredNote:
        """Format clinical data as SOAP note"""
        sections = {
            "subjective": self._format_subjective(clinical_data),
            "objective": self._format_objective(clinical_data),
            "assessment": clinical_data.assessment or "",
            "plan": clinical_data.plan or ""
        }
        
        note_content = f"""SOAP NOTE

S (Subjective):
{sections['subjective']}

O (Objective):
{sections['objective']}

A (Assessment):
{sections['assessment']}

P (Plan):
{sections['plan']}"""
        
        return StructuredNote(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=ctx.session_data.get("transcription_id"),
            format_type="soap",
            note_content=note_content,
            sections=sections
        )
    
    async def format_bullet_points(self, ctx: RunContextWrapper, clinical_data: ClinicalData) -> StructuredNote:
        """Format clinical data as bullet points"""
        # Implementation for bullet point format
        pass
    
    async def format_narrative(self, ctx: RunContextWrapper, clinical_data: ClinicalData) -> StructuredNote:
        """Format clinical data as narrative"""
        # Implementation for narrative format
        pass
    
    # Tool implementations for QA Agent
    async def validate_note(self, ctx: RunContextWrapper, note: StructuredNote) -> Dict[str, Any]:
        """Validate clinical note for completeness"""
        missing_sections = []
        warnings = []
        
        # Check required sections
        required_sections = ["chief_complaint", "history_present_illness", "assessment", "plan"]
        for section in required_sections:
            if not note.sections.get(section):
                missing_sections.append(section)
        
        # Check for safety issues
        if "allergies" not in note.note_content.lower():
            warnings.append("No allergy information documented")
        
        return {
            "missing_sections": missing_sections,
            "warnings": warnings
        }
    
    async def generate_qa_report(self, ctx: RunContextWrapper, note: StructuredNote, validation: Dict[str, Any]) -> QAReport:
        """Generate comprehensive QA report"""
        # Calculate scores
        completeness_score = 1.0 - (len(validation["missing_sections"]) / 10.0)
        
        return QAReport(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=ctx.session_data.get("transcription_id"),
            overall_score=completeness_score,
            completeness_score=completeness_score,
            accuracy_score=0.9,  # Simplified
            clarity_score=0.85,  # Simplified
            missing_sections=validation["missing_sections"],
            warnings=validation["warnings"],
            suggestions=["Consider adding more detail to the assessment section"],
            approved=completeness_score > 0.8
        )
    
    # Handoff callbacks
    def _on_transcription_complete(self, ctx: RunContextWrapper, input_data: Optional[TranscriptionData] = None):
        """Called when transcription completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Transcription complete for session {session_id}")
        
        # Send SSE update
        if input_data and input_data.transcription_id:
            sse_manager.publish(
                f"transcription_{input_data.transcription_id}",
                {
                    "type": "transcription_complete",
                    "data": {
                        "word_count": input_data.word_count,
                        "speaker_count": len(input_data.speaker_roles)
                    }
                }
            )
    
    def _on_analysis_complete(self, ctx: RunContextWrapper, input_data: Optional[ClinicalData] = None):
        """Called when clinical analysis completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Clinical analysis complete for session {session_id}")
        
        # Send SSE updates for section completion
        if input_data and input_data.transcription_id:
            for section in input_data.sections:
                sse_manager.publish(
                    f"transcription_{input_data.transcription_id}",
                    {
                        "type": "section_complete",
                        "data": {
                            "section": section.name,
                            "content": section.content[:200] if section.content else "",
                            "confidence": section.confidence
                        }
                    }
                )
    
    def _on_note_structured(self, ctx: RunContextWrapper, input_data: Optional[StructuredNote] = None):
        """Called when note structuring completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Note structuring complete for session {session_id}")
        
        # Update database with structured note
        if input_data:
            asyncio.create_task(
                self._save_clinical_note(input_data)
            )
    
    # Input filters
    def _filter_clinical_data(self, input_data: HandoffInputData) -> HandoffInputData:
        """Filter conversation to only include clinical content"""
        # Keep only messages with medical content
        filtered_messages = []
        
        for msg in input_data.messages:
            # Simple filter - in production use more sophisticated NLP
            if any(term in msg.content.lower() for term in 
                   ["patient", "symptom", "diagnosis", "medication", "treatment"]):
                filtered_messages.append(msg)
        
        return HandoffInputData(
            messages=filtered_messages,
            context=input_data.context
        )
    
    # Helper methods
    def _format_subjective(self, clinical_data: ClinicalData) -> str:
        """Format subjective section"""
        parts = []
        
        if clinical_data.chief_complaint:
            parts.append(f"Chief Complaint: {clinical_data.chief_complaint}")
        
        if clinical_data.history_present_illness:
            parts.append(f"HPI: {clinical_data.history_present_illness}")
        
        if clinical_data.review_of_systems:
            parts.append("ROS: " + str(clinical_data.review_of_systems))
        
        return "\n".join(parts)
    
    def _format_objective(self, clinical_data: ClinicalData) -> str:
        """Format objective section"""
        parts = []
        
        if clinical_data.vital_signs:
            parts.append(f"Vital Signs: {clinical_data.vital_signs}")
        
        if clinical_data.physical_examination:
            parts.append(f"Physical Exam: {clinical_data.physical_examination}")
        
        if clinical_data.diagnostic_results:
            parts.append(f"Diagnostic Results: {clinical_data.diagnostic_results}")
        
        return "\n".join(parts)
    
    async def _update_transcription_status(self, transcription_id: str, status: str, data: Dict[str, Any]):
        """Update transcription in database"""
        async with SessionLocal() as db:
            transcription = db.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = status
                transcription.transcript = data.get("transcript", "")
                transcription.word_count = data.get("word_count", 0)
                db.commit()
    
    async def _save_clinical_note(self, note: StructuredNote):
        """Save clinical note to database"""
        async with SessionLocal() as db:
            clinical_note = ClinicalNote(
                transcription_id=note.transcription_id,
                format_type=note.format_type,
                content=note.note_content,
                sections=note.sections
            )
            db.add(clinical_note)
            db.commit()


# Global instance
medical_scribe_agents = MedicalScribeAgents()