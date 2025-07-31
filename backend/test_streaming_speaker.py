#!/usr/bin/env python3
"""Test streaming API with speaker support"""
import asyncio
import aiohttp
import json
import time
import os
from datetime import datetime
import uuid

# API configuration
API_URL = "http://localhost:8000"
AUTH_TOKEN = None  # Will be obtained via login

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test123"


async def login():
    """Login and get auth token"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/api/v1/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD}  # Form data, not JSON
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["access_token"]
            else:
                print(f"Login failed: {response.status}")
                text = await response.text()
                print(f"Error: {text}")
                return None


async def create_streaming_session(token: str):
    """Create a new streaming session"""
    headers = {"Authorization": f"Bearer {token}"}
    
    session_data = {
        "encounter_id": f"temp-{uuid.uuid4()}",
        "format_preference": "soap",
        "enable_speaker_diarization": True,
        "patient_mrn": f"TEST-{int(time.time())}",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "patient_gender": "male",
        "provider_name": "Dr. Test",
        "location": "Test Clinic",
        "ehr_sections": {
            "chief_complaint": "Follow-up for multiple speakers test"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/api/v1/streaming/start",
            json=session_data,
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["session_id"]
            else:
                print(f"Failed to create session: {response.status}")
                text = await response.text()
                print(f"Error: {text}")
                return None


async def send_text_chunks(token: str, session_id: str):
    """Send text chunks with different speakers"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Simulate conversation with multiple speakers
    chunks = [
        # Doctor speaking
        {"text": "Good morning Mr. Doe, how are you feeling today?", "speaker_id": "SPEAKER_00"},
        {"text": "I see you're here for a follow-up appointment.", "speaker_id": "SPEAKER_00"},
        
        # Patient speaking
        {"text": "Hi doctor, I'm doing better than last week.", "speaker_id": "SPEAKER_01"},
        {"text": "The medication seems to be helping with the pain.", "speaker_id": "SPEAKER_01"},
        
        # Doctor again
        {"text": "That's great to hear. Can you describe the pain level on a scale of 1 to 10?", "speaker_id": "SPEAKER_00"},
        
        # Patient
        {"text": "It was about an 8 last week, but now it's down to about a 3 or 4.", "speaker_id": "SPEAKER_01"},
        {"text": "I can sleep through the night now without waking up.", "speaker_id": "SPEAKER_01"},
        
        # Nurse joins
        {"text": "Excuse me doctor, here are the patient's vitals from today.", "speaker_id": "SPEAKER_02"},
        {"text": "Blood pressure is 120 over 80, temperature is 98.6.", "speaker_id": "SPEAKER_02"},
        
        # Doctor
        {"text": "Thank you. Mr. Doe, your vitals look good.", "speaker_id": "SPEAKER_00"},
        {"text": "Let's continue with the current medication for another month.", "speaker_id": "SPEAKER_00"},
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, chunk in enumerate(chunks):
            # Send chunk
            data = {
                "text": chunk["text"],
                "speaker_id": chunk["speaker_id"],
                "is_final": i == len(chunks) - 1
            }
            
            async with session.post(
                f"{API_URL}/api/v1/streaming/{session_id}/text",
                json=data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[{chunk['speaker_id']}] Sent: {chunk['text'][:50]}...")
                    print(f"  Response: {result}")
                else:
                    print(f"Failed to send chunk: {response.status}")
                    text = await response.text()
                    print(f"Error: {text}")
            
            # Small delay between chunks
            await asyncio.sleep(0.5)


async def end_streaming_session(token: str, session_id: str):
    """End the streaming session"""
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/api/v1/streaming/{session_id}/end",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"\nSession ended: {data}")
                return True
            else:
                print(f"Failed to end session: {response.status}")
                text = await response.text()
                print(f"Error: {text}")
                return False


async def get_transcription_status(token: str, session_id: str):
    """Check transcription status"""
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/api/v1/transcription/{session_id}/status",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                return None


async def main():
    """Main test function"""
    print("Testing Streaming API with Speaker Support")
    print("=========================================")
    
    # Login
    print("\n1. Logging in...")
    token = await login()
    if not token:
        print("Failed to login")
        return
    print(f"Got token: {token[:20]}...")
    
    # Create session
    print("\n2. Creating streaming session...")
    session_id = await create_streaming_session(token)
    if not session_id:
        print("Failed to create session")
        return
    print(f"Session ID: {session_id}")
    
    # Send chunks
    print("\n3. Sending text chunks with multiple speakers...")
    await send_text_chunks(token, session_id)
    
    # End session
    print("\n4. Ending streaming session...")
    await end_streaming_session(token, session_id)
    
    # Wait a bit for processing
    print("\n5. Waiting for processing...")
    await asyncio.sleep(5)
    
    # Check status
    print("\n6. Checking final status...")
    status = await get_transcription_status(token, session_id)
    if status:
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress']}%")
        if 'speaker_count' in status:
            print(f"Speaker count: {status['speaker_count']}")
        if 'sections' in status:
            print(f"Sections completed: {', '.join(status['sections'])}")


if __name__ == "__main__":
    asyncio.run(main())