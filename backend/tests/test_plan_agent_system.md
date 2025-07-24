# Comprehensive Testing Plan for Agent-Based Medical Scribe System

## 1. Overview
This testing plan covers the complete agent-based medical scribe system including speaker diarization, section-specific agents, EHR integration, and real-time UI updates.

## 2. Testing Objectives
- Verify speaker identification accuracy (doctor vs patient)
- Validate agent routing decisions based on transcription content
- Ensure proper EHR data pre-population
- Test re-summarization triggers and accuracy
- Validate UI responsiveness and real-time updates
- Ensure system handles edge cases gracefully

## 3. Test Environment Setup

### 3.1 Backend Requirements
- Python 3.9+ with all dependencies installed
- Redis server running on localhost:6379
- PostgreSQL database with test data
- OpenAI API key configured
- Mock EHR data available

### 3.2 Frontend Requirements
- Node.js 16+ with npm packages installed
- WebSocket connection to backend
- Chrome/Firefox with developer tools

### 3.3 Test Data Preparation
```python
# Sample test patients
test_patients = [
    {
        "id": "test-patient-001",
        "first_name": "John",
        "last_name": "Doe",
        "mrn": "MRN001234",
        "date_of_birth": "1978-05-15",
        "allergies": "Penicillin, Aspirin",
        "medications": ["Metformin 500mg", "Lisinopril 10mg"],
        "medical_history": ["Type 2 Diabetes", "Hypertension"]
    }
]
```

## 4. Unit Tests

### 4.1 Speaker Diarization Agent Tests
```python
# test_speaker_diarization_agent.py
import pytest
from app.services.speaker_diarization_agent import SpeakerDiarizationAgent

class TestSpeakerDiarization:
    @pytest.fixture
    def agent(self):
        return SpeakerDiarizationAgent()
    
    async def test_doctor_identification(self, agent):
        transcription = "Let me examine your throat and check your blood pressure."
        result = await agent.identify_speaker(transcription)
        assert result.speaker == "DOCTOR"
        assert result.confidence > 0.8
    
    async def test_patient_identification(self, agent):
        transcription = "I've been having this cough for about two weeks now."
        result = await agent.identify_speaker(transcription)
        assert result.speaker == "PATIENT"
        assert result.confidence > 0.8
    
    async def test_ambiguous_speech(self, agent):
        transcription = "The medication seems to be working well."
        result = await agent.identify_speaker(transcription)
        assert result.confidence < 0.7  # Lower confidence expected
```

### 4.2 Section Agent Tests
```python
# test_section_agents.py
import pytest
from app.services.openai_section_agents import OpenAISectionAgents

class TestSectionAgents:
    @pytest.fixture
    def agents(self):
        return OpenAISectionAgents()
    
    async def test_chief_complaint_agent(self, agents):
        transcription = "I've been experiencing severe headaches for the past week."
        result = await agents.process_section(
            "chief_complaint",
            transcription,
            speaker="PATIENT",
            format_preference="long"
        )
        assert "headaches" in result.content.lower()
        assert result.format_versions["long"]
        assert result.format_versions["short"]
        assert result.format_versions["bullet"]
    
    async def test_medications_agent(self, agents):
        transcription = "I'm currently taking metformin twice daily and lisinopril once in the morning."
        result = await agents.process_section(
            "medications",
            transcription,
            speaker="PATIENT",
            format_preference="bullet"
        )
        assert "metformin" in result.content.lower()
        assert "lisinopril" in result.content.lower()
```

### 4.3 Context Manager Tests
```python
# test_context_manager.py
import pytest
import time
from app.services.context_manager import ContextManager

class TestContextManager:
    @pytest.fixture
    def manager(self):
        return ContextManager()
    
    def test_context_completion_timeout(self, manager):
        encounter_id = "test-enc-001"
        manager.add_to_context(encounter_id, "chief_complaint", "Test content")
        
        # Should not be complete immediately
        assert not manager.is_context_complete(encounter_id)
        
        # Mock time passage
        manager.contexts[encounter_id]["chief_complaint"]["last_update"] = time.time() - 31
        
        # Should be complete after timeout
        assert manager.is_context_complete(encounter_id, "chief_complaint")
```

## 5. Integration Tests

