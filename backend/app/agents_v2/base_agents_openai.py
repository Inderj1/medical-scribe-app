"""Base agent definitions using OpenAI Agents SDK patterns"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from functools import wraps
import json

from app.agents_v2.models import (
    TranscriptionData, ClinicalData, StructuredNote, QAReport, SessionContext,
    MedicalEntity, ClinicalSection
)
from app.core.sse_manager import sse_manager
from app.db.session import SessionLocal
from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote

logger = logging.getLogger(__name__)


# Agent SDK pattern implementation
@dataclass
class HandoffInputData:
    """Input data for handoff between agents"""
    messages: List[Dict[str, Any]]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext:
    """Context for agent execution"""
    session_data: Dict[str, Any]
    messages: List[Dict[str, Any]]
    current_agent: Optional['Agent'] = None
    trace: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RunResult:
    """Result from agent execution"""
    agent: 'Agent'
    messages: List[Dict[str, Any]]
    trace: List[Dict[str, Any]]
    session_data: Dict[str, Any]


@dataclass
class Handoff:
    """Handoff configuration between agents"""
    agent: 'Agent'
    on_handoff: Optional[Callable] = None
    input_filter: Optional[Callable] = None
    tool_description_override: Optional[str] = None


@dataclass
class Agent:
    """Agent with tools and handoffs"""
    name: str
    instructions: str
    tools: List[Callable] = field(default_factory=list)
    handoffs: List[Handoff] = field(default_factory=list)
    
    async def execute_tool(self, tool_name: str, context: RunContext, **kwargs) -> Any:
        """Execute a tool by name"""
        for tool in self.tools:
            if tool.__name__ == tool_name:
                # Inject context into tool execution
                return await tool(context, **kwargs)
        raise ValueError(f"Tool {tool_name} not found")


def handoff(agent: Agent, on_handoff: Optional[Callable] = None, 
           input_filter: Optional[Callable] = None,
           tool_description_override: Optional[str] = None) -> Handoff:
    """Create a handoff configuration"""
    return Handoff(
        agent=agent,
        on_handoff=on_handoff,
        input_filter=input_filter,
        tool_description_override=tool_description_override
    )


# Input filter helpers
class handoff_filters:
    @staticmethod
    def remove_all_tools(input_data: HandoffInputData) -> HandoffInputData:
        """Remove all tool calls from conversation history"""
        filtered_messages = [
            msg for msg in input_data.messages
            if msg.get("role") != "tool"
        ]
        return HandoffInputData(messages=filtered_messages, context=input_data.context)
    
    @staticmethod
    def keep_last_n_messages(n: int):
        """Keep only the last n messages"""
        def filter_func(input_data: HandoffInputData) -> HandoffInputData:
            return HandoffInputData(
                messages=input_data.messages[-n:],
                context=input_data.context
            )
        return filter_func


# Recommended prompt prefix for better agent behavior
RECOMMENDED_PROMPT_PREFIX = """You are a specialized agent in a medical documentation workflow.
Follow these principles:
1. Focus on your specific responsibilities
2. Provide clear, structured outputs
3. Hand off to the next agent when your task is complete
4. Maintain patient privacy and medical accuracy

