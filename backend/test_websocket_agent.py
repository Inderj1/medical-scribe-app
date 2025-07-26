"""Test WebSocket agent connection"""
import asyncio
import websockets
import json
import base64
import numpy as np
from datetime import datetime


async def test_websocket_connection():
    """Test the agent WebSocket endpoint"""
    
    # You'll need a valid Clerk token for this test
    # In production, get this from the Clerk SDK
    token = "YOUR_CLERK_TOKEN_HERE"
    
    uri = f"ws://localhost:8000/api/v2/ws/agent?token={token}"
    
    print(f"🔌 Connecting to WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Test 1: Start encounter
            print("\n1️⃣ Starting encounter...")
            await websocket.send(json.dumps({
                "type": "encounter:start",
                "encounter_id": "TEST_ENC_001",
                "patient_id": "TEST_PAT_001"
            }))
            
            # Wait for response
            response = await websocket.recv()
            print(f"Response: {json.loads(response)}")
            
            # Test 2: Send audio data
            print("\n2️⃣ Sending audio data...")
            # Generate fake audio data (1 second of silence at 24kHz)
            sample_rate = 24000
            duration = 0.1  # 100ms chunks
            samples = int(sample_rate * duration)
            
            # Create silent PCM16 audio
            audio_data = np.zeros(samples, dtype=np.int16)
            
            # Send a few chunks
            for i in range(5):
                await websocket.send(audio_data.tobytes())
                print(f"Sent audio chunk {i+1}")
                await asyncio.sleep(0.1)
            
            # Test 3: Change format preference
            print("\n3️⃣ Changing format preference...")
            await websocket.send(json.dumps({
                "type": "format:preference",
                "format": "bullet"
            }))
            
            # Test 4: End encounter
            print("\n4️⃣ Ending encounter...")
            await websocket.send(json.dumps({
                "type": "encounter:end"
            }))
            
            # Wait for final response
            response = await websocket.recv()
            print(f"Final response: {json.loads(response)}")
            
            print("\n✅ WebSocket test completed!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Make sure:")
        print("1. The backend is running (python -m uvicorn app.main:app --reload)")
        print("2. You have a valid Clerk authentication token")
        print("3. The WebSocket endpoint is accessible")


async def test_realtime_streaming():
    """Test real-time audio streaming"""
    
    print("\n🎤 Testing Real-time Audio Streaming")
    print("=" * 50)
    
    # This would simulate continuous audio streaming
    # In a real scenario, this would come from the browser's microphone
    
    sample_rate = 24000  # 24kHz
    chunk_duration = 0.02  # 20ms chunks for real-time
    chunk_samples = int(sample_rate * chunk_duration)
    
    print(f"Audio config:")
    print(f"- Sample rate: {sample_rate} Hz")
    print(f"- Chunk duration: {chunk_duration * 1000} ms")
    print(f"- Samples per chunk: {chunk_samples}")
    print(f"- Bytes per chunk: {chunk_samples * 2} (PCM16)")
    
    # Generate test audio pattern
    t = np.linspace(0, chunk_duration, chunk_samples)
    frequency = 440  # A4 note
    audio_chunk = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
    
    print(f"\n✅ Test audio generated: {len(audio_chunk)} samples")


if __name__ == "__main__":
    print("🧪 Medical Scribe Agent WebSocket Tests")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_realtime_streaming())
    
    # Uncomment to test actual WebSocket connection
    # Note: Requires valid authentication token
    # asyncio.run(test_websocket_connection())