#!/usr/bin/env python3
"""Test authentication and streaming endpoint"""

import requests
import json
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User


def test_direct_api_call():
    """Test direct API call without auth"""
    print("\n1. Testing direct API call without auth:")
    print("-" * 40)
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/streaming/start",
            json={
                "encounter_id": "1",
                "format_preference": "soap"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


def test_with_fake_token():
    """Test with a fake Bearer token"""
    print("\n2. Testing with fake Bearer token:")
    print("-" * 40)
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/streaming/start",
            headers={
                "Authorization": "Bearer fake-token-123"
            },
            json={
                "encounter_id": "1",
                "format_preference": "soap"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


def check_users_in_db():
    """Check if there are any users in the database"""
    print("\n3. Checking users in database:")
    print("-" * 40)
    
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users in database")
        for user in users[:5]:  # Show first 5
            print(f"  - {user.email} (ID: {user.id}, Active: {user.is_active})")
    finally:
        db.close()


def test_health_endpoint():
    """Test health endpoint to verify API is running"""
    print("\n4. Testing health endpoint:")
    print("-" * 40)
    
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Testing Authentication and API Endpoints")
    print("=" * 60)
    
    test_health_endpoint()
    test_direct_api_call()
    test_with_fake_token()
    check_users_in_db()
    
    print("\n" + "=" * 60)
    print("✅ Test complete")
    print("=" * 60)