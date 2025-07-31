#!/usr/bin/env python3
"""Test the streaming API fix"""

import asyncio
import aiohttp
import json
import uuid
from datetime import datetime

async def test_streaming():
    # Test data
    session_data = {
        "encounter_id": f"temp-{uuid.uuid4()}",
        "format_preference": "soap",
        "provider_name": "Dr. Smith",
        "location": "Medical Office",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "patient_mrn": "TEST-MRN-123",
        "patient_gender": "male",
        "ehr_sections": {
            "chief_complaint": "Chest pain and shortness of breath",
            "allergies": "Penicillin",
            "past_medical_history": "Hypertension, Type 2 Diabetes",
            "review_of_systems": "Positive for chest pain, shortness of breath",
            "physical_examination": "BP 150/90, HR 88, RR 20"
        }
    }
    
    # Test user credentials (OAuth2PasswordRequestForm format)
    auth_data = {
        "username": "demo@example.com",
        "password": "DemoPassword123!"
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. Login to get token
        print("\n1. Logging in...")
        async with session.post(
            "http://localhost:8000/api/v1/auth/login",
            data=auth_data
        ) as resp:
            if resp.status != 200:
                print(f"Login failed: {resp.status}")
                text = await resp.text()
                print(text)
                return
            
            login_data = await resp.json()
            token = login_data["access_token"]
            print(f"✓ Logged in successfully")
        
        # 2. Start streaming session
        print("\n2. Starting streaming session...")
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.post(
            "http://localhost:8000/api/v1/streaming/start",
            json=session_data,
            headers=headers
        ) as resp:
            if resp.status != 200:
                print(f"Failed to start streaming: {resp.status}")
                text = await resp.text()
                print(text)
                return
            
            result = await resp.json()
            session_id = result["session_id"]
            print(f"✓ Session started: {session_id}")
            print(f"  SSE endpoint: {result['sse_endpoint']}")
        
        # 3. Stream some text
        print("\n3. Streaming text chunks...")
        text_chunks = [
            "Patient presents with chest pain that started yesterday. ",
            "The pain is described as pressure-like, ",
            "radiating to the left arm. ",
            "Associated with shortness of breath and diaphoresis. ",
            "No fever or cough. Patient has history of hypertension. ",
            "Currently taking lisinopril 10mg daily. ",
            "Blood pressure today is 150/90. ",
            "EKG shows normal sinus rhythm. "
        ]
        
        for i, chunk in enumerate(text_chunks):
            async with session.post(
                f"http://localhost:8000/api/v1/streaming/{session_id}/text",
                json={
                    "text": chunk,
                    "is_final": i == len(text_chunks) - 1,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers=headers
            ) as resp:
                if resp.status == 200:
                    print(f"  ✓ Sent chunk {i+1}/{len(text_chunks)}")
                else:
                    print(f"  ✗ Failed chunk {i+1}: {resp.status}")
            
            await asyncio.sleep(0.5)
        
        # 4. End session
        print("\n4. Ending session...")
        async with session.post(
            f"http://localhost:8000/api/v1/streaming/{session_id}/end",
            headers=headers
        ) as resp:
            if resp.status == 200:
                print("✓ Session ended successfully")
            else:
                print(f"✗ Failed to end session: {resp.status}")
        
        # 5. Monitor SSE events
        print("\n5. Monitoring SSE events...")
        print(f"   Connect to: http://localhost:8000/api/v1/sse/transcription/{session_id}")
        print("   (Would normally use SSE client here)")
        
        # 6. Check transcription status
        print("\n6. Checking transcription status...")
        await asyncio.sleep(2)  # Give agents time to process
        
        async with session.get(
            f"http://localhost:8000/api/v1/transcription/{session_id}/status",
            headers=headers
        ) as resp:
            if resp.status == 200:
                status_data = await resp.json()
                print(f"✓ Status: {status_data.get('status', 'unknown')}")
                print(f"  Progress: {status_data.get('progress', 0)}%")
            else:
                print(f"✗ Failed to get status: {resp.status}")

if __name__ == "__main__":
    print("Testing Streaming API Fix...")
    print("============================")
    asyncio.run(test_streaming())