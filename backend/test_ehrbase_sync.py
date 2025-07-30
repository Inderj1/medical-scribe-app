#!/usr/bin/env python3
"""Test EHRBase patient sync functionality"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_direct_ehrbase():
    """Test direct EHRBase API access"""
    print("Testing direct EHRBase API...")
    
    # Test getting patients
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://3.223.44.85/api/patients")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Found {len(data) if isinstance(data, list) else 'unknown'} patients")
                if data:
                    # Show first patient
                    patient = data[0] if isinstance(data, list) else data
                    print(f"Sample patient: {json.dumps(patient, indent=2)}")
        except Exception as e:
            print(f"Error: {e}")

async def test_patient_sync():
    """Test syncing patients through our API"""
    print("\nTesting patient sync through our API...")
    
    headers = {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # First sync patients
            response = await client.post(
                "http://localhost:8000/api/v1/patients/sync",
                headers=headers
            )
            print(f"Sync status: {response.status_code}")
            if response.status_code == 200:
                print(f"Sync result: {response.json()}")
            else:
                print(f"Error: {response.text}")
            
            # Then list patients
            response = await client.get(
                "http://localhost:8000/api/v1/patients/",
                headers=headers
            )
            print(f"\nList status: {response.status_code}")
            if response.status_code == 200:
                patients = response.json()
                print(f"Found {len(patients)} patients in local database")
                for patient in patients[:3]:  # Show first 3
                    print(f"- {patient.get('first_name')} {patient.get('last_name')} (MRN: {patient.get('mrn')}, EHR ID: {patient.get('ehr_id')})")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_ehrbase())
    asyncio.run(test_patient_sync())