### 5.1 Agent Orchestrator Integration
```python
# test_agent_orchestrator_integration.py
import pytest
from app.services.agent_orchestrator import AgentOrchestrator

class TestAgentOrchestration:
    @pytest.fixture
    async def orchestrator(self):
        orchestrator = AgentOrchestrator()
        await orchestrator.initialize_encounter("test-enc-001", "test-patient-001")
        return orchestrator
    
    async def test_full_transcription_flow(self, orchestrator):
        # Test complete flow from transcription to section update
        transcription_result = TranscriptionResult(
            id="trans-001",
            text="I've been having chest pain for three days.",
            confidence=0.95,
            segments=[],
            timestamp=datetime.utcnow().isoformat()
        )
        
        result = await orchestrator.process_transcription(
            transcription_result,
            "test-enc-001",
            "long"
        )
        
        assert result.speaker_info.speaker in ["DOCTOR", "PATIENT"]
        assert len(result.section_updates) > 0
        assert result.routing_decision.primary_section == "chief_complaint"
```

### 5.2 WebSocket Integration Tests
```python
# test_websocket_integration.py
import pytest
import asyncio
from fastapi.testclient import TestClient

class TestWebSocketIntegration:
    async def test_clinical_notes_start(self, client: TestClient):
        with client.websocket_connect("/ws/enhanced-audio-stream?token=test-token") as websocket:
            # Send start clinical notes message
            websocket.send_json({
                "type": "clinical_notes:start",
                "patient_id": "test-patient-001",
                "encounter_type": "routine_visit"
            })
            
            # Should receive prefill data
            response = websocket.receive_json()
            assert response["type"] == "clinical_notes:prefill"
            assert "data" in response
            assert "sections" in response["data"]
```

## 6. End-to-End Tests

### 6.1 Complete Clinical Encounter Flow
```python
# test_e2e_clinical_encounter.py
class TestE2EClinicalEncounter:
    async def test_complete_encounter_flow(self):
        """Test complete flow from start to finish"""
        # 1. Start clinical notes
        # 2. Simulate audio streaming with doctor/patient conversation
        # 3. Verify speaker identification
        # 4. Check section updates
        # 5. Test format changes
        # 6. Verify re-summarization
        # 7. End encounter and check summary
```

### 6.2 UI Integration Tests
```javascript
// test_ui_integration.spec.js
describe('Clinical Notes UI Integration', () => {
    it('should display Start Clinical Notes button', async () => {
        // Navigate to clinical notes page
        // Click start button
        // Verify loading state
        // Check for prefilled data
    });
    
    it('should show speaker indicator updates', async () => {
        // Start clinical notes
        // Simulate transcription with speaker info
        // Verify speaker indicator shows correct speaker
        // Check confidence display
    });
    
    it('should update agent status in real-time', async () => {
        // Start transcription
        // Verify agent status shows processing
        // Check section highlights
        // Verify completion states
    });
});
```

## 7. Performance Tests

### 7.1 Latency Testing
```python
# test_performance.py
import time
import statistics

class TestPerformance:
    async def test_speaker_identification_latency(self):
        agent = SpeakerDiarizationAgent()
        latencies = []
        
        for _ in range(100):
            start = time.time()
            await agent.identify_speaker("Test transcription")
            latencies.append(time.time() - start)
        
        avg_latency = statistics.mean(latencies)
        assert avg_latency < 0.5  # Should be under 500ms
    
    async def test_section_processing_latency(self):
        agents = OpenAISectionAgents()
        latencies = []
        
        for _ in range(50):
            start = time.time()
            await agents.process_section(
                "chief_complaint",
                "Test content",
                "PATIENT",
                "long"
            )
            latencies.append(time.time() - start)
        
        avg_latency = statistics.mean(latencies)
        assert avg_latency < 2.0  # Should be under 2 seconds
```

### 7.2 Load Testing
```python
# test_load.py
class TestLoad:
    async def test_concurrent_encounters(self):
        """Test system with multiple concurrent encounters"""
        orchestrator = AgentOrchestrator()
        encounters = []
        
        # Create 10 concurrent encounters
        for i in range(10):
            encounter_id = f"load-test-enc-{i}"
            await orchestrator.initialize_encounter(encounter_id, f"patient-{i}")
            encounters.append(encounter_id)
        
        # Process transcriptions concurrently
        tasks = []
        for enc_id in encounters:
            task = orchestrator.process_transcription(
                create_test_transcription(),
                enc_id,
                "long"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        assert all(r.success for r in results)
```

## 8. Edge Case Tests

