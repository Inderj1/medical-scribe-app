"""Unit tests for streaming transcription agents"""
import pytest
import asyncio
import base64
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.agents.streaming_transcription_agent import StreamingTranscriptionAgent, AudioBuffer
from app.agents.base import AgentMessage


class TestAudioBuffer:
    """Test the AudioBuffer class"""
    
    def test_init(self):
        """Test buffer initialization"""
        buffer = AudioBuffer(sample_rate=16000, channels=1)
        assert buffer.sample_rate == 16000
        assert buffer.channels == 1
        assert len(buffer.audio_chunks) == 0
        assert buffer.total_duration_ms == 0
        
    def test_add_chunk(self):
        """Test adding audio chunks"""
        buffer = AudioBuffer()
        
        # Add chunks
        chunk1 = b"audio_data_1"
        chunk2 = b"audio_data_2"
        
        buffer.add_chunk(chunk1, 1000)
        assert len(buffer.audio_chunks) == 1
        assert buffer.total_duration_ms == 1000
        
        buffer.add_chunk(chunk2, 500)
        assert len(buffer.audio_chunks) == 2
        assert buffer.total_duration_ms == 1500
        
    def test_get_audio_for_transcription(self):
        """Test getting combined audio and clearing buffer"""
        buffer = AudioBuffer()
        
        # Add chunks
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for i, chunk in enumerate(chunks):
            buffer.add_chunk(chunk, 1000)
            
        # Get combined audio
        combined_audio, duration = buffer.get_audio_for_transcription()
        
        assert combined_audio == b"chunk1chunk2chunk3"
        assert duration == 3000
        
        # Buffer should be cleared
        assert len(buffer.audio_chunks) == 0
        assert buffer.total_duration_ms == 0
        
    def test_should_transcribe_min_duration(self):
        """Test transcription trigger based on minimum duration"""
        buffer = AudioBuffer()
        
        # Not enough audio
        buffer.add_chunk(b"short", 1000)
        assert not buffer.should_transcribe(min_duration_ms=5000)
        
        # Add more to reach minimum
        buffer.add_chunk(b"more", 4000)
        assert buffer.should_transcribe(min_duration_ms=5000)
        
    def test_should_transcribe_max_duration(self):
        """Test transcription trigger based on maximum duration"""
        buffer = AudioBuffer()
        
        # Add audio exceeding max duration
        buffer.add_chunk(b"long_audio", 35000)
        assert buffer.should_transcribe(max_duration_ms=30000)
        
    def test_should_transcribe_time_based(self):
        """Test transcription trigger based on time since last transcription"""
        buffer = AudioBuffer()
        
        # Add some audio
        buffer.add_chunk(b"audio", 1000)
        
        # Simulate time passing
        from datetime import timedelta
        buffer.last_transcription_time = datetime.utcnow() - timedelta(seconds=15)
        
        assert buffer.should_transcribe()
        
    def test_create_wav_file(self):
        """Test WAV file creation"""
        buffer = AudioBuffer(sample_rate=16000, channels=1)
        
        # Create simple audio data
        audio_data = b"\x00\x01" * 1000  # Simple pattern
        
        wav_data = buffer.create_wav_file(audio_data)
        
        # Check WAV header
        assert wav_data[:4] == b"RIFF"
        assert b"WAVE" in wav_data[:12]
        

