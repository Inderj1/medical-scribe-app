#!/usr/bin/env python3
"""Monitor SSE events in real-time"""

import asyncio
import sys
import os
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.sse_manager import sse_manager


async def monitor_all_events():
    """Monitor all SSE events across all channels"""
    print("🔍 Monitoring SSE Events (Press Ctrl+C to stop)")
    print("=" * 80)
    
    # Monkey patch to intercept all publishes
    original_publish = sse_manager.publish
    
    async def intercepted_publish(channel, event):
        print(f"\n📨 [{datetime.now().strftime('%H:%M:%S')}] Channel: {channel}")
        print(f"   Type: {event.get('type', 'unknown')}")
        if 'data' in event:
            data = event['data']
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'content' and isinstance(value, str) and len(value) > 100:
                        print(f"   {key}: {value[:100]}...")
                    else:
                        print(f"   {key}: {value}")
            else:
                print(f"   data: {data}")
        print("-" * 80)
        
        # Call original publish
        return await original_publish(channel, event)
    
    sse_manager.publish = intercepted_publish
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")
    finally:
        # Restore original method
        sse_manager.publish = original_publish


async def main():
    print("=" * 80)
    print("🚀 SSE Event Monitor")
    print("=" * 80)
    print("\nThis will show all SSE events being published in real-time.")
    print("Start a transcription in another terminal to see events.\n")
    
    await monitor_all_events()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")