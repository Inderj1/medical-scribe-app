"""Tests for OpenAI Agents SDK implementation with Swarm"""
import pytest
import asyncio
import base64
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from swarm import Swarm, Agent
from app.agents.medical_scribe_agents import (
    transcription_agent,
    clinical_analysis_agent,
    note_structuring_agent,
    quality_assurance_agent,
    start_transcription_session,
    process_audio_chunk,
    end_transcription_session,
    analyze_transcript,
    format_clinical_note,
    check_note_quality,
    AudioBuffer
)


class TestAudioBuffer:
    """Test the AudioBuffer class"""
    
    def test_init(self):
        """Test buffer initialization"""
        buffer = AudioBuffer(sample_rate=16000)
        assert buffer.sample_rate == 16000
        assert len(buffer.audio_chunks) == 0
        assert buffer.total_duration_ms == 0
        
    def test_add_chunk(self):
        """Test adding audio chunks"""
        buffer = AudioBuffer()
        
        chunk1 = b"audio_data_1"
        chunk2 = b"audio_data_2"
        
        buffer.add_chunk(chunk1, 1000)
        assert len(buffer.audio_chunks) == 1
        assert buffer.total_duration_ms == 1000
        
        buffer.add_chunk(chunk2, 500)
        assert len(buffer.audio_chunks) == 2
        assert buffer.total_duration_ms == 1500
        
    def test_should_transcribe(self):
        """Test transcription trigger logic"""
        buffer = AudioBuffer()
        
        # Not enough audio
        buffer.add_chunk(b"short", 1000)
        assert not buffer.should_transcribe()
        
        # Enough audio
        buffer.add_chunk(b"more", 4500)
        assert buffer.should_transcribe()
        
    def test_get_audio_and_clear(self):
        """Test getting combined audio and clearing buffer"""
        buffer = AudioBuffer()
        
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for chunk in chunks:
            buffer.add_chunk(chunk, 1000)
            
        combined, duration = buffer.get_audio_and_clear()
        
        assert combined == b"chunk1chunk2chunk3"
        assert duration == 3000
        assert len(buffer.audio_chunks) == 0
        assert buffer.total_duration_ms == 0


class TestAgentFunctions:
    """Test individual agent functions"""
    
    def test_start_transcription_session(self):
        """Test starting a transcription session"""
        session_id = "test-session-123"
        encounter_id = "test-encounter-456"
        
        result = start_transcription_session(session_id, encounter_id)
        
        assert f"Started transcription session {session_id}" in result
        assert session_id in result
        assert encounter_id in result
        
    def test_process_audio_chunk_no_session(self):
        """Test processing audio with no session"""
        result = process_audio_chunk("invalid-session", "data", 1000)
        assert "Error: Session not found" in result
        
    @patch('app.agents.medical_scribe_agents.sync_client')
    def test_process_audio_chunk_with_transcription(self, mock_client):
        """Test processing audio that triggers transcription"""
        # Start session first
        session_id = "test-session"
        start_transcription_session(session_id, "encounter-123")
        
        # Mock Whisper response
        mock_response = Mock()
        mock_response.text = "Patient has chest pain"
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        # Add enough audio to trigger transcription
        audio_data = base64.b64encode(b"audio" * 1000).decode()
        result = process_audio_chunk(session_id, audio_data, 5000)
        
        assert "Transcribed segment 1" in result
        assert "Patient has chest pain" in result
        
    def test_end_transcription_session_no_session(self):
        """Test ending non-existent session"""
        result = end_transcription_session("invalid-session")
        assert "Error: Session not found" in result
        
    def test_end_transcription_session_returns_agent(self):
        """Test ending session returns proper agent"""
        # Start session
        session_id = "test-session"
        start_transcription_session(session_id, "encounter-123")
        
        # End session
        result = end_transcription_session(session_id)
        
        assert isinstance(result, Agent)
        assert result == clinical_analysis_agent
        
    @patch('app.agents.medical_scribe_agents.sync_client')
    def test_analyze_transcript(self, mock_client):
        """Test transcript analysis"""
        # Mock GPT-4 response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "chief_complaint": "Chest pain",
            "vital_signs": "BP 120/80, HR 72",
            "assessment": "Possible angina",
            "plan": "ECG, troponin levels"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        result = analyze_transcript("Patient has chest pain", "encounter-123")
        
        assert isinstance(result, Agent)
        assert result == note_structuring_agent
        
    def test_format_clinical_note_soap(self):
        """Test SOAP note formatting"""
        clinical_sections = {
            "chief_complaint": "Chest pain",
            "history_of_present_illness": "3 days of intermittent chest pain",
            "vital_signs": "BP 120/80, HR 72",
            "physical_examination": "Clear lungs, regular heart rhythm",
            "assessment": "Possible angina",
            "plan": "ECG, troponin, aspirin"
        }
        
        note = format_clinical_note(json.dumps(clinical_sections), "soap")
        
        assert "SUBJECTIVE:" in note
        assert "Chief Complaint: Chest pain" in note
        assert "OBJECTIVE:" in note
        assert "Vital Signs: BP 120/80, HR 72" in note
        assert "ASSESSMENT:" in note
        assert "PLAN:" in note
        
    def test_format_clinical_note_bullet(self):
        """Test bullet point formatting"""
        clinical_sections = {
            "chief_complaint": "Headache",
            "medications": "Ibuprofen 400mg PRN"
        }
        
        note = format_clinical_note(json.dumps(clinical_sections), "bullet")
        
        assert "CLINICAL NOTE:" in note
        assert "• Chief Complaint: Headache" in note
        assert "• Medications: Ibuprofen 400mg PRN" in note
        
    def test_check_note_quality(self):
        """Test quality checking"""
        good_note = """
        SUBJECTIVE:
        Chief Complaint: Chest pain
        
        ASSESSMENT:
        Possible angina
        
        PLAN:
        ECG, medication
        """
        
        result = check_note_quality(good_note)
        
        assert "Quality check complete" in result
        assert "Score: 1.00" in result
        
        # Test incomplete note
        bad_note = "Patient has symptoms"
        result = check_note_quality(bad_note)
        
        assert "Score: 0.00" in result


