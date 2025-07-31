#!/usr/bin/env python3
"""Debug SSE and section updates"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.sse_manager import sse_manager
from app.agents.context_manager import handoff_context
from app.db.session import SessionLocal
from app.models.transcription import Transcription
from app.models.clinical_note import ClinicalNote


async def check_sse_subscribers():
    """Check active SSE subscribers"""
    print("\n🔔 Active SSE Subscribers:")
    print("-" * 40)
    
    # Access internal state (for debugging only)
    if hasattr(sse_manager, '_subscribers'):
        for channel, subscribers in sse_manager._subscribers.items():
            print(f"Channel: {channel}")
            print(f"  Subscribers: {len(subscribers)}")
    else:
        print("Unable to access subscriber information")


def check_recent_transcriptions():
    """Check recent transcriptions and their status"""
    print("\n📝 Recent Transcriptions:")
    print("-" * 40)
    
    db = SessionLocal()
    try:
        transcriptions = db.query(Transcription).order_by(
            Transcription.created_at.desc()
        ).limit(5).all()
        
        for t in transcriptions:
            print(f"\nID: {t.id}")
            print(f"  Status: {t.status}")
            print(f"  Progress: {t.progress}%")
            print(f"  Created: {t.created_at}")
            print(f"  Has transcript: {'Yes' if t.transcript else 'No'}")
            
            # Check for clinical note
            clinical_note = db.query(ClinicalNote).filter(
                ClinicalNote.transcription_id == t.id
            ).first()
            
            if clinical_note:
                print(f"  Clinical Note ID: {clinical_note.id}")
                sections_with_content = []
                if clinical_note.chief_complaint: sections_with_content.append("chief_complaint")
                if clinical_note.history_present_illness: sections_with_content.append("hpi")
                if clinical_note.medications: sections_with_content.append("medications")
                if clinical_note.additional_notes: sections_with_content.append("additional_notes")
                if clinical_note.care_coordination: sections_with_content.append("care_coordination")
                print(f"  Sections with content: {', '.join(sections_with_content)}")
            else:
                print("  Clinical Note: Not found")
                
    finally:
        db.close()


def check_context_sessions():
    """Check active context sessions"""
    print("\n🔧 Active Context Sessions:")
    print("-" * 40)
    
    # Check if there are any active sessions
    if hasattr(handoff_context, '_contexts'):
        for session_id, context in handoff_context._contexts.items():
            print(f"\nSession: {session_id}")
            print(f"  Keys: {list(context.keys())}")
            if 'sections_for_sse' in context:
                print(f"  SSE Sections: {list(context['sections_for_sse'].keys())}")
            if 'clinical_data' in context:
                clinical_keys = list(context['clinical_data'].keys()) if isinstance(context['clinical_data'], dict) else []
                print(f"  Clinical Data Keys: {clinical_keys}")
    else:
        print("No active sessions found")


async def test_sse_publish():
    """Test publishing an SSE event"""
    print("\n🧪 Testing SSE Publishing:")
    print("-" * 40)
    
    test_channel = "test:debug"
    
    try:
        await sse_manager.publish(test_channel, {
            "type": "test",
            "data": {
                "message": "Debug test event",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        print("✅ Successfully published test event")
    except Exception as e:
        print(f"❌ Error publishing test event: {e}")


async def main():
    print("=" * 60)
    print("🔍 SSE and Section Update Debugging")
    print("=" * 60)
    
    # Check SSE subscribers
    await check_sse_subscribers()
    
    # Check recent transcriptions
    check_recent_transcriptions()
    
    # Check context sessions
    check_context_sessions()
    
    # Test SSE publishing
    await test_sse_publish()
    
    print("\n" + "=" * 60)
    print("✅ Debug check complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())