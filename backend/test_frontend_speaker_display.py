#!/usr/bin/env python3
"""
Frontend Speaker Display Test

This script simulates WebSocket messages with speaker information
to test the frontend's ability to display multi-speaker transcriptions.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrontendSpeakerTest:
    """Test frontend speaker display functionality"""
    
    def __init__(self):
        self.ws_url = "ws://localhost:8000/api/v2/ws/agent"
        self.test_token = "test_token_123"  # Replace with actual token
        
    async def send_speaker_messages(self, websocket):
        """Send test messages with speaker information"""
        
        # Test conversation with multiple speakers
        test_messages = [
            {
                "type": "transcription:partial",
                "text": "Good morning, Mrs. Johnson. How are you feeling today?",
                "speaker_id": "SPEAKER_01",
                "speaker_role": "healthcare_provider",
                "speaker_count": 1,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:complete",
                "text": "Good morning, Mrs. Johnson. How are you feeling today?",
                "speaker_id": "SPEAKER_01",
                "speaker_role": "healthcare_provider",
                "speaker_count": 1,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:partial",
                "text": "I'm doing much better, doctor. The pain in my knee has reduced significantly.",
                "speaker_id": "SPEAKER_02",
                "speaker_role": "patient",
                "speaker_count": 2,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:complete",
                "text": "I'm doing much better, doctor. The pain in my knee has reduced significantly.",
                "speaker_id": "SPEAKER_02",
                "speaker_role": "patient",
                "speaker_count": 2,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:partial",
                "text": "Here are the vital signs. Blood pressure is 120 over 80.",
                "speaker_id": "SPEAKER_03",
                "speaker_role": "nurse",
                "speaker_count": 3,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:complete",
                "text": "Here are the vital signs. Blood pressure is 120 over 80, temperature is 98.6.",
                "speaker_id": "SPEAKER_03",
                "speaker_role": "nurse",
                "speaker_count": 3,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:partial",
                "text": "Excellent. Let's continue with the treatment plan.",
                "speaker_id": "SPEAKER_01",
                "speaker_role": "healthcare_provider",
                "speaker_count": 3,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "type": "transcription:complete",
                "text": "Excellent. Let's continue with the treatment plan we discussed.",
                "speaker_id": "SPEAKER_01",
                "speaker_role": "healthcare_provider", 
                "speaker_count": 3,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        logger.info("Sending test messages with speaker information...")
        
        for i, message in enumerate(test_messages):
            logger.info(f"Sending message {i+1}/{len(test_messages)}: {message['type']} from {message['speaker_id']} ({message.get('speaker_role', 'unknown')})")
            
            await websocket.send(json.dumps(message))
            
            # Delay between messages to simulate real conversation
            if message["type"] == "partial":
                await asyncio.sleep(0.5)  # Short delay for partial
            else:
                await asyncio.sleep(2.0)  # Longer delay after complete
        
        logger.info("All test messages sent!")
    
    async def test_frontend_display(self):
        """Test the frontend's ability to display speaker information"""
        
        logger.info("Frontend Speaker Display Test")
        logger.info("=" * 50)
        logger.info("This test will send WebSocket messages with speaker information.")
        logger.info("Please ensure:")
        logger.info("1. The backend is running (./run.sh --backend-only)")
        logger.info("2. The frontend is running (./run.sh --frontend-only)")
        logger.info("3. You have the RealtimeTranscription component open in your browser")
        logger.info("4. You've started a recording session")
        logger.info("=" * 50)
        
        input("Press Enter when ready to start the test...")
        
        try:
            # Connect to WebSocket
            ws_url_with_token = f"{self.ws_url}?token={self.test_token}"
            
            async with websockets.connect(ws_url_with_token) as websocket:
                logger.info("Connected to WebSocket")
                
                # Send test messages
                await self.send_speaker_messages(websocket)
                
                logger.info("\nTest completed!")
                logger.info("Check your browser to verify:")
                logger.info("1. Each speaker has a different colored label")
                logger.info("2. Speaker roles are displayed correctly (Provider, Patient, Nurse)")
                logger.info("3. Speaker count shows '3 speakers'")
                logger.info("4. Transcription segments are properly separated by speaker")
                
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            logger.error("Make sure the backend is running and accessible")


async def main():
    """Run the frontend test"""
    tester = FrontendSpeakerTest()
    await tester.test_frontend_display()


if __name__ == "__main__":
    print("\n🔍 Frontend Speaker Display Test")
    print("This test requires manual verification in the browser.")
    print("Make sure both backend and frontend are running.\n")
    
    asyncio.run(main())