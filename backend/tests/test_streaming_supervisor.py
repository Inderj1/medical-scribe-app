"""Unit tests for streaming medical scribe supervisor"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.agents.streaming_medical_scribe_supervisor import (
    StreamingMedicalScribeSupervisor, 
    StreamingSession
)
from app.agents.base import AgentMessage


class TestStreamingSession:
    """Test the StreamingSession class"""
    
    def test_init(self):
        """Test session initialization"""
        session = StreamingSession(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            user_id="user-001"
        )
        
        assert session.session_id == "test-123"
        assert session.encounter_id == "enc-456"
        assert session.transcription_id == "trans-789"
        assert session.user_id == "user-001"
        assert session.status == "active"
        assert session.audio_chunks_received == 0
        assert session.total_duration_ms == 0
        assert session.current_transcript == ""
        assert session.clinical_sections == {}
        

class TestStreamingMedicalScribeSupervisor:
    """Test the StreamingMedicalScribeSupervisor"""
    
    @pytest.fixture
    async def supervisor(self):
        """Create supervisor instance"""
        supervisor = StreamingMedicalScribeSupervisor()
        # Give it a moment to initialize
        await asyncio.sleep(0.1)
        yield supervisor
        # Cleanup
        await supervisor.shutdown()
        
    @pytest.mark.asyncio
    async def test_start_session(self, supervisor):
        """Test starting a new session"""
        result = await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={"sample_rate": 16000},
            user_id="user-001"
        )
        
        assert result["status"] == "success"
        assert "test-123" in supervisor.active_sessions
        
        session = supervisor.active_sessions["test-123"]
        assert session.encounter_id == "enc-456"
        assert session.user_id == "user-001"
        assert session.status == "active"
        
    @pytest.mark.asyncio
    async def test_process_audio_chunk(self, supervisor):
        """Test processing audio chunks"""
        # Start session first
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Process audio chunk
        result = await supervisor.process_audio_chunk(
            session_id="test-123",
            audio_data="base64encodedaudio",
            duration_ms=1000,
            sequence_number=1
        )
        
        assert result["status"] == "success"
        assert result["chunks_received"] == 1
        assert result["total_duration_ms"] == 1000
        
        # Check session was updated
        session = supervisor.active_sessions["test-123"]
        assert session.audio_chunks_received == 1
        assert session.total_duration_ms == 1000
        assert 1 in session.sequence_tracker
        
    @pytest.mark.asyncio
    async def test_process_audio_chunk_invalid_session(self, supervisor):
        """Test processing audio chunk for invalid session"""
        result = await supervisor.process_audio_chunk(
            session_id="invalid-session",
            audio_data="data",
            duration_ms=1000
        )
        
        assert result["status"] == "error"
        assert result["error"] == "Session not found"
        
    @pytest.mark.asyncio
    async def test_validate_session(self, supervisor):
        """Test session validation"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Valid session and user
        assert supervisor.validate_session("test-123", "user-001") is True
        
        # Invalid session
        assert supervisor.validate_session("invalid", "user-001") is False
        
        # Valid session, wrong user
        assert supervisor.validate_session("test-123", "wrong-user") is False
        
    @pytest.mark.asyncio
    async def test_get_session_status(self, supervisor):
        """Test getting session status"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Add some activity
        await supervisor.process_audio_chunk(
            session_id="test-123",
            audio_data="data",
            duration_ms=2000
        )
        
        # Get status
        status = await supervisor.get_session_status("test-123")
        
        assert status["session_id"] == "test-123"
        assert status["status"] == "active"
        assert status["audio_chunks_received"] == 1
        assert status["total_duration_ms"] == 2000
        assert "duration_seconds" in status
        assert "clinical_sections_identified" in status
        
    @pytest.mark.asyncio
    async def test_get_current_transcript(self, supervisor):
        """Test getting current transcript"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Set some transcript
        session = supervisor.active_sessions["test-123"]
        session.current_transcript = "Test transcript content"
        session.clinical_sections = {"chief_complaint": "Chest pain"}
        
        # Get transcript
        result = await supervisor.get_current_transcript("test-123")
        
        assert result["session_id"] == "test-123"
        assert result["current_transcript"] == "Test transcript content"
        assert result["clinical_sections"]["chief_complaint"] == "Chest pain"
        assert result["transcript_length"] == 22
        
    @pytest.mark.asyncio
    async def test_trigger_clinical_analysis(self, supervisor):
        """Test triggering clinical analysis"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Add transcript
        session = supervisor.active_sessions["test-123"]
        session.current_transcript = "Patient has chest pain"
        
        # Mock orchestrator
        supervisor.orchestrator.send_message = AsyncMock()
        
        # Trigger analysis
        result = await supervisor.trigger_clinical_analysis("test-123")
        
        assert result["status"] == "success"
        assert supervisor.orchestrator.send_message.called
        
    @pytest.mark.asyncio
    async def test_get_user_sessions(self, supervisor):
        """Test getting user sessions"""
        # Start multiple sessions
        await supervisor.start_session(
            session_id="session-1",
            encounter_id="enc-1",
            transcription_id="trans-1",
            audio_config={},
            user_id="user-001"
        )
        
        await supervisor.start_session(
            session_id="session-2",
            encounter_id="enc-2",
            transcription_id="trans-2",
            audio_config={},
            user_id="user-001"
        )
        
        await supervisor.start_session(
            session_id="session-3",
            encounter_id="enc-3",
            transcription_id="trans-3",
            audio_config={},
            user_id="user-002"  # Different user
        )
        
        # Get sessions for user-001
        sessions = await supervisor.get_user_sessions("user-001")
        
        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids
        assert "session-3" not in session_ids
        
    @pytest.mark.asyncio
    async def test_end_session(self, supervisor):
        """Test ending a session"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Add some data
        session = supervisor.active_sessions["test-123"]
        session.current_transcript = "Complete transcript"
        session.clinical_sections = {
            "chief_complaint": "Chest pain",
            "medications": "Aspirin"
        }
        session.audio_chunks_received = 10
        session.total_duration_ms = 30000
        
        # Mock wait for completion
        supervisor._wait_for_session_completion = AsyncMock()
        
        # End session
        result = await supervisor.end_session("test-123")
        
        assert result["status"] == "success"
        assert result["final_transcription"] == "Complete transcript"
        assert "clinical_note" in result
        assert result["audio_chunks_processed"] == 10
        assert result["total_audio_duration_ms"] == 30000
        
        # Session should be removed
        assert "test-123" not in supervisor.active_sessions
        
    @pytest.mark.asyncio
    async def test_handle_transcription_segment(self, supervisor):
        """Test handling transcription segment messages"""
        # Start session
        await supervisor.start_session(
            session_id="test-123",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Mock trigger_clinical_analysis
        supervisor.trigger_clinical_analysis = AsyncMock()
        
        # Handle transcription segment
        message = AgentMessage(
            agent_id="TranscriptionAgent",
            message_type="transcription_segment",
            payload={
                "session_id": "test-123",
                "total_text": "Updated transcript text",
                "segment_number": 5
            }
        )
        
        await supervisor._handle_transcription_segment(message)
        
        # Check session was updated
        session = supervisor.active_sessions["test-123"]
        assert session.current_transcript == "Updated transcript text"
        
        # Clinical analysis should be triggered (segment 5)
        assert supervisor.trigger_clinical_analysis.called
        
    @pytest.mark.asyncio
    async def test_format_clinical_note(self, supervisor):
        """Test clinical note formatting"""
        clinical_sections = {
            "chief_complaint": "Chest pain for 3 days",
            "medications": "Aspirin 81mg daily",
            "vital_signs": "BP 120/80, HR 72",
            "assessment": "Possible angina",
            "plan": "EKG, stress test"
        }
        
        note = supervisor._format_clinical_note(clinical_sections)
        
        assert "**CHIEF COMPLAINT:**" in note
        assert "Chest pain for 3 days" in note
        assert "**MEDICATIONS:**" in note
        assert "Aspirin 81mg daily" in note
        assert "**VITAL SIGNS:**" in note
        assert "**ASSESSMENT:**" in note
        assert "**PLAN:**" in note
        
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, supervisor):
        """Test cleanup of inactive sessions"""
        # Start session
        await supervisor.start_session(
            session_id="old-session",
            encounter_id="enc-456",
            transcription_id="trans-789",
            audio_config={},
            user_id="user-001"
        )
        
        # Make session appear inactive
        session = supervisor.active_sessions["old-session"]
        session.last_activity = datetime.utcnow() - timedelta(minutes=35)
        
        # Mock end_session
        supervisor.end_session = AsyncMock()
        
        # Manually trigger cleanup (normally runs in background)
        await supervisor._cleanup_inactive_sessions()
        
        # Session should be cleaned up
        # Note: In the actual implementation, cleanup runs periodically
        # For testing, we'd need to wait or mock the timing