class TestAgentHandoffs:
    """Test agent handoff behavior"""
    
    def test_transcription_to_clinical_handoff(self):
        """Test handoff from transcription to clinical analysis"""
        # Start and end session
        session_id = "test-handoff"
        start_transcription_session(session_id, "encounter-123")
        
        agent = end_transcription_session(session_id)
        
        assert isinstance(agent, Agent)
        assert agent == clinical_analysis_agent
        
    @patch('app.agents.medical_scribe_agents.sync_client')
    def test_clinical_to_note_handoff(self, mock_client):
        """Test handoff from clinical to note structuring"""
        # Mock GPT-4 response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "chief_complaint": "Test complaint"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        agent = analyze_transcript("test transcript", "encounter-123")
        
        assert isinstance(agent, Agent)
        assert agent == note_structuring_agent


class TestSwarmIntegration:
    """Test Swarm integration"""
    
    @pytest.fixture
    def swarm_client(self):
        """Create Swarm client"""
        return Swarm()
        
    def test_agent_creation(self):
        """Test that agents are properly created"""
        assert transcription_agent.name == "TranscriptionAgent"
        assert clinical_analysis_agent.name == "ClinicalAnalysisAgent"
        assert note_structuring_agent.name == "NoteStructuringAgent"
        assert quality_assurance_agent.name == "QualityAssuranceAgent"
        
    def test_agent_functions_registered(self):
        """Test that functions are registered with agents"""
        assert len(transcription_agent.functions) == 3
        assert start_transcription_session in transcription_agent.functions
        assert process_audio_chunk in transcription_agent.functions
        assert end_transcription_session in transcription_agent.functions
        
        assert len(clinical_analysis_agent.functions) == 1
        assert analyze_transcript in clinical_analysis_agent.functions
        
        assert len(note_structuring_agent.functions) == 1
        assert format_clinical_note in note_structuring_agent.functions
        
    @patch('app.agents.medical_scribe_agents.sync_client')
    def test_full_pipeline_simulation(self, mock_client):
        """Test full agent pipeline"""
        # Mock Whisper
        mock_whisper = Mock()
        mock_whisper.text = "Patient reports severe headache"
        mock_client.audio.transcriptions.create.return_value = mock_whisper
        
        # Mock GPT-4
        mock_gpt = Mock()
        mock_gpt.choices = [Mock()]
        mock_gpt.choices[0].message.content = json.dumps({
            "chief_complaint": "Severe headache",
            "assessment": "Migraine",
            "plan": "Sumatriptan"
        })
        mock_client.chat.completions.create.return_value = mock_gpt
        
        # Start session
        session_id = "pipeline-test"
        start_transcription_session(session_id, "encounter-123")
        
        # Process audio
        audio_data = base64.b64encode(b"audio" * 2000).decode()
        process_audio_chunk(session_id, audio_data, 5000)
        
        # End session - get agent
        agent1 = end_transcription_session(session_id)
        assert agent1 == clinical_analysis_agent
        
        # Process clinical analysis - get agent
        agent2 = analyze_transcript("Patient reports severe headache", "encounter-123")
        assert agent2 == note_structuring_agent
        
        # Format note - final result
        note = format_clinical_note('{"chief_complaint": "Severe headache"}', "soap")
        assert "SUBJECTIVE:" in note
        assert "Chief Complaint: Severe headache" in note