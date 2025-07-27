"""Test script for streaming transcription system"""
import asyncio
import base64
import json
from pathlib import Path

# Add the app directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.streaming_medical_scribe_supervisor import StreamingMedicalScribeSupervisor
from app.core.config import settings

# Simulate audio chunks (in real use, these would come from the microphone)
SIMULATED_TRANSCRIPT_CHUNKS = [
    "Doctor: Good morning, Mrs. Johnson. What brings you in today?",
    "Patient: I've been having chest pain for the past three days.",
    "It started suddenly when I was walking up the stairs.",
    "Doctor: Can you describe the pain for me?",
    "Patient: It's a sharp pain, right in the center of my chest.",
    "It gets worse when I take a deep breath or move around.",
    "Doctor: I see. On a scale of 1 to 10, how would you rate the pain?",
    "Patient: It's about a 7 when it's at its worst, maybe a 4 right now.",
    "Doctor: Any other symptoms? Shortness of breath, nausea, sweating?",
    "Patient: Yes, I've been a bit short of breath, especially when the pain is bad.",
    "Doctor: Are you currently taking any medications?",
    "Patient: I take metformin 500 mg twice daily for my diabetes,",
    "and lisinopril 10 mg once daily for blood pressure.",
    "Doctor: Any drug allergies?",
    "Patient: I'm allergic to penicillin - I get a rash.",
    "Doctor: Let me check your vital signs.",
    "Your blood pressure is 145/90, heart rate is 88,",
    "temperature is 98.6, and oxygen saturation is 97%.",
    "Doctor: I'm going to do a physical exam now.",
    "I hear some mild wheezing in your left lung base.",
    "Your heart sounds are regular without murmurs.",
    "Doctor: Based on your symptoms and examination,",
    "I'm concerned about possible pleuritis or costochondritis.",
    "We'll need to do a chest X-ray and an EKG to rule out any cardiac issues.",
    "I'm going to prescribe ibuprofen 600 mg three times daily",
    "for the pain and inflammation.",
    "Please follow up in one week,",
    "or sooner if the pain worsens or you develop new symptoms.",
    "Any questions?",
    "Patient: No, that makes sense. Thank you, doctor."
]


def simulate_audio_chunk(text: str) -> str:
    """Simulate converting text to audio chunk (base64 encoded)"""
    # In real use, this would be actual PCM audio data
    # For testing, we'll just encode the text
    return base64.b64encode(text.encode()).decode()


async def test_streaming_transcription():
    """Test the streaming transcription system"""
    print("Starting streaming transcription test...")
    
    # Initialize supervisor
    supervisor = StreamingMedicalScribeSupervisor()
    
    # Give the system a moment to initialize
    await asyncio.sleep(1)
    
    # Start a session
    session_result = await supervisor.start_session(
        session_id="test-session-123",
        encounter_id="test-encounter-456",
        transcription_id="test-transcription-789",
        audio_config={
            "sample_rate": 16000,
            "channels": 1,
            "format": "pcm16"
        },
        user_id="test-user"
    )
    
    print(f"\nSession started: {session_result}")
    
    if session_result["status"] != "success":
        print("Failed to start session")
        return
        
    session_id = "test-session-123"
    
    # Simulate streaming audio chunks
    print("\nStreaming audio chunks...")
    
    for i, chunk_text in enumerate(SIMULATED_TRANSCRIPT_CHUNKS):
        # Simulate audio chunk
        audio_data = simulate_audio_chunk(chunk_text)
        
        # Process chunk
        result = await supervisor.process_audio_chunk(
            session_id=session_id,
            audio_data=audio_data,
            duration_ms=1000,  # 1 second per chunk
            sequence_number=i
        )
        
        print(f"\nChunk {i+1}/{len(SIMULATED_TRANSCRIPT_CHUNKS)}: {chunk_text[:50]}...")
        
        # Simulate real-time delay between chunks
        await asyncio.sleep(0.5)
        
        # Every 10 chunks, check status
        if (i + 1) % 10 == 0:
            status = await supervisor.get_session_status(session_id)
            print(f"\nSession status after {i+1} chunks:")
            print(f"  - Chunks received: {status['audio_chunks_received']}")
            print(f"  - Total duration: {status['total_duration_ms']}ms")
            print(f"  - Transcript length: {status['transcript_length']} chars")
            print(f"  - Clinical sections: {status['clinical_sections_identified']}")
            
            # Trigger clinical analysis
            await supervisor.trigger_clinical_analysis(session_id)
            
    # Get current transcript
    print("\n" + "="*50)
    print("Getting current transcript...")
    transcript_result = await supervisor.get_current_transcript(session_id)
    
    if transcript_result.get("current_transcript"):
        print("\nCURRENT TRANSCRIPT:")
        print("-"*30)
        print(transcript_result["current_transcript"])
        
    if transcript_result.get("clinical_sections"):
        print("\nCLINICAL SECTIONS:")
        print("-"*30)
        for section, content in transcript_result["clinical_sections"].items():
            print(f"\n{section.upper()}:")
            print(str(content)[:200] + "..." if len(str(content)) > 200 else str(content))
            
    # End session
    print("\n" + "="*50)
    print("Ending session...")
    
    end_result = await supervisor.end_session(session_id)
    
    if end_result["status"] == "success":
        print("\nSESSION COMPLETED SUCCESSFULLY!")
        print(f"Duration: {end_result['duration_seconds']:.1f} seconds")
        print(f"Chunks processed: {end_result['audio_chunks_processed']}")
        print(f"Total audio duration: {end_result['total_audio_duration_ms']}ms")
        
        if end_result.get("clinical_note"):
            print("\nFINAL CLINICAL NOTE:")
            print("-"*30)
            print(end_result["clinical_note"])
            
    # Shutdown
    await supervisor.shutdown()
    print("\nTest completed.")


# Override the transcription for testing (simulate Whisper API)
async def mock_streaming_transcribe(self, audio_file_path: str):
    """Mock transcription for testing"""
    # In real use, this would call the actual Whisper API
    # For testing, we'll return the simulated text
    
    # Read the "audio" (which is actually base64 encoded text for testing)
    with open(audio_file_path, 'rb') as f:
        data = f.read()
        
    # Decode to get the original text
    try:
        text = base64.b64decode(data).decode()
    except:
        # If it's actual audio, just return placeholder
        text = "[Audio transcription would appear here]"
        
    return text


# Monkey patch for testing
import app.agents.streaming_transcription_agent
app.agents.streaming_transcription_agent.StreamingTranscriptionAgent._transcribe_audio = mock_streaming_transcribe


if __name__ == "__main__":
    # Check if OpenAI API key is set
    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in environment")
        print("Please set it in your .env file or environment variables")
        exit(1)
        
    asyncio.run(test_streaming_transcription())