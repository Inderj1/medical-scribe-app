"""Integration tests for OpenAI Agents SDK with real API calls"""
import pytest
import asyncio
import base64
import json
import os
from unittest.mock import patch
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    check_note_quality
)


# Skip these tests if OPENAI_API_KEY is not set
SKIP_INTEGRATION = not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == ""


@pytest.mark.integration
class TestRealAPIIntegration:
    """Integration tests that make real API calls"""
    
    def test_real_whisper_transcription(self):
        """Test real Whisper API transcription"""
        # Start session
        session_id = "integration-test-1"
        start_transcription_session(session_id, "test-encounter")
        
        # Create a simple WAV file with silence (44 bytes header + audio data)
        # This is a minimal valid WAV file
        # Create proper WAV header for 2 seconds of audio
        data_size = 64000  # 2 seconds * 16000 samples/sec * 2 bytes/sample
        file_size = data_size + 36  # data + header (44 - 8)
        
        wav_header = bytes([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            # File size - 8 (little endian)
            (file_size & 0xff), ((file_size >> 8) & 0xff), ((file_size >> 16) & 0xff), ((file_size >> 24) & 0xff),
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6d, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
            0x01, 0x00,              # AudioFormat (PCM)
            0x01, 0x00,              # NumChannels (mono)
            0x80, 0x3e, 0x00, 0x00,  # SampleRate (16000)
            0x00, 0x7d, 0x00, 0x00,  # ByteRate (32000)
            0x02, 0x00,              # BlockAlign
            0x10, 0x00,              # BitsPerSample (16)
            0x64, 0x61, 0x74, 0x61,  # "data"
            # Data size (little endian)
            (data_size & 0xff), ((data_size >> 8) & 0xff), ((data_size >> 16) & 0xff), ((data_size >> 24) & 0xff)
        ])
        
        # Add 2 seconds of silence (16000 samples * 2 bytes per sample * 2 seconds)
        # This ensures we meet the 0.1 second minimum requirement
        audio_data = wav_header + bytes(64000)
        audio_base64 = base64.b64encode(audio_data).decode()
        
        # Process audio chunk (should trigger transcription)
        result = process_audio_chunk(session_id, audio_base64, 5000)
        
        # Should get a transcription result (likely empty or minimal for silence)
        assert "Transcribed segment" in result or "buffered" in result
        
        # Clean up
        end_transcription_session(session_id)
        
    def test_real_gpt4_analysis(self):
        """Test real GPT-4 clinical analysis"""
        test_transcript = """
        Patient presents with chest pain that started 3 days ago. 
        Pain is described as pressure-like, radiating to left arm.
        Blood pressure is 140/90, heart rate 88.
        Patient takes aspirin daily and has history of hypertension.
        """
        
        result = analyze_transcript(test_transcript, "test-encounter")
        
        # Should return the next agent
        assert isinstance(result, Agent)
        assert result == note_structuring_agent
        
        # Check that context was updated with analysis
        from app.agents.medical_scribe_agents import _handoff_context
        assert "clinical_sections" in _handoff_context
        assert isinstance(_handoff_context["clinical_sections"], dict)
        
    def test_real_full_pipeline(self):
        """Test full pipeline with real API calls"""
        # Use Swarm client
        client = Swarm()
        
        # Start with a medical transcript
        test_transcript = """
        Chief complaint: Severe headache for 2 days.
        History: Patient reports throbbing pain on right side of head.
        Medications: Ibuprofen 400mg as needed.
        Vital signs: BP 130/85, HR 76, Temp 98.6F.
        Assessment: Likely migraine headache.
        Plan: Prescribe sumatriptan, follow up in 1 week.
        """
        
        # Run through supervisor agent
        from app.agents.medical_scribe_agents import supervisor_agent
        
        response = client.run(
            agent=supervisor_agent,
            messages=[{
                "role": "user",
                "content": f"Process this medical transcript and create a clinical note: {test_transcript}"
            }]
        )
        
        # Check we got a response
        assert response.messages
        assert len(response.messages) > 0
        
        # The final message should contain a clinical note
        final_message = response.messages[-1]
        if isinstance(final_message, dict):
            content = final_message.get('content', '')
        else:
            content = final_message.content
        assert isinstance(content, str)
        assert len(content) > 0


@pytest.mark.integration  
class TestRealSwarmIntegration:
    """Test Swarm orchestration with real agents"""
    
    def test_swarm_agent_handoffs(self):
        """Test real agent handoffs through Swarm"""
        client = Swarm()
        
        # Start with transcription agent
        response = client.run(
            agent=transcription_agent,
            messages=[{
                "role": "user",
                "content": "Start a transcription session with session_id=swarm-test and encounter_id=encounter-123"
            }]
        )
        
        assert response.messages
        final_message = response.messages[-1]
        if isinstance(final_message, dict):
            content = final_message.get('content', '')
        else:
            content = final_message.content
        assert "started" in content.lower() or "session" in content.lower()
        
        # End session to trigger handoff
        response = client.run(
            agent=transcription_agent,
            messages=[{
                "role": "user", 
                "content": "End the transcription session swarm-test"
            }]
        )
        
        # Check that we got a response showing the agent processed the request
        # The handoff might have gone through the entire pipeline
        final_msg = response.messages[-1]
        if isinstance(final_msg, dict):
            content = final_msg.get('content', '')
        else:
            content = final_msg.content
        
        # If we got a clinical note, the handoff worked
        assert any(term in content.lower() for term in ["soap", "clinical note", "subjective", "objective", "assessment", "plan", "session", "ended", "transcript"])
        
    def test_quality_check_real(self):
        """Test quality checking with real API"""
        test_note = """
        SUBJECTIVE:
        Chief Complaint: Headache
        HPI: 2 days of severe headache
        
        OBJECTIVE:
        Vital Signs: BP 130/85, HR 76
        
        ASSESSMENT:
        Migraine headache
        
        PLAN:
        Sumatriptan prescribed
        Follow up in 1 week
        """
        
        result = check_note_quality(test_note)
        
        assert "Quality check complete" in result
        assert "Score:" in result
        assert "1.00" in result  # Should be complete


def test_api_key_configuration():
    """Test that API keys are properly configured"""
    from app.core.config import settings
    
    assert settings.OPENAI_API_KEY is not None
    assert len(settings.OPENAI_API_KEY) > 0
    
    # Key should be properly set
    assert settings.OPENAI_API_KEY.startswith("sk-")