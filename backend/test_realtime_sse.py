#!/usr/bin/env python3
"""Test script for real-time SSE updates during transcription processing"""

import asyncio
import uuid
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.sse_manager import sse_manager
from app.agents.context_manager import handoff_context
from app.services.agent_runner import run_agent_processing


async def monitor_sse_events(transcription_id: str):
    """Monitor SSE events for a transcription"""
    channel = f"transcription:{transcription_id}"
    print(f"\n🔔 Monitoring SSE events on channel: {channel}")
    
    events_received = []
    
    async for event in sse_manager.subscribe(channel):
        print(f"\n📨 SSE Event received at {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Type: {event['type']}")
        print(f"   Data: {event['data']}")
        
        events_received.append(event)
        
        # Break after completed event
        if event['type'] == 'completed':
            break
    
    print(f"\n✅ Total events received: {len(events_received)}")
    return events_received


async def simulate_agent_processing():
    """Simulate agent processing with section updates"""
    transcription_id = str(uuid.uuid4())
    session_id = transcription_id
    channel = f"transcription:{transcription_id}"
    
    print(f"\n🚀 Starting simulated agent processing")
    print(f"   Transcription ID: {transcription_id}")
    
    # Initialize context
    handoff_context.create_session(session_id, {
        "transcription_id": transcription_id,
        "audio_path": "/fake/path.wav",
        "patient_context": {
            "first_name": "Test",
            "last_name": "Patient",
            "mrn": "123456",
            "age": 35
        }
    })
    
    # Simulate processing steps
    await asyncio.sleep(1)
    
    # 1. Transcription complete
    print("\n📝 Simulating transcription completion...")
    handoff_context.update_context(session_id, {
        "transcript": "Patient presents with headache for 3 days. No fever. Taking ibuprofen.",
        "transcript_ready_for_sse": True
    })
    
    await asyncio.sleep(2)
    
    # 2. Clinical analysis sections
    print("\n🔬 Simulating clinical analysis...")
    handoff_context.update_context(session_id, {
        "sections_for_sse": {
            "chief_complaint": {
                "content": "Headache for 3 days",
                "confidence": 0.95
            },
            "history_present_illness": {
                "content": "Patient reports persistent headache starting 3 days ago. No associated fever or other symptoms.",
                "confidence": 0.9
            },
            "medications": {
                "content": "Ibuprofen as needed for pain",
                "confidence": 0.85
            }
        }
    })
    
    await asyncio.sleep(2)
    
    # 3. SOAP sections
    print("\n📋 Simulating SOAP note structuring...")
    existing_sections = handoff_context.get_from_context(session_id, "sections_for_sse", {})
    existing_sections.update({
        "soap_subjective": {
            "content": "Patient presents with 3-day history of headache. No fever. Taking ibuprofen PRN.",
            "confidence": 0.9
        },
        "soap_assessment": {
            "content": "Tension headache, likely stress-related",
            "confidence": 0.85
        },
        "soap_plan": {
            "content": "Continue ibuprofen PRN. Follow up if symptoms persist beyond 1 week.",
            "confidence": 0.9
        }
    })
    handoff_context.update_context(session_id, {
        "sections_for_sse": existing_sections
    })
    
    await asyncio.sleep(2)
    
    # 4. Complete
    print("\n✅ Simulating completion...")
    await sse_manager.publish(channel, {
        "type": "completed",
        "data": {
            "transcription_id": transcription_id,
            "status": "completed"
        }
    })
    
    # Cleanup
    handoff_context.delete_session(session_id)
    
    print("\n🏁 Agent processing simulation complete")


async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 Testing Real-time SSE Updates")
    print("=" * 60)
    
    # Create a test transcription ID
    test_transcription_id = str(uuid.uuid4())
    
    # Start monitoring task
    monitor_task = asyncio.create_task(
        monitor_sse_events(test_transcription_id)
    )
    
    # Give monitor time to subscribe
    await asyncio.sleep(0.5)
    
    # Run the actual agent runner monitoring
    from app.services.agent_runner import _monitor_sections_continuously
    
    # Set up test context
    handoff_context.create_session(test_transcription_id, {
        "transcription_id": test_transcription_id
    })
    
    # Create monitoring and simulation tasks
    channel = f"transcription:{test_transcription_id}"
    
    runner_monitor_task = asyncio.create_task(
        _monitor_sections_continuously(test_transcription_id, channel)
    )
    
    simulate_task = asyncio.create_task(simulate_agent_processing())
    
    # Let simulation run
    await simulate_task
    
    # Cancel monitoring
    runner_monitor_task.cancel()
    try:
        await runner_monitor_task
    except asyncio.CancelledError:
        pass
    
    # Wait for all events to be received
    events = await monitor_task
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    event_types = [e['type'] for e in events]
    print(f"\nEvent types received: {event_types}")
    
    section_events = [e for e in events if e['type'] == 'section_completed']
    print(f"\nSections completed: {len(section_events)}")
    for event in section_events:
        section = event['data'].get('section', 'unknown')
        confidence = event['data'].get('confidence', 0)
        print(f"  - {section}: {confidence:.0%} confidence")
    
    print("\n✅ Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())