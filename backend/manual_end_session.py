#!/usr/bin/env python3
"""Manual script to end the current streaming session"""

import httpx
import asyncio

async def end_session():
    """End the current streaming session"""
    session_id = "fb218c58-998e-44eb-92a1-c45ff2fe542f"
    token = "eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18yenJ3S1ZSZk9GMnN0Q1RQOTA1UURBWXhQSGQiLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwOi8vbG9jYWxob3N0OjMxMDAiLCJleHAiOjE3NTM5MzMzMzgsImZ2YSI6WzEyLC0xXSwiaWF0IjoxNzUzOTMzMjc4LCJpc3MiOiJodHRwczovL2V4Y2l0aW5nLXNhbG1vbi02Ny5jbGVyay5hY2NvdW50cy5kZXYiLCJuYmYiOjE3NTM5MzMyNjgsInNpZCI6InNlc3NfMzBjZ3c1M3lhRGRwN3hjdnBpS3NpZTdKc1RjIiwic3ViIjoidXNlcl8zMFJVWDEyOUcyOUlTazdaakkyUHhpc25jSHUifQ.qoUvED3ARzrrScjhEbCt5ACQvYSjBR9Lp2PgK32BTUQcKIBiA7LPbAUVPs6XX1hLXpeUj1oDkmJ8XuFwGz-I2zQuti42I1jrZAwKHkfXAoculPclUYPGLf-OhUa1dx0j-15LGvZg_rE0eBKiwwoRVFQo3HgCqSJXOaSQpmj2YpVS1-IHH1gnqBhGEIatFZJVV2ZAGBnMqVHraMhDQP-OtXPLM067SRiOzH9wlvH_TDVjyXkOvHnPVoAqGuXdBZQ6YmHUndbMYCeoeEQlGulT8bY0YYXzEW3y2VcGYSiyFxn5y8mrBvKkAkglyz66W3ontUH_AbQv2BiPJpjv0S6KjQ"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    url = f"http://localhost:8000/api/v1/streaming/{session_id}/end"
    
    print(f"Ending session {session_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        
        if response.status_code == 200:
            print("Session ended successfully!")
            print("The AI agents are now processing your transcript...")
            print("Check your browser - sections should update in 5-10 seconds")
        else:
            print(f"Failed to end session: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(end_session())