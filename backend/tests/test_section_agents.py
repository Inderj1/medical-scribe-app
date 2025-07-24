import pytest
import asyncio
from datetime import datetime
from app.services.openai_section_agents import OpenAISectionAgents, SectionResult

class TestOpenAISectionAgents:
    @pytest.fixture
    def agents(self):
        return OpenAISectionAgents()
    
    @pytest.mark.asyncio
    async def test_chief_complaint_processing(self, agents):
        """Test chief complaint section processing"""
        test_cases = [
            {
                "text": "I've been experiencing severe headaches for the past week, especially in the morning.",
                "speaker": "PATIENT",
                "format": "long",
                "expected_keywords": ["headaches", "week", "morning"]
            },
            {
                "text": "My chest hurts when I breathe deeply and I've had a fever.",
                "speaker": "PATIENT", 
                "format": "short",
                "expected_keywords": ["chest", "breathe", "fever"]
            }
        ]
        
        for case in test_cases:
            result = await agents.process_section(
                "chief_complaint",
                case["text"],
                case["speaker"],
                case["format"]
            )
            
            assert result.section == "chief_complaint"
            assert result.content
            assert result.confidence > 0.7
            
            # Check all format versions exist
            assert "long" in result.format_versions
            assert "short" in result.format_versions
            assert "bullet" in result.format_versions
            
            # Verify expected keywords in content
            content_lower = result.content.lower()
            for keyword in case["expected_keywords"]:
                assert keyword in content_lower, f"Missing keyword: {keyword}"
    
    @pytest.mark.asyncio
    async def test_medications_processing(self, agents):
        """Test medications section processing"""
        medication_texts = [
            "I'm currently taking metformin 500mg twice daily and lisinopril 10mg once in the morning.",
            "Patient reports taking aspirin 81mg daily, atorvastatin 20mg at bedtime.",
            "No current medications, stopped all prescriptions last month."
        ]
        
        for text in medication_texts:
            result = await agents.process_section(
                "medications",
                text,
                "PATIENT",
                "bullet"
            )
            
            assert result.section == "medications"
            assert result.format_versions["bullet"]
            
            # Bullet format should have bullet points
            if "No current medications" not in text:
                assert "•" in result.format_versions["bullet"] or "-" in result.format_versions["bullet"]
    
    @pytest.mark.asyncio
    async def test_physical_exam_processing(self, agents):
        """Test physical exam section processing"""
        exam_text = """
        Blood pressure 138/88, pulse 92 regular, temperature 98.6F.
        Lungs clear to auscultation bilaterally. Heart regular rate and rhythm, 
        no murmurs. Abdomen soft, non-tender.
        """
        
        result = await agents.process_section(
            "physical_exam",
            exam_text,
            "DOCTOR",
            "long"
        )
        
        assert result.section == "physical_exam"
        assert "blood pressure" in result.content.lower() or "bp" in result.content.lower()
        assert result.entities  # Should extract vital signs
    
    @pytest.mark.asyncio
    async def test_assessment_plan_processing(self, agents):
        """Test assessment and plan section processing"""
        plan_text = """
        Assessment: Likely viral upper respiratory infection.
        Plan: Rest, fluids, acetaminophen for fever. Return if symptoms worsen
        or don't improve in 7 days. Consider antibiotic if bacterial infection suspected.
        """
        
        result = await agents.process_section(
            "assessment_plan",
            plan_text,
            "DOCTOR",
            "long"
        )
        
        assert result.section == "assessment_plan"
        assert "viral" in result.content.lower()
        assert "rest" in result.content.lower()
        assert result.confidence > 0.8  # High confidence for clear plan
    
    @pytest.mark.asyncio
    async def test_format_consistency(self, agents):
        """Test that all formats contain similar information"""
        text = "Patient has been taking lisinopril 10mg daily for hypertension control."
        
        result = await agents.process_section(
            "medications",
            text,
            "PATIENT",
            "long"
        )
        
        # All formats should mention the medication
        assert "lisinopril" in result.format_versions["long"].lower()
        assert "lisinopril" in result.format_versions["short"].lower()
        assert "lisinopril" in result.format_versions["bullet"].lower()
        
        # Bullet should be shortest, long should be longest
        assert len(result.format_versions["bullet"]) <= len(result.format_versions["short"])
        assert len(result.format_versions["short"]) <= len(result.format_versions["long"])
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, agents):
        """Test medical entity extraction"""
        text = """
        Patient reports taking metoprolol 50mg for blood pressure,
        diagnosed with diabetes type 2 last year, allergic to penicillin.
        """
        
        result = await agents.process_section(
            "history_present_illness",
            text,
            "PATIENT",
            "long"
        )
        
        assert result.entities
        
        # Check for expected entity types
        entity_types = {e.get("type") for e in result.entities if isinstance(e, dict)}
        expected_types = {"medication", "condition", "allergy"}
        
        # At least some expected types should be found
        assert len(entity_types.intersection(expected_types)) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_section_handling(self, agents):
        """Test handling of invalid section names"""
        with pytest.raises(Exception):
            await agents.process_section(
                "invalid_section",
                "Test text",
                "PATIENT",
                "long"
            )
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, agents):
        """Test handling of empty or minimal text"""
        result = await agents.process_section(
            "chief_complaint",
            "",
            "PATIENT",
            "long"
        )
        
        assert result.content
        assert result.confidence < 0.5  # Low confidence for empty text
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, agents):
        """Test concurrent processing of multiple sections"""
        tasks = [
            agents.process_section("chief_complaint", "Headache for 3 days", "PATIENT", "long"),
            agents.process_section("medications", "Taking ibuprofen as needed", "PATIENT", "short"),
            agents.process_section("physical_exam", "BP 120/80, temp normal", "DOCTOR", "bullet"),
            agents.process_section("assessment_plan", "Migraine, prescribe sumatriptan", "DOCTOR", "long")
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 4
        assert all(r.content for r in results)
        assert all(r.section in ["chief_complaint", "medications", "physical_exam", "assessment_plan"] for r in results)
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, agents):
        """Test that context is preserved across multiple calls"""
        # First process chief complaint
        result1 = await agents.process_section(
            "chief_complaint",
            "Severe abdominal pain since yesterday",
            "PATIENT",
            "long"
        )
        
        # Then process related physical exam
        result2 = await agents.process_section(
            "physical_exam",
            "Tenderness in right lower quadrant, positive rebound",
            "DOCTOR",
            "long",
            previous_content={"chief_complaint": result1.content}
        )
        
        # Assessment should consider both
        assert result2.confidence > 0.8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])