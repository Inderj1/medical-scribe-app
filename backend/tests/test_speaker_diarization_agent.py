import pytest
import asyncio
from datetime import datetime
from app.services.speaker_diarization_agent import SpeakerDiarizationAgent, SpeakerIdentification

class TestSpeakerDiarizationAgent:
    @pytest.fixture
    def agent(self):
        return SpeakerDiarizationAgent()
    
    @pytest.mark.asyncio
    async def test_doctor_identification_clear_cases(self, agent):
        """Test clear doctor speech patterns"""
        doctor_phrases = [
            "Let me examine your throat and check your blood pressure.",
            "I'm going to prescribe you amoxicillin for the infection.",
            "Your test results show elevated cholesterol levels.",
            "I recommend starting physical therapy twice a week.",
            "Based on your symptoms, this appears to be bronchitis."
        ]
        
        for phrase in doctor_phrases:
            result = await agent.identify_speaker(phrase)
            assert result.speaker == "DOCTOR", f"Failed to identify doctor in: {phrase}"
            assert result.confidence > 0.8, f"Low confidence for doctor phrase: {phrase}"
    
    @pytest.mark.asyncio
    async def test_patient_identification_clear_cases(self, agent):
        """Test clear patient speech patterns"""
        patient_phrases = [
            "I've been having this cough for about two weeks now.",
            "The pain started yesterday and it's getting worse.",
            "I feel dizzy when I stand up too quickly.",
            "My mother had diabetes and heart disease.",
            "I take my medication every morning with breakfast."
        ]
        
        for phrase in patient_phrases:
            result = await agent.identify_speaker(phrase)
            assert result.speaker == "PATIENT", f"Failed to identify patient in: {phrase}"
            assert result.confidence > 0.8, f"Low confidence for patient phrase: {phrase}"
    
    @pytest.mark.asyncio
    async def test_ambiguous_speech_patterns(self, agent):
        """Test ambiguous phrases that could be either speaker"""
        ambiguous_phrases = [
            "The medication seems to be working well.",
            "Blood pressure is better than last time.",
            "No allergic reactions so far.",
            "Sleep has improved significantly."
        ]
        
        for phrase in ambiguous_phrases:
            result = await agent.identify_speaker(phrase)
            assert result.speaker in ["DOCTOR", "PATIENT"]
            # Expect lower confidence for ambiguous phrases
            assert result.confidence < 0.8, f"Too high confidence for ambiguous phrase: {phrase}"
    
    @pytest.mark.asyncio
    async def test_with_context(self, agent):
        """Test speaker identification with conversation context"""
        # First establish doctor context
        context = "Doctor: How can I help you today?"
        result = await agent.identify_speaker(
            "I've been experiencing headaches",
            context=context
        )
        assert result.speaker == "PATIENT"
        assert result.confidence > 0.85  # Higher confidence with context
        
        # Test with patient context
        context = "Patient: I've been feeling unwell. Doctor: Tell me more about your symptoms."
        result = await agent.identify_speaker(
            "When did these symptoms start?",
            context=context
        )
        assert result.speaker == "DOCTOR"
    
    @pytest.mark.asyncio
    async def test_medical_terminology(self, agent):
        """Test identification with medical terminology"""
        medical_phrases = [
            ("The patient presents with bilateral pneumonia", "DOCTOR"),
            ("Recommend CT scan to rule out pulmonary embolism", "DOCTOR"),
            ("I think I might have strep throat", "PATIENT"),
            ("My blood sugar was 250 this morning", "PATIENT")
        ]
        
        for phrase, expected in medical_phrases:
            result = await agent.identify_speaker(phrase)
            assert result.speaker == expected, f"Misidentified: {phrase}"
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self, agent):
        """Test a complete conversation flow"""
        conversation = [
            ("Good morning, what brings you in today?", "DOCTOR"),
            ("I've been having severe back pain", "PATIENT"),
            ("How long has this been going on?", "DOCTOR"),
            ("About three weeks now", "PATIENT"),
            ("On a scale of 1 to 10, how would you rate the pain?", "DOCTOR"),
            ("It's about a 7 or 8 most days", "PATIENT"),
            ("Let's do a physical examination", "DOCTOR")
        ]
        
        for text, expected in conversation:
            result = await agent.identify_speaker(text)
            assert result.speaker == expected, f"Failed in conversation: {text}"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling for edge cases"""
        # Empty text
        result = await agent.identify_speaker("")
        assert result.speaker in ["DOCTOR", "PATIENT"]
        assert result.confidence < 0.5
        
        # Very long text
        long_text = "test " * 1000
        result = await agent.identify_speaker(long_text)
        assert result.speaker in ["DOCTOR", "PATIENT"]
        
        # Special characters
        result = await agent.identify_speaker("!@#$%^&*()")
        assert result.speaker in ["DOCTOR", "PATIENT"]
        assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_performance(self, agent):
        """Test performance with multiple concurrent requests"""
        phrases = [
            "I need to check your blood pressure",
            "My head hurts when I wake up",
            "The x-ray shows improvement",
            "I've been taking the medication as prescribed"
        ] * 10
        
        start_time = datetime.now()
        
        # Process concurrently
        tasks = [agent.identify_speaker(phrase) for phrase in phrases]
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should process 40 phrases in under 5 seconds
        assert duration < 5.0, f"Processing took too long: {duration}s"
        assert all(r.speaker in ["DOCTOR", "PATIENT"] for r in results)
    
    @pytest.mark.asyncio
    async def test_consistency(self, agent):
        """Test consistency of results for same input"""
        phrase = "The treatment is showing positive results"
        
        # Run multiple times
        results = []
        for _ in range(5):
            result = await agent.identify_speaker(phrase)
            results.append(result)
        
        # All results should be the same
        speakers = [r.speaker for r in results]
        assert len(set(speakers)) == 1, "Inconsistent results for same input"
        
        # Confidence should be similar (within 0.1)
        confidences = [r.confidence for r in results]
        assert max(confidences) - min(confidences) < 0.1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])