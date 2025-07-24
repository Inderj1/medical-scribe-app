import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.services.speaker_diarization_agent import SpeakerDiarizationAgent, SpeakerIdentification
from app.services.openai_section_agents import OpenAISectionAgents, SectionResult
from app.services.context_manager import ContextManager
from app.services.enhanced_transcription_service import TranscriptionResult

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    primary_section: str
    confidence: float
    secondary_sections: List[str]
    reasoning: str


@dataclass
class OrchestrationResult:
    speaker_info: SpeakerIdentification
    routing_decision: RoutingDecision
    section_updates: List[SectionResult]
    requires_resummary: bool
    timestamp: str


class AgentOrchestrator:
    """
    Orchestrates the flow of transcriptions through various agents:
    1. Speaker diarization
    2. Section routing
    3. Content processing
    4. Re-summarization when context is complete
    """
    
    def __init__(self):
        self.diarization_agent = SpeakerDiarizationAgent()
        self.section_agents = OpenAISectionAgents()
        self.context_manager = ContextManager()
        self.active_encounters = {}  # encounter_id -> metadata
        
        # Section routing patterns
        self.section_patterns = {
            "chief_complaint": {
                "keywords": ["brings you", "main concern", "chief complaint", "reason for visit"],
                "early_encounter": True,
                "speaker_preference": "PATIENT"
            },
            "history_present_illness": {
                "keywords": ["when did", "how long", "describe", "tell me more", "started"],
                "early_encounter": True,
                "speaker_preference": "BOTH"
            },
            "medications": {
                "keywords": ["medications", "taking", "prescribe", "pharmacy", "allergies"],
                "early_encounter": False,
                "speaker_preference": "BOTH"
            },
            "physical_exam": {
                "keywords": ["examine", "listen", "blood pressure", "temperature", "look at"],
                "early_encounter": False,
                "speaker_preference": "DOCTOR"
            },
            "review_of_systems": {
                "keywords": ["other symptoms", "experiencing", "problems with", "review of systems"],
                "early_encounter": False,
                "speaker_preference": "BOTH"
            },
            "assessment_plan": {
                "keywords": ["assessment", "diagnosis", "plan", "recommend", "follow up"],
                "early_encounter": False,
                "speaker_preference": "DOCTOR"
            }
        }
    
    async def initialize_encounter(self, encounter_id: str, patient_id: str) -> Dict:
        """Initialize a new encounter"""
        self.active_encounters[encounter_id] = {
            "patient_id": patient_id,
            "start_time": datetime.utcnow(),
            "sections_visited": set(),
            "format_preference": "long",
            "utterance_count": 0
        }
        
        logger.info(f"Initialized encounter {encounter_id} for patient {patient_id}")
        return {"status": "initialized", "encounter_id": encounter_id}
    
    async def process_transcription(
        self,
        transcription_result: TranscriptionResult,
        encounter_id: str,
        format_preference: str = "long"
    ) -> OrchestrationResult:
        """
        Main orchestration method that processes a transcription through all agents.
        """
        if encounter_id not in self.active_encounters:
            raise ValueError(f"Encounter {encounter_id} not initialized")
        
        # Update format preference
        self.active_encounters[encounter_id]["format_preference"] = format_preference
        self.active_encounters[encounter_id]["utterance_count"] += 1
        
        # Step 1: Identify speaker
        context = self.context_manager.get_recent_context(encounter_id, num_utterances=5)
        speaker_info = await self.diarization_agent.identify_speaker(
            transcription_result.text,
            context="\n".join(context) if context else None
        )
        
        # Step 2: Add to context
        self.context_manager.add_to_context(
            encounter_id,
            transcription_result.text,
            speaker_info.to_dict()
        )
        
        # Step 3: Determine routing
        routing_decision = await self._determine_routing(
            transcription_result.text,
            speaker_info,
            encounter_id
        )
        
        # Step 4: Process with appropriate agents
        section_updates = await self._process_with_agents(
            transcription_result,
            routing_decision,
            speaker_info,
            encounter_id,
            format_preference
        )
        
        # Step 5: Check if any sections need re-summarization
        requires_resummary = False
        for section in routing_decision.secondary_sections + [routing_decision.primary_section]:
            if self.context_manager.is_context_complete(encounter_id, section):
                logger.info(f"Section {section} is complete, triggering re-summarization")
                summary = await self._re_summarize_section(encounter_id, section, format_preference)
                if summary:
                    section_updates.append(summary)
                    requires_resummary = True
        
        # Update sections visited
        self.active_encounters[encounter_id]["sections_visited"].add(routing_decision.primary_section)
        
        return OrchestrationResult(
            speaker_info=speaker_info,
            routing_decision=routing_decision,
            section_updates=section_updates,
            requires_resummary=requires_resummary,
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def _determine_routing(
        self,
        text: str,
        speaker_info: SpeakerIdentification,
        encounter_id: str
    ) -> RoutingDecision:
        """Determine which section(s) should process this transcription"""
        text_lower = text.lower()
        scores = {}
        
        # Calculate scores for each section
        for section, config in self.section_patterns.items():
            score = 0.0
            
            # Keyword matching
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 0.3
            
            # Speaker preference
            if config["speaker_preference"] == speaker_info.speaker:
                score += 0.2
            elif config["speaker_preference"] == "BOTH":
                score += 0.1
            
            # Early encounter bonus
            utterance_count = self.active_encounters[encounter_id]["utterance_count"]
            if config["early_encounter"] and utterance_count <= 10:
                score += 0.2
            elif not config["early_encounter"] and utterance_count > 10:
                score += 0.1
            
            # Penalty if section already visited (except for ongoing sections)
            if section in self.active_encounters[encounter_id]["sections_visited"]:
                if section not in ["history_present_illness", "assessment_plan"]:
                    score *= 0.5
            
            scores[section] = min(score, 1.0)
        
        # Determine primary and secondary sections
        sorted_sections = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_section = sorted_sections[0][0]
        confidence = sorted_sections[0][1]
        
        # Get secondary sections with significant scores
        secondary_sections = [
            section for section, score in sorted_sections[1:]
            if score > 0.3 and score > confidence * 0.5
        ]
        
        # Generate reasoning
        reasoning = f"Primary section '{primary_section}' selected with confidence {confidence:.2f}. "
        if secondary_sections:
            reasoning += f"Also relevant to: {', '.join(secondary_sections)}."
        
        return RoutingDecision(
            primary_section=primary_section,
            confidence=confidence,
            secondary_sections=secondary_sections,
            reasoning=reasoning
        )
    
    async def _process_with_agents(
        self,
        transcription_result: TranscriptionResult,
        routing_decision: RoutingDecision,
        speaker_info: SpeakerIdentification,
        encounter_id: str,
        format_preference: str
    ) -> List[SectionResult]:
        """Process transcription with the selected section agents"""
        updates = []
        
        # Get recent context
        context = self.context_manager.get_recent_context(encounter_id)
        
        # Process with primary section agent
        primary_task = self.section_agents.process_section(
            section=routing_decision.primary_section,
            transcription=transcription_result.text,
            speaker=speaker_info.speaker,
            format_preference=format_preference,
            previous_content=context
        )
        
        # Process with secondary section agents in parallel
        secondary_tasks = []
        for section in routing_decision.secondary_sections[:2]:  # Limit to 2 secondary
            secondary_tasks.append(
                self.section_agents.process_section(
                    section=section,
                    transcription=transcription_result.text,
                    speaker=speaker_info.speaker,
                    format_preference=format_preference,
                    previous_content=context
                )
            )
        
        # Wait for all processing to complete
        all_tasks = [primary_task] + secondary_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Collect successful updates
        for result in results:
            if isinstance(result, SectionResult):
                updates.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Agent processing error: {result}")
        
        return updates
    
    async def _re_summarize_section(
        self,
        encounter_id: str,
        section: str,
        format_preference: str
    ) -> Optional[SectionResult]:
        """Re-summarize a section when context is complete"""
        try:
            summary = await self.section_agents.get_context_summary(
                encounter_id=encounter_id,
                section=section,
                format_preference=format_preference
            )
            
            if summary:
                # Mark section as complete
                self.context_manager.mark_section_complete(encounter_id, section)
                
                return SectionResult(
                    section=section,
                    content=summary,
                    formatted_content={
                        format_preference: summary
                    },
                    confidence=1.0,
                    entities={},
                    timestamp=datetime.utcnow().isoformat()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Re-summarization failed for section {section}: {str(e)}")
            return None
    
    def update_format_preference(self, encounter_id: str, format_preference: str):
        """Update the format preference for an encounter"""
        if encounter_id in self.active_encounters:
            self.active_encounters[encounter_id]["format_preference"] = format_preference
            logger.info(f"Updated format preference to {format_preference} for encounter {encounter_id}")
    
    def end_encounter(self, encounter_id: str) -> Dict:
        """End an encounter and clean up resources"""
        if encounter_id not in self.active_encounters:
            return {"status": "error", "message": "Encounter not found"}
        
        # Get summary before clearing
        summary = self.context_manager.get_conversation_summary(encounter_id)
        
        # Clear all contexts
        self.context_manager.clear_encounter_context(encounter_id)
        self.section_agents.clear_context(encounter_id)
        
        # Remove from active encounters
        encounter_data = self.active_encounters.pop(encounter_id)
        
        return {
            "status": "ended",
            "encounter_id": encounter_id,
            "duration_seconds": (datetime.utcnow() - encounter_data["start_time"]).total_seconds(),
            "summary": summary
        }
    
    async def get_encounter_status(self, encounter_id: str) -> Dict:
        """Get the current status of an encounter"""
        if encounter_id not in self.active_encounters:
            return {"status": "not_found"}
        
        encounter = self.active_encounters[encounter_id]
        summary = self.context_manager.get_conversation_summary(encounter_id)
        
        return {
            "status": "active",
            "encounter_id": encounter_id,
            "patient_id": encounter["patient_id"],
            "duration_seconds": (datetime.utcnow() - encounter["start_time"]).total_seconds(),
            "format_preference": encounter["format_preference"],
            "sections_visited": list(encounter["sections_visited"]),
            "utterance_count": encounter["utterance_count"],
            "conversation_summary": summary
        }