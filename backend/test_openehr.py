#!/usr/bin/env python3
"""Test script for OpenEHR integration"""

import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def test_openehr():
    async with httpx.AsyncClient() as client:
        # 1. Register a test user
        print("1. Registering test user...")
        register_response = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "username": "test_doctor",
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test Doctor",
                "role": "physician",
                "license_number": "12345",
                "specialty": "General Practice"
            }
        )
        
        if register_response.status_code == 200:
            print("✓ User registered successfully")
        elif register_response.status_code == 400:
            print("! User already exists, continuing...")
        else:
            print(f"✗ Registration failed: {register_response.text}")
            return
        
        # 2. Login to get access token
        print("\n2. Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/api/auth/token",
            data={
                "username": "test_doctor",
                "password": "testpassword123"
            }
        )
        
        if login_response.status_code != 200:
            print(f"✗ Login failed: {login_response.text}")
            return
        
        token = login_response.json()["access_token"]
        print("✓ Login successful")
        
        # Set authorization header
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Test OpenEHR connection
        print("\n3. Testing OpenEHR connection...")
        test_response = await client.get(
            f"{BASE_URL}/api/openehr/test",
            headers=headers
        )
        
        if test_response.status_code == 200:
            print("✓ OpenEHR connection test passed")
            print(f"   Response: {json.dumps(test_response.json(), indent=2)}")
        else:
            print(f"✗ OpenEHR test failed: {test_response.text}")
        
        # 4. Create a test composition
        print("\n4. Creating test composition...")
        composition_data = {
            "patient_id": "test-patient-123",
            "encounter_id": "test-encounter-456",
            "clinical_notes": {
                "chief_complaint": {"text": "Patient presents with headache"},
                "history_of_present_illness": {"text": "Headache started 2 days ago, moderate severity"},
                "assessment": {"text": "Tension headache"},
                "plan": {"text": "Rest and OTC pain medication"}
            },
            "vitals": {
                "blood_pressure": "120/80",
                "heart_rate": 72,
                "temperature": 98.6
            }
        }
        
        create_response = await client.post(
            f"{BASE_URL}/api/openehr/compositions",
            json=composition_data,
            headers=headers
        )
        
        if create_response.status_code == 200:
            print("✓ Composition created successfully")
            print(f"   Response: {json.dumps(create_response.json(), indent=2)}")
        else:
            print(f"✗ Composition creation failed: {create_response.text}")
        
        # 5. Get patient compositions
        print("\n5. Getting patient compositions...")
        get_response = await client.get(
            f"{BASE_URL}/api/openehr/compositions/test-patient-123",
            headers=headers
        )
        
        if get_response.status_code == 200:
            print("✓ Retrieved patient compositions")
            print(f"   Response: {json.dumps(get_response.json(), indent=2)}")
        else:
            print(f"✗ Failed to get compositions: {get_response.text}")


if __name__ == "__main__":
    print("OpenEHR Integration Test")
    print("=" * 50)
    asyncio.run(test_openehr())