"""


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
    async def process_audio_file(self, ctx: RunContext, audio_path: str) -> Dict[str, Any]:
        """Process audio file with Whisper API"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Processing audio file for session {session_id}: {audio_path}")
        
        try:
            # Import here to avoid circular dependency
            from app.services.transcription import transcribe_audio_whisper
            
            # Transcribe audio
            transcript_data = await transcribe_audio_whisper(audio_path)
            
            # Create TranscriptionData object
            transcription_data = TranscriptionData(
                session_id=session_id,
                transcription_id=ctx.session_data.get("transcription_id"),
                transcript=transcript_data.get("transcript", ""),
                speaker_segments=transcript_data.get("speaker_segments", []),
                speaker_roles=transcript_data.get("speaker_roles", {}),
                word_count=transcript_data.get("word_count", 0),
                audio_duration=transcript_data.get("duration")
            )
            
            # Store in session context
            if session_id in self.session_contexts:
                context = self.session_contexts[session_id]
                context.updated_at = datetime.utcnow()
            
            # Update database
            if transcription_data.transcription_id:
                await self._update_transcription_status(
                    transcription_data.transcription_id, 
                    "transcribed", 
                    transcript_data
                )
            
            # Store transcription data in context for next agent
            ctx.session_data["transcription_data"] = transcription_data
            
            return {
                "status": "success",
                "message": f"Successfully transcribed audio: {transcription_data.word_count} words",
                "transcript_preview": transcription_data.transcript[:200] + "..." if len(transcription_data.transcript) > 200 else transcription_data.transcript
            }
            
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process audio: {str(e)}"
            }
    
    async def process_text_stream(self, ctx: RunContext, text_chunk: str, speaker_id: str = "SPEAKER_00") -> Dict[str, Any]:
        """Process streaming text input"""
        session_id = ctx.session_data.get("session_id")
        
        # Get or create session context
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = SessionContext(
                session_id=session_id,
                transcription_id=ctx.session_data.get("transcription_id", "")
            )
        
        context = self.session_contexts[session_id]
        
        # In production, implement proper text aggregation
        # For now, just acknowledge receipt
        
        return {
            "status": "success",
            "message": f"Processed text chunk: {len(text_chunk)} characters from {speaker_id}"
        }
    
    async def identify_speaker_roles(self, ctx: RunContext) -> Dict[str, str]:
        """Identify roles of different speakers"""
        # In production, use more sophisticated speaker role identification
        # For now, return default mapping
        return {
            "SPEAKER_00": "Healthcare Provider",
            "SPEAKER_01": "Patient",
            "SPEAKER_02": "Nurse/Assistant"
        }
    
    # Tool implementations for Clinical Analysis Agent
    async def extract_clinical_sections(self, ctx: RunContext) -> ClinicalData:
        """Extract clinical sections using GPT-4"""
        logger.info("Extracting clinical sections from transcript")
        
        # Get transcription data from context
        transcription_data = ctx.session_data.get("transcription_data")
        if not transcription_data or not isinstance(transcription_data, TranscriptionData):
            raise ValueError("No transcription data found in context")
        
        try:
            from openai import OpenAI
            from app.core.config import settings
            
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Prepare prompt for clinical extraction
            system_prompt = """You are a medical AI assistant. Extract clinical information from the transcript and return it as JSON with these fields:
            - chief_complaint: The main reason for the visit
            - history_present_illness: Detailed history of current illness
            - review_of_systems: Any systems review mentioned
            - past_medical_history: Past medical conditions
            - medications: Current medications (as array)
            - allergies: Known allergies (as array)
            - social_history: Social history details
            - family_history: Family medical history
            - physical_examination: Physical exam findings (as object)
            - vital_signs: Vital signs (as object)
            - assessment: Clinical assessment
            - plan: Treatment plan
            
            Return only valid JSON."""
            
            # Call GPT-4 for extraction
            response = client.chat.completions.create(
                model=settings.GPT_MODEL if hasattr(settings, 'GPT_MODEL') else "gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription_data.transcript}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse response
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Create ClinicalData object
            clinical_data = ClinicalData(
                session_id=ctx.session_data.get("session_id"),
                transcription_id=transcription_data.transcription_id,
                chief_complaint=extracted_data.get("chief_complaint"),
                history_present_illness=extracted_data.get("history_present_illness"),
                review_of_systems=extracted_data.get("review_of_systems"),
                past_medical_history=extracted_data.get("past_medical_history"),
                medications=extracted_data.get("medications", []),
                allergies=extracted_data.get("allergies", []),
                social_history=extracted_data.get("social_history"),
                family_history=extracted_data.get("family_history"),
                physical_examination=extracted_data.get("physical_examination"),
                vital_signs=extracted_data.get("vital_signs"),
                assessment=extracted_data.get("assessment"),
                plan=extracted_data.get("plan")
            )
            
            # Store in context for next agent
            ctx.session_data["clinical_data"] = clinical_data
            
            return clinical_data
            
        except Exception as e:
            logger.error(f"Error extracting clinical sections: {str(e)}")
            # Return empty clinical data on error
            return ClinicalData(
                session_id=ctx.session_data.get("session_id"),
                transcription_id=transcription_data.transcription_id
            )
    
    async def identify_medical_entities(self, ctx: RunContext) -> List[MedicalEntity]:
        """Identify medical entities from clinical data"""
        clinical_data = ctx.session_data.get("clinical_data")
        if not clinical_data:
            return []
        
        entities = []
        
        # Extract entities from different sections
        if clinical_data.chief_complaint:
            entities.append(MedicalEntity(
                type="symptom",
                value=clinical_data.chief_complaint,
                confidence=0.9,
                section="chief_complaint"
            ))
        
        if clinical_data.medications:
            for med in clinical_data.medications:
                entities.append(MedicalEntity(
                    type="medication",
                    value=med,
                    confidence=0.95,
                    section="medications"
                ))
        
        if clinical_data.assessment:
            # In production, use NER to extract diagnoses
            entities.append(MedicalEntity(
                type="diagnosis",
                value=clinical_data.assessment,
                confidence=0.85,
                section="assessment"
            ))
        
        # Add entities to clinical data
        clinical_data.medical_entities = entities
        
        return entities
    
    async def enhance_with_ehr(self, ctx: RunContext) -> ClinicalData:
        """Enhance clinical data with EHR information"""
        clinical_data = ctx.session_data.get("clinical_data")
        if not clinical_data:
            return clinical_data
        
        # Get EHR sections from context
        ehr_sections = ctx.session_data.get("ehr_sections", {})
        
        # Merge with clinical data
        if ehr_sections.get("medications") and not clinical_data.medications:
            clinical_data.medications = ehr_sections["medications"]
        
        if ehr_sections.get("allergies") and not clinical_data.allergies:
            clinical_data.allergies = ehr_sections["allergies"]
        
        if ehr_sections.get("past_medical_history") and not clinical_data.past_medical_history:
            clinical_data.past_medical_history = ehr_sections["past_medical_history"]
        
        return clinical_data
    
    # Tool implementations for Note Structuring Agent
    async def format_soap_note(self, ctx: RunContext) -> StructuredNote:
        """Format clinical data as SOAP note"""
        clinical_data = ctx.session_data.get("clinical_data")
        if not clinical_data:
            raise ValueError("No clinical data found in context")
        
        sections = {
            "subjective": self._format_subjective(clinical_data),
            "objective": self._format_objective(clinical_data),
            "assessment": clinical_data.assessment or "No assessment documented",
            "plan": clinical_data.plan or "No plan documented"
        }
        
        note_content = f"""SOAP NOTE
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

S (Subjective):
{sections['subjective']}

O (Objective):
{sections['objective']}

A (Assessment):
{sections['assessment']}

P (Plan):
{sections['plan']}"""
        
        structured_note = StructuredNote(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=clinical_data.transcription_id,
            format_type="soap",
            note_content=note_content,
            sections=sections
        )
        
        # Store in context
        ctx.session_data["structured_note"] = structured_note
        
        return structured_note
    
    async def format_bullet_points(self, ctx: RunContext) -> StructuredNote:
        """Format clinical data as bullet points"""
        clinical_data = ctx.session_data.get("clinical_data")
        if not clinical_data:
            raise ValueError("No clinical data found in context")
        
        bullet_content = f"""CLINICAL NOTE - BULLET FORMAT
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

CHIEF COMPLAINT:
• {clinical_data.chief_complaint or 'Not documented'}

HISTORY OF PRESENT ILLNESS:
• {clinical_data.history_present_illness or 'Not documented'}

MEDICATIONS:
{self._format_list_as_bullets(clinical_data.medications)}

ALLERGIES:
{self._format_list_as_bullets(clinical_data.allergies)}

ASSESSMENT:
• {clinical_data.assessment or 'Not documented'}

PLAN:
• {clinical_data.plan or 'Not documented'}"""
        
        return StructuredNote(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=clinical_data.transcription_id,
            format_type="bullet",
            note_content=bullet_content,
            sections={}
        )
    
    async def format_narrative(self, ctx: RunContext) -> StructuredNote:
        """Format clinical data as narrative"""
        clinical_data = ctx.session_data.get("clinical_data")
        if not clinical_data:
            raise ValueError("No clinical data found in context")
        
        narrative = f"""CLINICAL NARRATIVE
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

The patient presents with {clinical_data.chief_complaint or 'unspecified concerns'}. 

{clinical_data.history_present_illness or 'No additional history was provided.'}

Past medical history is {clinical_data.past_medical_history or 'unremarkable'}. 
Current medications include {', '.join(clinical_data.medications) if clinical_data.medications else 'none reported'}. 
Patient allergies: {', '.join(clinical_data.allergies) if clinical_data.allergies else 'NKDA'}.

Clinical assessment: {clinical_data.assessment or 'Pending further evaluation'}.

Treatment plan: {clinical_data.plan or 'To be determined'}.
"""
        
        return StructuredNote(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=clinical_data.transcription_id,
            format_type="narrative",
            note_content=narrative,
            sections={}
        )
    
    # Tool implementations for QA Agent
    async def validate_note(self, ctx: RunContext) -> Dict[str, Any]:
        """Validate clinical note for completeness"""
        structured_note = ctx.session_data.get("structured_note")
        if not structured_note:
            return {"missing_sections": ["all"], "warnings": ["No note found"]}
        
        missing_sections = []
        warnings = []
        
        # Check required sections based on format
        if structured_note.format_type == "soap":
            required_sections = ["subjective", "objective", "assessment", "plan"]
            for section in required_sections:
                if not structured_note.sections.get(section) or len(structured_note.sections[section].strip()) < 10:
                    missing_sections.append(section)
        
        # Check for safety issues
        note_lower = structured_note.note_content.lower()
        if "allerg" not in note_lower:
            warnings.append("No allergy information documented")
        
        if "medicat" not in note_lower:
            warnings.append("No medication information documented")
        
        # Check note length
        if len(structured_note.note_content) < 200:
            warnings.append("Note appears too brief")
        
        return {
            "missing_sections": missing_sections,
            "warnings": warnings,
            "note_length": len(structured_note.note_content),
            "has_required_sections": len(missing_sections) == 0
        }
    
    async def generate_qa_report(self, ctx: RunContext) -> QAReport:
        """Generate comprehensive QA report"""
        structured_note = ctx.session_data.get("structured_note")
        validation = await self.validate_note(ctx)
        
        # Calculate scores
        missing_count = len(validation["missing_sections"])
        warning_count = len(validation["warnings"])
        
        completeness_score = max(0, 1.0 - (missing_count * 0.2))
        accuracy_score = 0.9 if validation["has_required_sections"] else 0.7
        clarity_score = 0.85 if validation["note_length"] > 300 else 0.6
        
        overall_score = (completeness_score + accuracy_score + clarity_score) / 3
        
        # Generate suggestions
        suggestions = []
        if missing_count > 0:
            suggestions.append(f"Complete missing sections: {', '.join(validation['missing_sections'])}")
        if validation["note_length"] < 300:
            suggestions.append("Add more detail to provide comprehensive documentation")
        if warning_count > 0:
            suggestions.append("Address the warnings to improve note quality")
        
        qa_report = QAReport(
            session_id=ctx.session_data.get("session_id"),
            transcription_id=structured_note.transcription_id if structured_note else "",
            overall_score=overall_score,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            clarity_score=clarity_score,
            missing_sections=validation["missing_sections"],
            warnings=validation["warnings"],
            suggestions=suggestions,
            approved=overall_score > 0.8
        )
        
        # Store in context
        ctx.session_data["qa_report"] = qa_report
        
        return qa_report
    
    # Handoff callbacks
    def _on_transcription_complete(self, ctx: RunContext, input_data: Optional[HandoffInputData] = None):
        """Called when transcription completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Transcription complete for session {session_id}")
        
        # Send SSE update
        transcription_data = ctx.session_data.get("transcription_data")
        if transcription_data and isinstance(transcription_data, TranscriptionData):
            asyncio.create_task(sse_manager.publish(
                f"transcription_{transcription_data.transcription_id}",
                {
                    "type": "transcription_complete",
                    "data": {
                        "word_count": transcription_data.word_count,
                        "speaker_count": len(transcription_data.speaker_roles)
                    }
                }
            ))
    
    def _on_analysis_complete(self, ctx: RunContext, input_data: Optional[HandoffInputData] = None):
        """Called when clinical analysis completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Clinical analysis complete for session {session_id}")
        
        # Send SSE updates for section completion
        clinical_data = ctx.session_data.get("clinical_data")
        if clinical_data and isinstance(clinical_data, ClinicalData):
            sections_found = []
            if clinical_data.chief_complaint:
                sections_found.append("chief_complaint")
            if clinical_data.history_present_illness:
                sections_found.append("history_present_illness")
            if clinical_data.assessment:
                sections_found.append("assessment")
            if clinical_data.plan:
                sections_found.append("plan")
            
            asyncio.create_task(sse_manager.publish(
                f"transcription_{clinical_data.transcription_id}",
                {
                    "type": "analysis_complete",
                    "data": {
                        "sections_found": sections_found,
                        "entity_count": len(clinical_data.medical_entities)
                    }
                }
            ))
    
    def _on_note_structured(self, ctx: RunContext, input_data: Optional[HandoffInputData] = None):
        """Called when note structuring completes"""
        session_id = ctx.session_data.get("session_id")
        logger.info(f"Note structuring complete for session {session_id}")
        
        # Update database with structured note
        structured_note = ctx.session_data.get("structured_note")
        if structured_note:
            asyncio.create_task(self._save_clinical_note(structured_note))
    
    # Input filters
    def _filter_clinical_data(self, input_data: HandoffInputData) -> HandoffInputData:
        """Filter conversation to only include clinical content"""
        # Keep only messages with medical content
        medical_terms = ["patient", "symptom", "diagnosis", "medication", "treatment", 
                        "pain", "fever", "complaint", "history", "exam", "vital"]
        
        filtered_messages = []
        for msg in input_data.messages:
            # Check if message contains medical terms
            content_lower = msg.get("content", "").lower()
            if any(term in content_lower for term in medical_terms):
                filtered_messages.append(msg)
        
        # Always keep the last message (current request)
        if input_data.messages and input_data.messages[-1] not in filtered_messages:
            filtered_messages.append(input_data.messages[-1])
        
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
            parts.append(f"\nHistory of Present Illness: {clinical_data.history_present_illness}")
        
        if clinical_data.review_of_systems:
            parts.append(f"\nReview of Systems: {self._format_dict(clinical_data.review_of_systems)}")
        
        if clinical_data.past_medical_history:
            parts.append(f"\nPast Medical History: {clinical_data.past_medical_history}")
        
        if clinical_data.medications:
            parts.append(f"\nCurrent Medications:\n{self._format_list_as_bullets(clinical_data.medications)}")
        
        if clinical_data.allergies:
            parts.append(f"\nAllergies:\n{self._format_list_as_bullets(clinical_data.allergies)}")
        
        if clinical_data.social_history:
            parts.append(f"\nSocial History: {clinical_data.social_history}")
        
        if clinical_data.family_history:
            parts.append(f"\nFamily History: {clinical_data.family_history}")
        
        return "\n".join(parts) if parts else "No subjective information documented"
    
    def _format_objective(self, clinical_data: ClinicalData) -> str:
        """Format objective section"""
        parts = []
        
        if clinical_data.vital_signs:
            parts.append(f"Vital Signs: {self._format_dict(clinical_data.vital_signs)}")
        
        if clinical_data.physical_examination:
            parts.append(f"\nPhysical Examination: {self._format_dict(clinical_data.physical_examination)}")
        
        if clinical_data.diagnostic_results:
            parts.append(f"\nDiagnostic Results: {clinical_data.diagnostic_results}")
        
        return "\n".join(parts) if parts else "No objective findings documented"
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary as readable text"""
        if not data:
            return "None"
        return ", ".join([f"{k}: {v}" for k, v in data.items()])
    
    def _format_list_as_bullets(self, items: List[str]) -> str:
        """Format list as bullet points"""
        if not items:
            return "• None documented"
        return "\n".join([f"• {item}" for item in items])
    
    async def _update_transcription_status(self, transcription_id: str, status: str, data: Dict[str, Any]):
        """Update transcription in database"""
        with SessionLocal() as db:
            transcription = db.query(Transcription).filter_by(id=transcription_id).first()
            if transcription:
                transcription.status = status
                transcription.transcript = data.get("transcript", "")
                transcription.word_count = data.get("word_count", 0)
                db.commit()
    
    async def _save_clinical_note(self, note: StructuredNote):
        """Save clinical note to database"""
        with SessionLocal() as db:
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