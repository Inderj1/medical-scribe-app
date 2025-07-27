"""Integration tests for streaming transcription API endpoints"""
import pytest
import asyncio
import base64
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.models.user import User
from app.models.encounter import Encounter
from app.models.transcription import Transcription
from app.core.auth import get_current_user
from app.db.session import get_db


# Mock user for testing
mock_user = User(
    id="test-user-123",
    email="test@example.com",
    full_name="Test User"
)

# Mock database session
class MockDB:
    def __init__(self):
        self.encounters = []
        self.transcriptions = []
        
    def query(self, model):
        return self
        
    def filter(self, *args, **kwargs):
        return self
        
    def first(self):
        # Return mock encounter
        return Encounter(
            id="test-encounter-123",
            user_id="test-user-123",
            patient_id="patient-456"
        )
        
    def add(self, obj):
        if isinstance(obj, Transcription):
            obj.id = "test-transcription-123"
            self.transcriptions.append(obj)
            
    def commit(self):
        pass
        
    def refresh(self, obj):
        pass


# Override dependencies
async def override_get_current_user():
    return mock_user

def override_get_db():
    return MockDB()


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


class TestStreamingAPI:
    """Test streaming transcription API endpoints"""
    
    @pytest.fixture
    def mock_supervisor(self):
        """Mock the streaming supervisor"""
        with patch('app.api.streaming_transcription.get_streaming_supervisor') as mock:
            supervisor = Mock()
            mock.return_value = supervisor
            yield supervisor
            
    def test_start_session_success(self, mock_supervisor):
        """Test successful session start"""
        # Mock supervisor response
        mock_supervisor.start_session = AsyncMock(return_value={
            "status": "success",
            "session_id": "test-session-123",
            "message": "Session started successfully"
        })
        
        # Make request
        response = client.post(
            "/api/v1/streaming/session/start",
            json={
                "encounter_id": "test-encounter-123",
                "audio_config": {
                    "sample_rate": 16000,
                    "channels": 1,
                    "format": "pcm16"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "session_id" in data
        assert data["message"] == "Transcription session started successfully"
        
    def test_start_session_encounter_not_found(self, mock_supervisor):
        """Test starting session with invalid encounter"""
        # Mock database to return None
        with patch.object(MockDB, 'first', return_value=None):
            response = client.post(
                "/api/v1/streaming/session/start",
                json={
                    "encounter_id": "invalid-encounter"
                }
            )
            
        assert response.status_code == 404
        assert response.json()["detail"] == "Encounter not found"
        
    def test_upload_audio_chunk_success(self, mock_supervisor):
        """Test successful audio chunk upload"""
        # Mock supervisor
        mock_supervisor.validate_session.return_value = True
        mock_supervisor.process_audio_chunk = AsyncMock(return_value={
            "status": "success",
            "chunks_received": 5,
            "total_duration_ms": 5000,
            "current_transcript_preview": "Doctor: Good morning..."
        })
        
        # Prepare audio data
        audio_data = base64.b64encode(b"test audio data").decode()
        
        # Make request
        response = client.post(
            "/api/v1/streaming/session/audio-chunk",
            json={
                "session_id": "test-session-123",
                "audio_data": audio_data,
                "duration_ms": 1000,
                "sequence_number": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["chunks_received"] == 5
        assert data["total_duration_ms"] == 5000
        
    def test_upload_audio_chunk_invalid_session(self, mock_supervisor):
        """Test audio chunk upload with invalid session"""
        mock_supervisor.validate_session.return_value = False
        
        response = client.post(
            "/api/v1/streaming/session/audio-chunk",
            json={
                "session_id": "invalid-session",
                "audio_data": "data",
                "duration_ms": 1000
            }
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found or unauthorized"
        
    def test_end_session_success(self, mock_supervisor):
        """Test successful session end"""
        # Mock supervisor
        mock_supervisor.validate_session.return_value = True
        mock_supervisor.end_session = AsyncMock(return_value={
            "status": "success",
            "transcription_id": "test-transcription-123",
            "final_transcription": "Complete transcript",
            "clinical_note": "**CHIEF COMPLAINT:**\nChest pain"
        })
        
        # Make request
        response = client.post(
            "/api/v1/streaming/session/end",
            json={
                "session_id": "test-session-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["message"] == "Session ended successfully"
        
    def test_get_session_status(self, mock_supervisor):
        """Test getting session status"""
        mock_supervisor.validate_session.return_value = True
        mock_supervisor.get_session_status = AsyncMock(return_value={
            "session_id": "test-session-123",
            "status": "active",
            "duration_seconds": 120,
            "audio_chunks_received": 60,
            "total_duration_ms": 120000,
            "transcript_length": 1500,
            "clinical_sections_identified": ["chief_complaint", "medications"]
        })
        
        response = client.get("/api/v1/streaming/session/test-session-123/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["status"] == "active"
        assert data["audio_chunks_received"] == 60
        assert len(data["clinical_sections_identified"]) == 2
        
    def test_get_current_transcript(self, mock_supervisor):
        """Test getting current transcript"""
        mock_supervisor.validate_session.return_value = True
        mock_supervisor.get_current_transcript = AsyncMock(return_value={
            "session_id": "test-session-123",
            "current_transcript": "Doctor: What brings you in today?\nPatient: I have chest pain.",
            "clinical_sections": {
                "chief_complaint": "Chest pain"
            },
            "transcript_length": 60
        })
        
        response = client.get("/api/v1/streaming/session/test-session-123/transcript")
        
        assert response.status_code == 200
        data = response.json()
        assert "current_transcript" in data
        assert "clinical_sections" in data
        assert data["clinical_sections"]["chief_complaint"] == "Chest pain"
        
    def test_trigger_clinical_update(self, mock_supervisor):
        """Test triggering clinical analysis"""
        mock_supervisor.validate_session.return_value = True
        mock_supervisor.trigger_clinical_analysis = AsyncMock(return_value={
            "status": "success",
            "message": "Clinical analysis triggered"
        })
        
        response = client.post("/api/v1/streaming/session/test-session-123/clinical-update")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
    def test_get_audio_config(self):
        """Test getting recommended audio configuration"""
        response = client.get("/api/v1/streaming/audio-config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sample_rate"] == 16000
        assert data["channels"] == 1
        assert data["format"] == "pcm16"
        assert "chunk_duration_ms" in data
        assert "min_chunk_size_bytes" in data
        
    def test_get_active_sessions(self, mock_supervisor):
        """Test getting active sessions for user"""
        mock_supervisor.get_user_sessions = AsyncMock(return_value=[
            {
                "session_id": "session-1",
                "encounter_id": "enc-1",
                "status": "active",
                "start_time": "2024-01-20T10:00:00",
                "duration_seconds": 300
            },
            {
                "session_id": "session-2",
                "encounter_id": "enc-2",
                "status": "active",
                "start_time": "2024-01-20T10:05:00",
                "duration_seconds": 60
            }
        ])
        
        response = client.get("/api/v1/streaming/session/active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["session_id"] == "session-1"
        assert data[1]["session_id"] == "session-2"


class TestStreamingAPIValidation:
    """Test API input validation"""
    
    def test_start_session_missing_encounter_id(self):
        """Test starting session without encounter_id"""
        response = client.post(
            "/api/v1/streaming/session/start",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
        
    def test_audio_chunk_invalid_base64(self):
        """Test audio chunk with invalid base64"""
        with patch('app.api.streaming_transcription.get_streaming_supervisor') as mock:
            supervisor = Mock()
            supervisor.validate_session.return_value = True
            supervisor.process_audio_chunk = AsyncMock(side_effect=Exception("Invalid base64"))
            mock.return_value = supervisor
            
            response = client.post(
                "/api/v1/streaming/session/audio-chunk",
                json={
                    "session_id": "test-session",
                    "audio_data": "invalid-base64!@#",
                    "duration_ms": 1000
                }
            )
            
            assert response.status_code == 500
            
    def test_audio_chunk_missing_fields(self):
        """Test audio chunk with missing required fields"""
        response = client.post(
            "/api/v1/streaming/session/audio-chunk",
            json={
                "session_id": "test-session"
                # Missing audio_data and duration_ms
            }
        )
        
        assert response.status_code == 422