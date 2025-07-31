#!/usr/bin/env python3
"""Direct test of SSE functionality"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_sse():
    """Test SSE connection directly"""
    
    # Create a new session first
    token = "eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18yenJ3S1ZSZk9GMnN0Q1RQOTA1UURBWXhQSGQiLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwOi8vbG9jYWxob3N0OjMxMDAiLCJleHAiOjE3NTM5MzE2OTEsImZ2YSI6WzU2LC0xXSwiaWF0IjoxNzUzOTMxNjMxLCJpc3MiOiJodHRwczovL2V4Y2l0aW5nLXNhbG1vbi02Ny5jbGVyay5hY2NvdW50cy5kZXYiLCJuYmYiOjE3NTM5MzE2MjEsInNpZCI6InNlc3NfMzBjWUk1VHFzMzBYeFNvamRZS2FXaDd1a0RDIiwic3ViIjoidXNlcl8zMDIxdG5WS3RSNXZXdXVkekRWcTJGa3YwelEifQ.QgBr1gCgTOIMthZVBUEiZts6Pl8vA5U9z8F6lqKMJ8HyzqewWNagTwCdxX4qjuQqTiDWIKfuQz9M__LFs3kCGIAQIvcnZoHdfm9I5I9fwfYmGXXXpyDQ-20G9z3pDcUtCrrhxdCDdkeZ18RcHqsgZMKW57liuGC8wuSNyA4Se03hbq6itrJ9xfYUurHJHmotCqVGjq-EuDdLFm-9AngiO4gfJpDgHBLJ20IAfALaLMaz2XcCYNiiPJHshjGhNYWTVX4o5UjrEht80RpFgWKOMl80dx3GStb756t6DxZo-kZ7EZRBRP5V0Zp50DEeDbXpouRDb8tx2UGF8fmf4LmxRQ"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("1. Creating streaming session...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Start streaming session
        response = await client.post(
            "http://localhost:8000/api/v1/streaming/start",
            json={
                "encounter_id": "test-encounter",
                "format_preference": "concise",
                "enable_speaker_diarization": True
            },
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Failed to start session: {response.status_code} - {response.text}")
            return
            
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Session started: {session_id}")
        
        # Connect to SSE before sending any data
        print("\n2. Connecting to SSE...")
        sse_url = f"http://localhost:8000/api/v1/sse/transcription/{session_id}?token={token}"
        
        # Create a task to monitor SSE
        async def monitor_sse():
            async with httpx.AsyncClient(timeout=300.0) as sse_client:
                async with sse_client.stream('GET', sse_url) as sse_response:
                    print(f"SSE Connected: {sse_response.status_code}")
                    event_type = None
                    async for line in sse_response.aiter_lines():
                        if line.startswith('event:'):
                            event_type = line[6:].strip()
                        elif line.startswith('data:') and event_type:
                            try:
                                data = json.loads(line[5:])
                                print(f"\n[SSE Event] {event_type}: {json.dumps(data, indent=2)}")
                            except:
                                print(f"\n[SSE Event] {event_type}: {line[5:]}")
                            event_type = None
        
        # Start SSE monitoring in background
        sse_task = asyncio.create_task(monitor_sse())
        
        # Give SSE time to connect
        await asyncio.sleep(2)
        
        # Send some test text
        print("\n3. Sending test transcript chunks...")
        
        test_chunks = [
            "Hello doctor, I've been having headaches for the past week.",
            "They usually start in the morning and get worse throughout the day.",
            "I've been taking ibuprofen but it doesn't help much."
        ]
        
        for i, chunk in enumerate(test_chunks):
            print(f"\nSending chunk {i+1}: '{chunk}'")
            response = await client.post(
                f"http://localhost:8000/api/v1/streaming/{session_id}/text",
                json={
                    "text_chunk": chunk,
                    "is_final": i == len(test_chunks) - 1,
                    "speaker_id": "SPEAKER_01"
                },
                headers=headers
            )
            print(f"Response: {response.status_code}")
            await asyncio.sleep(1)
        
        # End session
        print("\n4. Ending session...")
        response = await client.post(
            f"http://localhost:8000/api/v1/streaming/{session_id}/end",
            headers=headers
        )
        print(f"End response: {response.status_code}")
        
        # Wait for SSE events
        print("\n5. Waiting for SSE events...")
        await asyncio.sleep(10)
        
        # Cancel SSE monitoring
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    print("SSE Direct Test")
    print("===============")
    asyncio.run(test_sse())