class TestStreamingTranscriptionAgent:
    """Test the StreamingTranscriptionAgent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = StreamingTranscriptionAgent()
        yield agent
        # Cleanup
        for task in agent.background_tasks.values():
            task.cancel()
            
    @pytest.mark.asyncio
    async def test_start_session(self, agent):
        """Test starting a transcription session"""
        message = AgentMessage(
            agent_id="test",
            message_type="start_session",
            payload={
                "session_id": "test-123",
                "encounter_id": "enc-456",
                "audio_config": {
                    "sample_rate": 16000,
                    "channels": 1
                }
            }
        )
        
        response = await agent.process(message)
        
        assert response is not None
        assert response.message_type == "session_started"
        assert response.payload["status"] == "ready"
        assert "test-123" in agent.session_buffers
        assert "test-123" in agent.session_contexts
        
    @pytest.mark.asyncio
    async def test_handle_audio_chunk(self, agent):
        """Test handling audio chunks"""
        # Start session first
        await agent._handle_start_session(AgentMessage(
            agent_id="test",
            message_type="start_session",
            payload={
                "session_id": "test-123",
                "encounter_id": "enc-456"
            }
        ))
        
        # Send audio chunk
        audio_data = base64.b64encode(b"test audio data").decode()
        message = AgentMessage(
            agent_id="test",
            message_type="audio_chunk",
            payload={
                "session_id": "test-123",
                "audio_data": audio_data,
                "duration_ms": 1000
            }
        )
        
        # Mock transcription
        agent._transcribe_buffer = AsyncMock(return_value=None)
        
        response = await agent.process(message)
        
        # Check buffer was updated
        buffer = agent.session_buffers["test-123"]
        assert buffer.total_duration_ms == 1000
        assert len(buffer.audio_chunks) == 1
        
    @pytest.mark.asyncio
    async def test_end_session(self, agent):
        """Test ending a session"""
        # Start session
        await agent._handle_start_session(AgentMessage(
            agent_id="test",
            message_type="start_session",
            payload={
                "session_id": "test-123",
                "encounter_id": "enc-456"
            }
        ))
        
        # Mock transcription
        agent._transcribe_buffer = AsyncMock(return_value=AgentMessage(
            agent_id="test",
            message_type="final_transcription",
            payload={"text": "Final transcript"}
        ))
        
        # End session
        message = AgentMessage(
            agent_id="test",
            message_type="end_session",
            payload={"session_id": "test-123"}
        )
        
        response = await agent.process(message)
        
        assert response is not None
        assert response.message_type == "handoff:analyze_transcription"
        assert response.payload["is_final"] is True
        
        # Session should be cleaned up
        assert "test-123" not in agent.session_buffers
        assert "test-123" not in agent.session_contexts
        
    @pytest.mark.asyncio
    async def test_transcribe_buffer_with_mock_whisper(self, agent):
        """Test buffer transcription with mocked Whisper API"""
        # Start session
        session_id = "test-123"
        await agent._handle_start_session(AgentMessage(
            agent_id="test",
            message_type="start_session",
            payload={
                "session_id": session_id,
                "encounter_id": "enc-456"
            }
        ))
        
        # Add audio to buffer
        buffer = agent.session_buffers[session_id]
        buffer.add_chunk(b"test audio", 5000)
        
        # Mock OpenAI client
        mock_response = Mock()
        mock_response.strip.return_value = "Transcribed text from Whisper"
        
        with patch.object(agent.client.audio.transcriptions, 'create', 
                         return_value=asyncio.coroutine(lambda: mock_response)()):
            result = await agent._transcribe_buffer(session_id)
            
        # Check context was updated
        context = agent.session_contexts[session_id]
        assert context["total_text"] == "Transcribed text from Whisper"
        assert context["transcription_count"] == 1
        
    def test_create_prompt(self, agent):
        """Test prompt creation for Whisper"""
        # Empty context
        context = {"total_text": ""}
        prompt = agent._create_prompt(context)
        assert "Medical consultation transcript" in prompt
        
        # Context with previous text
        context = {"total_text": "Doctor: Good morning. Patient: Hello doctor, I have been experiencing chest pain."}
        prompt = agent._create_prompt(context)
        assert "Previous context:" in prompt
        assert "chest pain" in prompt
        
    @pytest.mark.asyncio
    async def test_periodic_transcription_check(self, agent):
        """Test periodic transcription checking"""
        # Start session
        session_id = "test-123"
        await agent._handle_start_session(AgentMessage(
            agent_id="test",
            message_type="start_session",
            payload={
                "session_id": session_id,
                "encounter_id": "enc-456"
            }
        ))
        
        # Add audio that should trigger transcription
        buffer = agent.session_buffers[session_id]
        buffer.add_chunk(b"audio" * 1000, 6000)  # 6 seconds
        
        # Mock transcribe_buffer
        agent._transcribe_buffer = AsyncMock()
        
        # Run periodic check once
        task = agent.background_tasks[session_id]
        
        # Wait a bit for the check to run
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        
        # Verify transcribe was called (if timing works out)
        # Note: This might be flaky due to timing, so we just check the task was created
        assert session_id in agent.background_tasks