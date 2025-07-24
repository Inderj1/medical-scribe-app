import pytest
import asyncio
from datetime import datetime
from app.services.agent_orchestrator import AgentOrchestrator, RoutingDecision
from app.services.enhanced_transcription_service import TranscriptionResult

class TestAgentOrchestrator:
    @pytest.fixture
    async def orchestrator(self):
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize_encounter("test-enc-001", "test-patient-001")
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_encounter_initialization(self):
        """Test encounter initialization"""
        orchestrator = AgentOrchestrator()
        
        # Initialize encounter
        await orchestrator.initialize_encounter("test-enc-002", "test-patient-002")
        
        assert "test-enc-002" in orchestrator.encounters
        assert orchestrator.encounters["test-enc-002"]["patient_id"] == "test-patient-002"
        assert orchestrator.encounters["test-enc-002"]["format_preference"] == "long"
        assert orchestrator.encounters["test-enc-002"]["start_time"] is not None
    
    @pytest.mark.asyncio
    async def test_routing_chief_complaint(self, orchestrator):
        """Test routing to chief complaint section"""
        decision = await orchestrator.route_transcription(
            "I've been having terrible headaches for the past week",
            "PATIENT"
        )
        
        assert decision.primary_section == "chief_complaint"
        assert decision.confidence > 0.8
        assert "chief_complaint" in decision.secondary_sections
    
    @pytest.mark.asyncio
    async def test_routing_medications(self, orchestrator):
        """Test routing to medications section"""
        decision = await orchestrator.route_transcription(
            "I take metformin twice daily and lisinopril in the morning",
            "PATIENT"
        )
        
        assert decision.primary_section == "medications"
        assert decision.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_routing_physical_exam(self, orchestrator):
        """Test routing to physical exam section"""
        decision = await orchestrator.route_transcription(
            "Blood pressure is 130/85, heart rate 78, lungs clear",
            "DOCTOR"
        )
        
        assert decision.primary_section == "physical_exam"
        assert decision.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_routing_with_keywords(self, orchestrator):
        """Test keyword-based routing"""
        test_cases = [
            ("My main concern is the chest pain", "chief_complaint"),
            ("Current medications include aspirin", "medications"),
            ("On examination, abdomen is soft", "physical_exam"),
            ("Diagnosis is acute bronchitis", "assessment_plan"),
            ("No fever or chills recently", "review_of_systems")
        ]
        
        for text, expected_section in test_cases:
            decision = await orchestrator.route_transcription(text, "DOCTOR")
            assert decision.primary_section == expected_section, f"Failed for: {text}"
    
    @pytest.mark.asyncio
    async def test_full_transcription_processing(self, orchestrator):
        """Test complete transcription processing flow"""
        transcription = TranscriptionResult(
            id="trans-001",
            text="I've been experiencing shortness of breath when climbing stairs",
            confidence=0.95,
            segments=[],
            processing_time=0.5,
            timestamp=datetime.utcnow().isoformat()
        )
        
        result = await orchestrator.process_transcription(
            transcription,
            "test-enc-001",
            "long"
        )
        
        # Check speaker identification
        assert result.speaker_info.speaker in ["DOCTOR", "PATIENT"]
        assert result.speaker_info.confidence > 0
        
        # Check routing
        assert result.routing_decision.primary_section is not None
        
        # Check section updates
        assert len(result.section_updates) > 0
        assert all(update.section for update in result.section_updates)
        assert all(update.content for update in result.section_updates)
    
    @pytest.mark.asyncio
    async def test_format_preference_handling(self, orchestrator):
        """Test different format preferences"""
        formats = ["long", "short", "bullet"]
        transcription = TranscriptionResult(
            id="trans-002",
            text="Patient reports nausea and vomiting for two days",
            confidence=0.9,
            segments=[],
            processing_time=0.4,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for format_pref in formats:
            orchestrator.update_format_preference("test-enc-001", format_pref)
            result = await orchestrator.process_transcription(
                transcription,
                "test-enc-001",
                format_pref
            )
            
            # Check that the requested format is included
            for update in result.section_updates:
                assert format_pref in update.formatted_content
    
    @pytest.mark.asyncio
    async def test_context_aware_routing(self, orchestrator):
        """Test routing considers conversation context"""
        # First, establish chief complaint context
        trans1 = TranscriptionResult(
            id="trans-003",
            text="What brings you in today?",
            confidence=0.95,
            segments=[],
            processing_time=0.3,
            timestamp=datetime.utcnow().isoformat()
        )
        
        result1 = await orchestrator.process_transcription(trans1, "test-enc-001", "long")
        
        # Next transcription should be routed to chief complaint due to context
        trans2 = TranscriptionResult(
            id="trans-004",
            text="I've been feeling very tired lately",
            confidence=0.95,
            segments=[],
            processing_time=0.3,
            timestamp=datetime.utcnow().isoformat()
        )
        
        result2 = await orchestrator.process_transcription(trans2, "test-enc-001", "long")
        assert result2.routing_decision.primary_section == "chief_complaint"
    
    @pytest.mark.asyncio
    async def test_resummary_trigger(self, orchestrator):
        """Test that resummary is triggered appropriately"""
        # Process multiple transcriptions
        transcriptions = [
            "I have diabetes and high blood pressure",
            "Taking metformin and lisinopril daily",
            "Blood pressure today is 145/90",
            "Recommend increasing lisinopril dose"
        ]
        
        results = []
        for i, text in enumerate(transcriptions):
            trans = TranscriptionResult(
                id=f"trans-{i}",
                text=text,
                confidence=0.9,
                segments=[],
                processing_time=0.3,
                timestamp=datetime.utcnow().isoformat()
            )
            result = await orchestrator.process_transcription(trans, "test-enc-001", "long")
            results.append(result)
        
        # At least one should trigger resummary
        assert any(r.requires_resummary for r in results)
    
    @pytest.mark.asyncio
    async def test_encounter_summary_generation(self, orchestrator):
        """Test encounter summary at the end"""
        # Process some transcriptions
        texts = [
            "Chief complaint is chest pain",
            "Taking aspirin for prevention",
            "ECG shows normal sinus rhythm",
            "Plan is to continue current medications"
        ]
        
        for text in texts:
            trans = TranscriptionResult(
                id=f"trans-{text[:5]}",
                text=text,
                confidence=0.9,
                segments=[],
                processing_time=0.3,
                timestamp=datetime.utcnow().isoformat()
            )
            await orchestrator.process_transcription(trans, "test-enc-001", "long")
        
        # End encounter and get summary
        summary = orchestrator.end_encounter("test-enc-001")
        
        assert summary is not None
        assert "sections_updated" in summary
        assert "total_transcriptions" in summary
        assert summary["total_transcriptions"] == 4
    
    @pytest.mark.asyncio
    async def test_concurrent_encounters(self, orchestrator):
        """Test handling multiple concurrent encounters"""
        # Initialize multiple encounters
        encounter_ids = []
        for i in range(5):
            enc_id = f"concurrent-enc-{i}"
            await orchestrator.initialize_encounter(enc_id, f"patient-{i}")
            encounter_ids.append(enc_id)
        
        # Process transcriptions concurrently
        tasks = []
        for enc_id in encounter_ids:
            trans = TranscriptionResult(
                id=f"trans-{enc_id}",
                text="Patient reports headache and fever",
                confidence=0.9,
                segments=[],
                processing_time=0.3,
                timestamp=datetime.utcnow().isoformat()
            )
            task = orchestrator.process_transcription(trans, enc_id, "long")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Each should have independent context
        for i, enc_id in enumerate(encounter_ids):
            assert enc_id in orchestrator.encounters
    
    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator):
        """Test error handling in orchestrator"""
        # Test with non-existent encounter
        trans = TranscriptionResult(
            id="trans-error",
            text="Test transcription",
            confidence=0.9,
            segments=[],
            processing_time=0.3,
            timestamp=datetime.utcnow().isoformat()
        )
        
        result = await orchestrator.process_transcription(
            trans,
            "non-existent-encounter",
            "long"
        )
        
        assert not result.success
        assert result.error is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])