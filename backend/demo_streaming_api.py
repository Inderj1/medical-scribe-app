#!/usr/bin/env python3
"""Demo script showing how to use the streaming transcription API"""
import asyncio
import aiohttp
import base64
import json
import time
from typing import Dict, Any

# API configuration
API_BASE_URL = "http://localhost:8000/api/v1/streaming"
AUTH_TOKEN = "your-auth-token-here"  # Replace with actual token


class StreamingTranscriptionClient:
    """Client for streaming transcription API"""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def start_session(self, encounter_id: str) -> Dict[str, Any]:
        """Start a new transcription session"""
        data = {
            "encounter_id": encounter_id,
            "audio_config": {
                "sample_rate": 16000,
                "channels": 1,
                "format": "pcm16"
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/session/start",
            json=data,
            headers=self.headers
        ) as response:
            return await response.json()
            
    async def send_audio_chunk(
        self, 
        session_id: str, 
        audio_data: bytes, 
        duration_ms: int,
        sequence_number: int = None
    ) -> Dict[str, Any]:
        """Send an audio chunk"""
        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode()
        
        data = {
            "session_id": session_id,
            "audio_data": audio_base64,
            "duration_ms": duration_ms
        }
        
        if sequence_number is not None:
            data["sequence_number"] = sequence_number
            
        async with self.session.post(
            f"{self.base_url}/session/audio-chunk",
            json=data,
            headers=self.headers
        ) as response:
            return await response.json()
            
    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status"""
        async with self.session.get(
            f"{self.base_url}/session/{session_id}/status",
            headers=self.headers
        ) as response:
            return await response.json()
            
    async def get_transcript(self, session_id: str) -> Dict[str, Any]:
        """Get current transcript"""
        async with self.session.get(
            f"{self.base_url}/session/{session_id}/transcript",
            headers=self.headers
        ) as response:
            return await response.json()
            
    async def trigger_analysis(self, session_id: str) -> Dict[str, Any]:
        """Trigger clinical analysis"""
        async with self.session.post(
            f"{self.base_url}/session/{session_id}/clinical-update",
            headers=self.headers
        ) as response:
            return await response.json()
            
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End transcription session"""
        data = {"session_id": session_id}
        
        async with self.session.post(
            f"{self.base_url}/session/end",
            json=data,
            headers=self.headers
        ) as response:
            return await response.json()


def simulate_audio_chunk(text: str, duration_ms: int = 1000) -> bytes:
    """Simulate an audio chunk (for demo purposes)"""
    # In a real application, this would be actual PCM audio data
    # For demo, we'll just use the text as a placeholder
    return text.encode()


async def demo_streaming_session():
    """Demonstrate a streaming transcription session"""
    print("=== Streaming Transcription API Demo ===\n")
    
    # Note: In a real scenario, you'd get the auth token from your authentication flow
    # and the encounter_id from your application context
    
    async with StreamingTranscriptionClient(API_BASE_URL, AUTH_TOKEN) as client:
        # 1. Start a session
        print("1. Starting transcription session...")
        try:
            start_response = await client.start_session("demo-encounter-123")
            session_id = start_response["session_id"]
            print(f"   ✓ Session started: {session_id}\n")
        except Exception as e:
            print(f"   ✗ Error starting session: {e}")
            print("\nMake sure the API server is running:")
            print("   cd backend && ./run.sh")
            return
            
        # 2. Simulate streaming audio chunks
        print("2. Streaming audio chunks...")
        
        # Simulate a medical conversation
        conversation_parts = [
            "Doctor: Good afternoon, Mrs. Johnson. How are you feeling today?",
            "Patient: Not great, doctor. I've been having this persistent cough for about two weeks now.",
            "Doctor: I see. Can you describe the cough? Is it dry or are you bringing up any phlegm?",
            "Patient: It's mostly dry, but sometimes in the morning there's a bit of yellow phlegm.",
            "Doctor: Any fever or shortness of breath?",
            "Patient: I had a low-grade fever last week, around 99.5, but it's gone now. I do get winded going up stairs.",
            "Doctor: Are you currently taking any medications?",
            "Patient: Just my usual lisinopril for blood pressure, 10mg daily.",
            "Doctor: Let me listen to your lungs. *examining* I hear some crackles in your lower right lung.",
            "Doctor: Your vital signs show blood pressure 128/82, heart rate 78, temperature 98.6, oxygen saturation 96%.",
            "Doctor: Based on your symptoms and exam, I think you may have a mild bronchitis.",
            "Doctor: I'm going to prescribe azithromycin 250mg, take two tablets on day one, then one tablet daily for four days.",
            "Doctor: Also, I recommend using a humidifier and getting plenty of rest. Come back if symptoms worsen."
        ]
        
        for i, text in enumerate(conversation_parts):
            # Simulate audio chunk
            audio_data = simulate_audio_chunk(text, 2000)  # 2 seconds per chunk
            
            try:
                chunk_response = await client.send_audio_chunk(
                    session_id=session_id,
                    audio_data=audio_data,
                    duration_ms=2000,
                    sequence_number=i
                )
                print(f"   ✓ Chunk {i+1}/{len(conversation_parts)} sent")
                
                # Simulate real-time delay
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   ✗ Error sending chunk {i+1}: {e}")
                
        print()
        
        # 3. Check status periodically
        print("3. Checking session status...")
        try:
            status = await client.get_status(session_id)
            print(f"   - Status: {status['status']}")
            print(f"   - Chunks received: {status['audio_chunks_received']}")
            print(f"   - Duration: {status['duration_seconds']:.1f} seconds")
            print(f"   - Transcript length: {status['transcript_length']} chars\n")
        except Exception as e:
            print(f"   ✗ Error getting status: {e}\n")
            
        # 4. Trigger clinical analysis
        print("4. Triggering clinical analysis...")
        try:
            analysis_response = await client.trigger_analysis(session_id)
            print(f"   ✓ {analysis_response['message']}\n")
            
            # Wait for processing
            await asyncio.sleep(2)
        except Exception as e:
            print(f"   ✗ Error triggering analysis: {e}\n")
            
        # 5. Get current transcript
        print("5. Getting current transcript...")
        try:
            transcript_response = await client.get_transcript(session_id)
            
            if transcript_response.get("current_transcript"):
                print("   Current Transcript:")
                print("   " + "-" * 50)
                transcript = transcript_response["current_transcript"]
                # Show first 300 chars
                preview = transcript[:300] + "..." if len(transcript) > 300 else transcript
                print(f"   {preview}")
                print("   " + "-" * 50)
                
            if transcript_response.get("clinical_sections"):
                print("\n   Clinical Sections Identified:")
                for section, content in transcript_response["clinical_sections"].items():
                    print(f"   - {section}")
                    
            print()
        except Exception as e:
            print(f"   ✗ Error getting transcript: {e}\n")
            
        # 6. End session
        print("6. Ending session...")
        try:
            end_response = await client.end_session(session_id)
            print(f"   ✓ {end_response['message']}")
            
            # In a real app, you might want to retrieve and save the final clinical note
            print("\n   Session completed successfully!")
            
        except Exception as e:
            print(f"   ✗ Error ending session: {e}")
            
    print("\n=== Demo Complete ===")


async def demo_audio_config():
    """Demonstrate getting audio configuration"""
    print("\n=== Audio Configuration ===")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/audio-config") as response:
                config = await response.json()
                
                print("Recommended audio settings:")
                print(f"  - Sample rate: {config['sample_rate']} Hz")
                print(f"  - Channels: {config['channels']} (mono)")
                print(f"  - Format: {config['format']}")
                print(f"  - Chunk duration: {config['chunk_duration_ms']} ms")
                print(f"  - Min chunk size: {config['min_chunk_size_bytes']} bytes")
                print(f"  - Max chunk size: {config['max_chunk_size_bytes']} bytes")
                
        except Exception as e:
            print(f"Error getting audio config: {e}")


if __name__ == "__main__":
    print("Medical Scribe Streaming API Demo\n")
    
    # Run the demos
    asyncio.run(demo_streaming_session())
    asyncio.run(demo_audio_config())
    
    print("\nNote: This demo uses simulated audio data.")
    print("In a real application, you would:")
    print("1. Capture audio from the microphone")
    print("2. Convert to PCM16 format at 16kHz")
    print("3. Send chunks as they're captured")
    print("4. Handle the transcript and clinical notes in your UI"
    
    print("\nFor a complete example with real audio, see the frontend implementation.")