### 8.1 Error Handling
```python
# test_error_handling.py
class TestErrorHandling:
    async def test_invalid_section_routing(self):
        orchestrator = AgentOrchestrator()
        # Test with nonsensical transcription
        result = await orchestrator.route_transcription(
            "!@#$%^&*()",
            "UNKNOWN"
        )
        assert result.primary_section is not None  # Should have fallback
    
    async def test_openai_api_failure(self):
        # Mock OpenAI API failure
        # Verify graceful degradation
        pass
    
    async def test_missing_patient_data(self):
        ehr_service = EHRPrefillService()
        result = await ehr_service.fetch_patient_data_for_notes(
            "non-existent-patient",
            mock_db
        )
        assert result["sections"]  # Should return empty sections
```

### 8.2 Boundary Conditions
```python
# test_boundaries.py
class TestBoundaries:
    async def test_very_long_transcription(self):
        # Test with 10,000+ character transcription
        long_text = "test " * 2000
        result = await agent.identify_speaker(long_text)
        assert result.speaker in ["DOCTOR", "PATIENT"]
    
    async def test_rapid_speaker_changes(self):
        # Test conversation with quick back-and-forth
        transcriptions = [
            ("Doctor: How are you?", "DOCTOR"),
            ("Patient: Not well.", "PATIENT"),
            ("Doctor: What's wrong?", "DOCTOR"),
            ("Patient: Headache.", "PATIENT")
        ]
        
        for text, expected in transcriptions:
            result = await agent.identify_speaker(text)
            assert result.speaker == expected
```

## 9. Security Tests

### 9.1 Input Validation
```python
# test_security.py
class TestSecurity:
    async def test_sql_injection_prevention(self):
        # Test with SQL injection attempts in transcription
        malicious_text = "'; DROP TABLE patients; --"
        result = await orchestrator.process_transcription(
            create_transcription(malicious_text),
            "test-enc",
            "long"
        )
        # Should process without executing SQL
        assert result.success
    
    async def test_xss_prevention(self):
        # Test with XSS attempts
        xss_text = "<script>alert('xss')</script>"
        result = await agents.process_section(
            "chief_complaint",
            xss_text,
            "PATIENT",
            "long"
        )
        # Should sanitize output
        assert "<script>" not in result.content
```

## 10. Test Execution Plan

### Phase 1: Unit Tests (Week 1)
1. Run all unit tests for individual components
2. Fix any failing tests
3. Achieve >90% code coverage

### Phase 2: Integration Tests (Week 1-2)
1. Test component interactions
2. Verify WebSocket communication
3. Test database operations

### Phase 3: E2E Tests (Week 2)
1. Complete encounter workflows
2. UI automation tests
3. Cross-browser testing

### Phase 4: Performance & Load Tests (Week 2-3)
1. Measure latencies
2. Stress test with concurrent users
3. Optimize bottlenecks

### Phase 5: Security & Edge Cases (Week 3)
1. Security vulnerability testing
2. Edge case validation
3. Error recovery testing

## 11. Test Metrics & Success Criteria

### Success Criteria:
- Speaker identification accuracy > 85%
- Agent routing accuracy > 90%
- Average processing latency < 2 seconds
- System handles 50+ concurrent encounters
- Zero critical security vulnerabilities
- UI updates within 100ms of backend events

### Key Metrics:
- Test coverage: >85%
- Pass rate: >95%
- Performance benchmarks met
- No memory leaks after 24-hour run

## 12. Bug Tracking & Reporting

### Bug Report Template:
```markdown
**Bug ID**: BUG-001
**Component**: Speaker Diarization Agent
**Severity**: High/Medium/Low
**Description**: [Clear description]
**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
**Expected Result**: [What should happen]
**Actual Result**: [What actually happens]
**Environment**: [OS, Browser, etc.]
**Logs/Screenshots**: [Attach if applicable]
```

## 13. Continuous Testing

### CI/CD Integration:
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests
        run: pytest tests/unit
      - name: Run Integration Tests
        run: pytest tests/integration
      - name: Generate Coverage Report
        run: pytest --cov=app tests/
```

## 14. Test Data Management

### Test Data Sets:
1. **Basic Conversations**: Simple doctor-patient interactions
2. **Complex Medical Cases**: Multiple conditions, medications
3. **Edge Cases**: Unclear speech, technical terms
4. **Performance Data**: Large transcriptions, rapid updates

### Data Privacy:
- Use synthetic patient data only
- No real patient information in tests
- Secure test environment isolation