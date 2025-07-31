#!/usr/bin/env python3
"""Simple test to check streaming API"""

import requests
from app.core.security import create_access_token
from datetime import timedelta

# Generate a token directly
token = create_access_token(
    data={"sub": "demo@example.com"},
    expires_delta=timedelta(hours=24)
)

print(f"Token: {token[:20]}...")

# Test streaming start
headers = {"Authorization": f"Bearer {token}"}
session_data = {
    "encounter_id": "temp-test-123",
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
        "past_medical_history": "Hypertension, Type 2 Diabetes"
    }
}

print("\nTesting streaming start...")
try:
    response = requests.post(
        "http://localhost:8000/api/v1/streaming/start",
        json=session_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success! Session ID: {result['session_id']}")
        print(f"  SSE endpoint: {result['sse_endpoint']}")
    else:
        print(f"✗ Error: {response.text}")
        
except Exception as e:
    print(f"✗ Failed: {e}")