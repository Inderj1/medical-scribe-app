"""End-to-end integration tests for streaming transcription"""
import pytest
import asyncio
import base64
import wave
import io
import numpy as np
from datetime import datetime

from app.agents.streaming_medical_scribe_supervisor import StreamingMedicalScribeSupervisor
from app.agents.streaming_transcription_agent import StreamingTranscriptionAgent
from app.agents.batch_clinical_context_agent import BatchClinicalContextAgent
from app.agents.batch_note_structuring_agent import BatchNoteStructuringAgent
from app.core.config import settings


def generate_audio_chunk(duration_ms: int, sample_rate: int = 16000) -> bytes:
    """Generate a fake audio chunk for testing"""
    # Calculate number of samples
    num_samples = int((duration_ms / 1000) * sample_rate)
    
    # Generate silent audio (zeros)
    audio_data = np.zeros(num_samples, dtype=np.int16)
    
    return audio_data.tobytes()


def create_test_wav_audio(text: str, duration_ms: int = 1000) -> bytes:
    """Create a test WAV file with metadata (not actual audio)"""
    # This is a mock - in production, this would be actual audio
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(16000)  # 16kHz
        
        # Generate silent audio
        audio_data = generate_audio_chunk(duration_ms)
        wav_file.writeframes(audio_data)
        
    wav_buffer.seek(0)
    return wav_buffer.read()


