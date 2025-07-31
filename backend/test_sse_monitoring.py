#!/usr/bin/env python3
"""Test SSE monitoring to see what events are being sent"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def monitor_sse():
    """Monitor SSE events for a transcription"""
    
    # Use a known transcription ID from the logs
    transcription_id = "2719d986-1b05-48ae-b979-0463f5781468"
    
    # Token from browser (using the same one)
    token = "eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18yenJ3S1ZSZk9GMnN0Q1RQOTA1UURBWXhQSGQiLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwOi8vbG9jYWxob3N0OjMxMDAiLCJleHAiOjE3NTM5MzE2OTEsImZ2YSI6WzU2LC0xXSwiaWF0IjoxNzUzOTMxNjMxLCJpc3MiOiJodHRwczovL2V4Y2l0aW5nLXNhbG1vbi02Ny5jbGVyay5hY2NvdW50cy5kZXYiLCJuYmYiOjE3NTM5MzE2MjEsInNpZCI6InNlc3NfMzBjWUk1VHFzMzBYeFNvamRZS2FXaDd1a0RDIiwic3ViIjoidXNlcl8zMDIxdG5WS3RSNXZXdXVkekRWcTJGa3YwelEifQ.QgBr1gCgTOIMthZVBUEiZts6Pl8vA5U9z8F6lqKMJ8HyzqewWNagTwCdxX4qjuQqTiDWIKfuQz9M__LFs3kCGIAQIvcnZoHdfm9I5I9fwfYmGXXXpyDQ-20G9z3pDcUtCrrhxdCDdkeZ18RcHqsgZMKW57liuGC8wuSNyA4Se03hbq6itrJ9xfYUurHJHmotCqVGjq-EuDdLFm-9AngiO4gfJpDgHBLJ20IAfALaLMaz2XcCYNiiPJHshjGhNYWTVX4o5UjrEht80RpFgWKOMl80dx3GStb756t6DxZo-kZ7EZRBRP5V0Zp50DEeDbXpouRDb8tx2UGF8fmf4LmxRQ"
    
    url = f"http://localhost:8000/api/v1/sse/transcription/{transcription_id}?token={token}"
    
    print(f"[{datetime.now()}] Connecting to SSE endpoint...")
    print(f"URL: {url[:100]}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                print(f"[{datetime.now()}] Connected! Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                async for line in response.content:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line:
                        print(f"\n[{datetime.now()}] Raw SSE data: {decoded_line}")
                        
                        # Parse SSE format
                        if decoded_line.startswith('event:'):
                            event_type = decoded_line[6:].strip()
                            print(f"  Event Type: {event_type}")
                        elif decoded_line.startswith('data:'):
                            data_str = decoded_line[5:].strip()
                            try:
                                data = json.loads(data_str)
                                print(f"  Data: {json.dumps(data, indent=2)}")
                            except:
                                print(f"  Raw Data: {data_str}")
                        elif decoded_line.startswith('id:'):
                            event_id = decoded_line[3:].strip()
                            print(f"  Event ID: {event_id}")
                        elif decoded_line.startswith('retry:'):
                            retry = decoded_line[6:].strip()
                            print(f"  Retry: {retry}")
                            
        except Exception as e:
            print(f"\n[{datetime.now()}] Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("SSE Event Monitor")
    print("=================")
    asyncio.run(monitor_sse())