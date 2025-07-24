import json
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SpeakerIdentification:
    speaker: str  # "DOCTOR" or "PATIENT"
    confidence: float
    reasoning: str
    
    def to_dict(self) -> Dict:
        return {
            "speaker": self.speaker,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


class SpeakerDiarizationAgent:
    """
    Agent responsible for identifying whether the speaker is a doctor or patient
    in medical conversation transcriptions.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-1106-preview"  # Using GPT-4 for better accuracy
        
        # Context patterns for speaker identification
        self.doctor_patterns = {
            "questions": [
                "what brings you", "how long have you", "when did", "describe the",
                "rate your pain", "any allergies", "medications", "tell me about"
            ],
            "clinical_terms": [
                "prescribe", "examination", "diagnose", "treatment plan",
                "blood pressure", "auscultation", "palpation", "recommend"
            ],
            "instructions": [
                "let me", "i'll examine", "we'll need to", "i'm going to",
                "take this", "follow up", "schedule"
            ]
        }
        
        self.patient_patterns = {
            "symptoms": [
                "i feel", "it hurts", "i've been having", "the pain",
                "started feeling", "my symptoms", "i can't", "bothers me"
            ],
            "personal": [
                "my wife", "my job", "at home", "when i wake up",
                "i tried", "makes it worse", "helps when"
            ],
            "responses": [
                "yes doctor", "no doctor", "about", "since", "for the past",
                "it's been", "i think"
            ]
        }
    
    async def identify_speaker(self, transcription: str, context: Optional[str] = None) -> SpeakerIdentification:
        """
        Identify whether the speaker is a doctor or patient based on the transcription.
        
        Args:
            transcription: The text to analyze
            context: Optional previous conversation context
            
        Returns:
            SpeakerIdentification object with speaker type and confidence
        """
        try:
            # Build the prompt
            prompt = self._build_identification_prompt(transcription, context)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at identifying speakers in medical conversations.
                        Analyze the provided text and determine if the speaker is a DOCTOR/HEALTHCARE PROVIDER or a PATIENT.
                        
                        Consider:
                        - Language patterns and medical terminology
                        - Who is asking questions vs answering
                        - Clinical assessments vs personal experiences
                        - Professional medical language vs lay descriptions
                        
                        Always respond in the exact JSON format specified."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and create identification
            speaker = result.get("speaker", "PATIENT")
            if speaker not in ["DOCTOR", "PATIENT"]:
                speaker = "PATIENT"  # Default to patient if unclear
                
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "Unable to determine clear reasoning")
            
            # Apply heuristic adjustments
            adjusted_confidence = self._apply_heuristics(transcription, speaker, confidence)
            
            return SpeakerIdentification(
                speaker=speaker,
                confidence=adjusted_confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Speaker identification failed: {str(e)}")
            # Fallback to heuristic-based identification
            return self._heuristic_identification(transcription)
    
    def _build_identification_prompt(self, transcription: str, context: Optional[str]) -> str:
        """Build the prompt for speaker identification"""
        context_text = ""
        if context:
            context_text = f"\nPrevious context:\n{context}\n"
        
        return f"""Analyze this medical conversation transcript and identify the speaker.

{context_text}
Current statement: "{transcription}"

Determine if this is spoken by:
- DOCTOR (healthcare provider, physician, nurse, medical professional)
- PATIENT (the person receiving medical care)

Consider the language patterns, who is asking vs answering questions, and the medical context.

Respond in this JSON format:
{{
    "speaker": "DOCTOR" or "PATIENT",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your determination"
}}"""
    
    def _apply_heuristics(self, text: str, speaker: str, base_confidence: float) -> float:
        """Apply pattern-based heuristics to adjust confidence"""
        text_lower = text.lower()
        
        # Count pattern matches
        doctor_score = 0
        patient_score = 0
        
        # Check doctor patterns
        for pattern_list in self.doctor_patterns.values():
            for pattern in pattern_list:
                if pattern in text_lower:
                    doctor_score += 1
        
        # Check patient patterns
        for pattern_list in self.patient_patterns.values():
            for pattern in pattern_list:
                if pattern in text_lower:
                    patient_score += 1
        
        # Adjust confidence based on pattern matches
        if speaker == "DOCTOR" and doctor_score > patient_score:
            adjustment = min(0.2, doctor_score * 0.05)
            return min(1.0, base_confidence + adjustment)
        elif speaker == "PATIENT" and patient_score > doctor_score:
            adjustment = min(0.2, patient_score * 0.05)
            return min(1.0, base_confidence + adjustment)
        elif (speaker == "DOCTOR" and patient_score > doctor_score) or \
             (speaker == "PATIENT" and doctor_score > patient_score):
            # Patterns contradict the classification
            adjustment = min(0.3, abs(doctor_score - patient_score) * 0.05)
            return max(0.3, base_confidence - adjustment)
        
        return base_confidence
    
    def _heuristic_identification(self, transcription: str) -> SpeakerIdentification:
        """Fallback heuristic-based identification when API fails"""
        text_lower = transcription.lower()
        
        # Count pattern matches
        doctor_score = 0
        patient_score = 0
        
        # Check patterns
        for pattern_list in self.doctor_patterns.values():
            for pattern in pattern_list:
                if pattern in text_lower:
                    doctor_score += 2
        
        for pattern_list in self.patient_patterns.values():
            for pattern in pattern_list:
                if pattern in text_lower:
                    patient_score += 2
        
        # Specific strong indicators
        if any(phrase in text_lower for phrase in ["let me examine", "i'll prescribe", "your diagnosis"]):
            doctor_score += 5
        if any(phrase in text_lower for phrase in ["i feel", "my pain", "it hurts when"]):
            patient_score += 5
        
        # Determine speaker
        if doctor_score > patient_score:
            confidence = min(0.9, 0.5 + (doctor_score - patient_score) * 0.05)
            return SpeakerIdentification(
                speaker="DOCTOR",
                confidence=confidence,
                reasoning=f"Heuristic: doctor patterns ({doctor_score}) > patient patterns ({patient_score})"
            )
        else:
            confidence = min(0.9, 0.5 + (patient_score - doctor_score) * 0.05)
            return SpeakerIdentification(
                speaker="PATIENT",
                confidence=confidence,
                reasoning=f"Heuristic: patient patterns ({patient_score}) > doctor patterns ({doctor_score})"
            )
    
    async def analyze_conversation_flow(self, utterances: list[Dict]) -> Dict:
        """
        Analyze a series of utterances to identify conversation patterns
        and improve speaker identification accuracy.
        """
        if not utterances:
            return {"pattern": "unknown", "corrections": []}
        
        # Look for conversation patterns
        corrections = []
        
        # Pattern: Question followed by answer
        for i in range(len(utterances) - 1):
            current = utterances[i]
            next_utt = utterances[i + 1]
            
            # If current ends with "?" and is identified as doctor, next should likely be patient
            if current["text"].strip().endswith("?") and current["speaker"] == "DOCTOR":
                if next_utt["speaker"] == "DOCTOR" and next_utt["confidence"] < 0.7:
                    corrections.append({
                        "index": i + 1,
                        "suggested_speaker": "PATIENT",
                        "reason": "Response to doctor's question"
                    })
        
        return {
            "pattern": "medical_consultation",
            "corrections": corrections,
            "confidence": 0.8
        }