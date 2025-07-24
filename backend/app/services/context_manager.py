import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversation context for medical encounters.
    Tracks utterances, determines when context is complete for re-summarization.
    """
    
    def __init__(self, completion_timeout: int = 30):
        self.contexts = {}  # encounter_id -> context data
        self.completion_timeout = completion_timeout  # seconds before context is considered complete
        self.section_keywords = {
            "chief_complaint": [
                "what brings you", "reason for visit", "main concern",
                "chief complaint", "why are you here"
            ],
            "history_present_illness": [
                "tell me more", "when did it start", "how long",
                "describe the", "getting worse", "getting better"
            ],
            "medications": [
                "medications", "taking any", "allergies", "prescribe",
                "pharmacy", "dose", "how often"
            ],
            "physical_exam": [
                "let me examine", "look at", "listen to", "blood pressure",
                "temperature", "heart rate", "breath sounds"
            ],
            "review_of_systems": [
                "any other symptoms", "experiencing any", "problems with",
                "issues with", "review of systems"
            ],
            "assessment_plan": [
                "my assessment", "diagnosis", "plan is", "recommend",
                "follow up", "tests", "referral"
            ]
        }
    
    def add_to_context(self, encounter_id: str, transcription: str, speaker_info: Dict):
        """Add a new utterance to the encounter context"""
        if encounter_id not in self.contexts:
            self.contexts[encounter_id] = {
                "utterances": [],
                "sections": defaultdict(list),
                "last_update": time.time(),
                "section_transitions": [],
                "current_section": None
            }
        
        utterance = {
            "text": transcription,
            "speaker": speaker_info["speaker"],
            "confidence": speaker_info.get("confidence", 0.0),
            "timestamp": time.time()
        }
        
        self.contexts[encounter_id]["utterances"].append(utterance)
        self.contexts[encounter_id]["last_update"] = time.time()
        
        # Detect potential section transition
        detected_section = self._detect_section_transition(transcription, speaker_info["speaker"])
        if detected_section and detected_section != self.contexts[encounter_id]["current_section"]:
            self.contexts[encounter_id]["section_transitions"].append({
                "from_section": self.contexts[encounter_id]["current_section"],
                "to_section": detected_section,
                "timestamp": time.time(),
                "trigger_text": transcription
            })
            self.contexts[encounter_id]["current_section"] = detected_section
            logger.info(f"Section transition detected: {detected_section}")
    
    def _detect_section_transition(self, text: str, speaker: str) -> Optional[str]:
        """Detect if the conversation is transitioning to a new section"""
        if speaker != "DOCTOR":
            return None
        
        text_lower = text.lower()
        
        for section, keywords in self.section_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return section
        
        return None
    
    def is_context_complete(self, encounter_id: str, section: Optional[str] = None) -> bool:
        """
        Determine if context is complete and ready for re-summarization.
        
        Context is complete when:
        1. No new utterances for completion_timeout seconds
        2. Doctor explicitly moves to next section
        3. Certain completion keywords are detected
        """
        if encounter_id not in self.contexts:
            return False
        
        context = self.contexts[encounter_id]
        
        # Check timeout
        time_since_last = time.time() - context["last_update"]
        if time_since_last > self.completion_timeout:
            return True
        
        # Check for section transition
        if section and context["section_transitions"]:
            last_transition = context["section_transitions"][-1]
            if last_transition["from_section"] == section:
                return True
        
        # Check for completion keywords in recent utterances
        if len(context["utterances"]) >= 2:
            recent_text = " ".join([u["text"].lower() for u in context["utterances"][-2:]])
            completion_phrases = [
                "anything else about",
                "let's move on",
                "next i'd like to",
                "now let's discuss",
                "that covers",
                "is there anything else"
            ]
            
            for phrase in completion_phrases:
                if phrase in recent_text:
                    return True
        
        return False
    
    def get_section_context(self, encounter_id: str, section: str) -> List[Dict]:
        """Get all utterances related to a specific section"""
        if encounter_id not in self.contexts:
            return []
        
        context = self.contexts[encounter_id]
        section_utterances = []
        
        # Find utterances that belong to this section based on transitions
        current_section = None
        for utterance in context["utterances"]:
            # Check if we're transitioning to a new section
            for transition in context["section_transitions"]:
                if abs(utterance["timestamp"] - transition["timestamp"]) < 1:
                    current_section = transition["to_section"]
                    break
            
            # Add utterance if it belongs to the requested section
            if current_section == section:
                section_utterances.append(utterance)
        
        return section_utterances
    
    def get_recent_context(self, encounter_id: str, num_utterances: int = 10) -> List[str]:
        """Get the most recent utterances as context"""
        if encounter_id not in self.contexts:
            return []
        
        utterances = self.contexts[encounter_id]["utterances"]
        recent = utterances[-num_utterances:] if len(utterances) > num_utterances else utterances
        
        return [f"{u['speaker']}: {u['text']}" for u in recent]
    
    def get_conversation_summary(self, encounter_id: str) -> Dict:
        """Get a summary of the entire conversation"""
        if encounter_id not in self.contexts:
            return {}
        
        context = self.contexts[encounter_id]
        
        # Count utterances by speaker
        speaker_counts = defaultdict(int)
        for utterance in context["utterances"]:
            speaker_counts[utterance["speaker"]] += 1
        
        # Calculate conversation duration
        if context["utterances"]:
            duration = context["utterances"][-1]["timestamp"] - context["utterances"][0]["timestamp"]
        else:
            duration = 0
        
        return {
            "total_utterances": len(context["utterances"]),
            "speaker_counts": dict(speaker_counts),
            "duration_seconds": duration,
            "section_transitions": len(context["section_transitions"]),
            "sections_covered": list(set(t["to_section"] for t in context["section_transitions"])),
            "current_section": context["current_section"]
        }
    
    def mark_section_complete(self, encounter_id: str, section: str):
        """Manually mark a section as complete"""
        if encounter_id not in self.contexts:
            return
        
        # Add a synthetic transition to mark completion
        self.contexts[encounter_id]["section_transitions"].append({
            "from_section": section,
            "to_section": None,
            "timestamp": time.time(),
            "trigger_text": "[Manual completion]"
        })
    
    def clear_encounter_context(self, encounter_id: str):
        """Clear all context for an encounter"""
        if encounter_id in self.contexts:
            del self.contexts[encounter_id]
            logger.info(f"Cleared context for encounter {encounter_id}")
    
    def get_utterances_since_timestamp(self, encounter_id: str, timestamp: float) -> List[Dict]:
        """Get all utterances since a specific timestamp"""
        if encounter_id not in self.contexts:
            return []
        
        return [
            u for u in self.contexts[encounter_id]["utterances"]
            if u["timestamp"] > timestamp
        ]