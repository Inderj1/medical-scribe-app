#!/usr/bin/env python3
"""
Live test script to verify the agent-based system is working
Run this after the services are up and running
"""

import asyncio
import json
import websocket
import base64
import time
from datetime import datetime

# Configuration
WS_URL = "ws://localhost:8000/ws/enhanced-audio-stream"
TEST_TOKEN = "test-token"  # You'll need to get a valid token

class AgentSystemTester:
    def __init__(self):
        self.ws = None
        self.responses = []
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received: {data['type']}")
            
            if data['type'] == 'clinical_notes:prefill':
                print("✓ EHR data prefilled successfully")
                print(f"  Sections: {list(data['data']['sections'].keys())}")
                
            elif data['type'] == 'speaker:identified':
                print(f"✓ Speaker identified: {data['speaker']} (confidence: {data['confidence']:.2f})")
                
            elif data['type'] == 'section:update':
                print(f"✓ Section updated: {data['section']}")
                print(f"  Content preview: {data['content'][:100]}...")
                
            self.responses.append(data)
            
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
    
    def on_open(self, ws):
        print("WebSocket connection opened")
        
        # Start clinical notes
        self.send_message({
            "type": "clinical_notes:start",
            "patient_id": "test-patient-001",
            "encounter_type": "routine_visit"
        })
        
        # Simulate some transcriptions after a delay
        asyncio.create_task(self.simulate_conversation())
    
    def send_message(self, message):
        """Send a message through WebSocket"""
        self.ws.send(json.dumps(message))
        print(f"Sent: {message['type']}")
    
    async def simulate_conversation(self):
        """Simulate a doctor-patient conversation"""
        await asyncio.sleep(2)  # Wait for initialization
        
        conversations = [
            ("Good morning, what brings you in today?", "doctor"),
            ("I've been having severe headaches for about a week now", "patient"),
            ("Can you describe the headaches? Where do you feel the pain?", "doctor"),
            ("It's mostly on the right side of my head, throbbing pain", "patient"),
            ("Are you currently taking any medications?", "doctor"),
            ("Yes, I take lisinopril for blood pressure and metformin for diabetes", "patient"),
            ("Let me check your vital signs", "doctor"),
            ("Blood pressure is 138 over 85, slightly elevated", "doctor"),
            ("I think we should start you on a migraine medication", "doctor")
        ]
        
        print("\n--- Starting conversation simulation ---")
        
        for text, speaker in conversations:
            print(f"\n[{speaker.upper()}]: {text}")
            
            # Create mock transcription result
            self.send_message({
                "type": "transcription",
                "audio": base64.b64encode(b"mock_audio").decode(),
                "id": f"trans-{int(time.time())}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Wait between messages
            await asyncio.sleep(3)
        
        print("\n--- Conversation simulation complete ---")
        
        # Close connection after simulation
        await asyncio.sleep(5)
        self.ws.close()
    
    def run_test(self, token):
        """Run the test"""
        print(f"Connecting to {WS_URL}")
        
        self.ws = websocket.WebSocketApp(
            f"{WS_URL}?token={token}",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run in a separate thread
        import threading
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
        
        # Keep main thread alive
        try:
            while wst.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nTest interrupted")
            self.ws.close()

def test_individual_components():
    """Test individual components directly"""
    print("\n=== Testing Individual Components ===\n")
    
    import sys
    import os
    sys.path.insert(0, os.path.abspath('.'))
    
    try:
        # Test 1: Speaker Diarization
        print("1. Testing Speaker Diarization Agent...")
        from app.services.speaker_diarization_agent import SpeakerDiarizationAgent
        
        agent = SpeakerDiarizationAgent()
        test_phrases = [
            "Let me examine your throat",
            "I've been coughing for days",
            "The medication is working"
        ]
        
        for phrase in test_phrases:
            result = asyncio.run(agent.identify_speaker(phrase))
            print(f"   '{phrase}' -> {result.speaker} ({result.confidence:.2f})")
        
        print("   ✓ Speaker diarization working\n")
        
    except Exception as e:
        print(f"   ✗ Speaker diarization error: {e}\n")
    
    try:
        # Test 2: Section Agents
        print("2. Testing Section Agents...")
        from app.services.openai_section_agents import OpenAISectionAgents
        
        agents = OpenAISectionAgents()
        result = asyncio.run(agents.process_section(
            "chief_complaint",
            "Patient reports severe headache",
            "PATIENT",
            "short"
        ))
        
        print(f"   Section: {result.section}")
        print(f"   Content: {result.content[:80]}...")
        print(f"   Formats: {list(result.formatted_content.keys())}")
        print("   ✓ Section agents working\n")
        
    except Exception as e:
        print(f"   ✗ Section agents error: {e}\n")
    
    try:
        # Test 3: Context Manager
        print("3. Testing Context Manager...")
        from app.services.context_manager import ContextManager
        
        manager = ContextManager()
        manager.add_to_context(
            "test-enc", 
            "Headache", 
            {"speaker": "PATIENT", "confidence": 0.9}
        )
        summary = manager.get_conversation_summary("test-enc")
        
        print(f"   Total utterances: {summary['total_utterances']}")
        print(f"   Speakers: {dict(summary['speaker_counts'])}")
        print(f"   Sections: {list(manager.contexts.get('test-enc', {}).keys())}")
        print("   ✓ Context manager working\n")
        
    except Exception as e:
        print(f"   ✗ Context manager error: {e}\n")

def main():
    """Main test function"""
    print("=== Agent-Based Medical Scribe System Live Test ===")
    print(f"Started at: {datetime.now()}\n")
    
    # Test individual components first
    test_individual_components()
    
    # Then test WebSocket integration
    print("\n=== Testing WebSocket Integration ===\n")
    print("Note: You need a valid authentication token for WebSocket test")
    print("You can get one by logging into the application first\n")
    
    # Uncomment and add valid token to test WebSocket
    # tester = AgentSystemTester()
    # tester.run_test("your-valid-token-here")
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()