class TestStreamingIntegration:
    """Integration tests for the complete streaming pipeline"""
    
    @pytest.fixture
    async def supervisor(self):
        """Create a real supervisor instance"""
        supervisor = StreamingMedicalScribeSupervisor()
        # Give agents time to initialize
        await asyncio.sleep(0.5)
        yield supervisor
        await supervisor.shutdown()
        
    @pytest.mark.asyncio
    @pytest.mark.skipif(not settings.OPENAI_API_KEY, reason="OpenAI API key not configured")
    async def test_complete_streaming_session(self, supervisor):
        """Test a complete streaming session with mock audio"""
        print("\n=== Starting Complete Streaming Session Test ===")
        
        # Start session
        session_result = await supervisor.start_session(
            session_id="integration-test-123",
            encounter_id="encounter-456",
            transcription_id="transcription-789",
            audio_config={
                "sample_rate": 16000,
                "channels": 1,
                "format": "pcm16"
            },
            user_id="test-user"
        )
        
        assert session_result["status"] == "success"
        session_id = "integration-test-123"
        print("✓ Session started successfully")
        
        # Simulate medical conversation chunks
        conversation_chunks = [
            "Doctor: Good morning, Mr. Smith. What brings you in today?",
            "Patient: I've been having severe headaches for the past week.",
            "Doctor: Can you describe the headaches? Where exactly do you feel the pain?",
            "Patient: It's mostly on the right side of my head, like a throbbing pain.",
            "Doctor: On a scale of 1 to 10, how severe is the pain?",
            "Patient: It's about an 8 when it's at its worst.",
            "Doctor: Are you taking any medications currently?",
            "Patient: Just ibuprofen 400mg when the pain gets bad.",
            "Doctor: Any nausea or visual disturbances with the headaches?",
            "Patient: Yes, sometimes I see flashing lights before the headache starts.",
            "Doctor: Based on your symptoms, this sounds like it could be migraine.",
            "Doctor: Let's check your vital signs. Blood pressure is 130/85.",
            "Doctor: Heart rate is 76, temperature is 98.4 degrees.",
            "Doctor: I'm going to prescribe sumatriptan 50mg for acute migraine attacks.",
            "Doctor: Take it at the onset of symptoms. Follow up in two weeks."
        ]
        
        # Send audio chunks
        print("\nSending audio chunks...")
        for i, text in enumerate(conversation_chunks):
            # Create mock audio (in real use, this would be actual audio)
            audio_data = base64.b64encode(text.encode()).decode()
            
            result = await supervisor.process_audio_chunk(
                session_id=session_id,
                audio_data=audio_data,
                duration_ms=2000,  # 2 seconds per chunk
                sequence_number=i
            )
            
            assert result["status"] == "success"
            print(f"✓ Chunk {i+1}/{len(conversation_chunks)} processed")
            
            # Small delay between chunks
            await asyncio.sleep(0.1)
            
        # Check session status
        print("\nChecking session status...")
        status = await supervisor.get_session_status(session_id)
        assert status["status"] == "active"
        assert status["audio_chunks_received"] == len(conversation_chunks)
        print(f"✓ Received {status['audio_chunks_received']} chunks")
        print(f"✓ Total duration: {status['total_duration_ms']}ms")
        
        # Trigger clinical analysis
        print("\nTriggering clinical analysis...")
        analysis_result = await supervisor.trigger_clinical_analysis(session_id)
        assert analysis_result["status"] == "success"
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Get current transcript
        print("\nGetting current transcript...")
        transcript_result = await supervisor.get_current_transcript(session_id)
        
        # With mock transcription, we should have some transcript
        # (In production with real Whisper API, this would be actual transcription)
        print(f"✓ Transcript length: {transcript_result['transcript_length']} chars")
        
        # End session
        print("\nEnding session...")
        end_result = await supervisor.end_session(session_id)
        
        assert end_result["status"] == "success"
        assert end_result["audio_chunks_processed"] == len(conversation_chunks)
        
        print("\n=== Session Results ===")
        print(f"Duration: {end_result['duration_seconds']:.1f} seconds")
        print(f"Audio chunks: {end_result['audio_chunks_processed']}")
        print(f"Total audio: {end_result['total_audio_duration_ms']}ms")
        
        if end_result.get("clinical_note"):
            print("\nClinical Note Preview:")
            print("-" * 40)
            print(end_result["clinical_note"][:500] + "..." if len(end_result["clinical_note"]) > 500 else end_result["clinical_note"])
            
        print("\n✓ Integration test completed successfully!")
        
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, supervisor):
        """Test handling multiple concurrent sessions"""
        print("\n=== Testing Concurrent Sessions ===")
        
        # Start multiple sessions
        sessions = []
        for i in range(3):
            result = await supervisor.start_session(
                session_id=f"concurrent-{i}",
                encounter_id=f"encounter-{i}",
                transcription_id=f"trans-{i}",
                audio_config={"sample_rate": 16000},
                user_id="test-user"
            )
            assert result["status"] == "success"
            sessions.append(f"concurrent-{i}")
            
        print(f"✓ Started {len(sessions)} concurrent sessions")
        
        # Send audio to each session
        for session_id in sessions:
            audio_data = base64.b64encode(f"Audio for {session_id}".encode()).decode()
            result = await supervisor.process_audio_chunk(
                session_id=session_id,
                audio_data=audio_data,
                duration_ms=1000
            )
            assert result["status"] == "success"
            
        print("✓ Sent audio to all sessions")
        
        # Check all sessions are active
        user_sessions = await supervisor.get_user_sessions("test-user")
        assert len(user_sessions) >= 3
        
        # End all sessions
        for session_id in sessions:
            await supervisor.end_session(session_id)
            
        print("✓ All concurrent sessions ended successfully")
        
    @pytest.mark.asyncio
    async def test_session_recovery(self, supervisor):
        """Test session recovery after errors"""
        print("\n=== Testing Session Recovery ===")
        
        # Start session
        session_id = "recovery-test"
        await supervisor.start_session(
            session_id=session_id,
            encounter_id="enc-recovery",
            transcription_id="trans-recovery",
            audio_config={},
            user_id="test-user"
        )
        
        # Send invalid audio chunk
        try:
            result = await supervisor.process_audio_chunk(
                session_id=session_id,
                audio_data="invalid-base64!@#",
                duration_ms=1000
            )
            # Should handle gracefully
        except Exception as e:
            print(f"✓ Error handled: {str(e)}")
            
        # Session should still be active
        status = await supervisor.get_session_status(session_id)
        assert status["session_id"] == session_id
        
        # Send valid chunk
        valid_audio = base64.b64encode(b"Valid audio").decode()
        result = await supervisor.process_audio_chunk(
            session_id=session_id,
            audio_data=valid_audio,
            duration_ms=1000
        )
        assert result["status"] == "success"
        
        print("✓ Session recovered after error")
        
        # Clean up
        await supervisor.end_session(session_id)
        
    @pytest.mark.asyncio
    async def test_audio_buffering(self, supervisor):
        """Test audio buffering and transcription triggering"""
        print("\n=== Testing Audio Buffering ===")
        
        session_id = "buffer-test"
        await supervisor.start_session(
            session_id=session_id,
            encounter_id="enc-buffer",
            transcription_id="trans-buffer",
            audio_config={"sample_rate": 16000},
            user_id="test-user"
        )
        
        # Send small chunks that should be buffered
        small_chunks_sent = 0
        for i in range(10):
            audio_data = base64.b64encode(f"Chunk {i}".encode()).decode()
            result = await supervisor.process_audio_chunk(
                session_id=session_id,
                audio_data=audio_data,
                duration_ms=500  # 0.5 seconds each
            )
            small_chunks_sent += 1
            
        print(f"✓ Sent {small_chunks_sent} small chunks (500ms each)")
        
        # Check that chunks were received
        status = await supervisor.get_session_status(session_id)
        assert status["audio_chunks_received"] == small_chunks_sent
        assert status["total_duration_ms"] == small_chunks_sent * 500
        
        print(f"✓ Total buffered duration: {status['total_duration_ms']}ms")
        
        # Clean up
        await supervisor.end_session(session_id)


# Mock the Whisper API for testing
async def mock_whisper_transcribe(self, model, file, language, prompt, response_format):
    """Mock Whisper API response"""
    # Read the file to simulate processing
    file_content = file.read()
    
    # In tests, we encode text in the audio data
    try:
        # Try to extract the mock text
        # This is just for testing - real audio would be transcribed
        return "Patient reports severe headaches on the right side, throbbing pain, severity 8 out of 10. Taking ibuprofen 400mg. Experiencing visual auras. Vital signs: BP 130/85, HR 76, temp 98.4. Prescribed sumatriptan 50mg for migraine."
    except:
        return "Mock transcription of audio segment"


# Apply mock for tests
pytest.fixture(autouse=True)
def mock_openai_whisper(monkeypatch):
    """Mock OpenAI Whisper API for all tests"""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "test":
        monkeypatch.setattr(
            "openai.AsyncOpenAI.audio.transcriptions.create",
            mock_whisper_transcribe
        )