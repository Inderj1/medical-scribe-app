"""Test script for batch agent system"""
import asyncio
import os
import tempfile
from pathlib import Path

# Add the app directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.batch_medical_scribe_supervisor import BatchMedicalScribeSupervisor
from app.core.config import settings

# Sample audio text for testing (we'll create a simple test case)
TEST_TRANSCRIPTION = """
Doctor: Good morning, Mrs. Johnson. What brings you in today?

Patient: I've been having chest pain for the past three days. It started suddenly when I was walking up the stairs.

Doctor: Can you describe the pain for me?

Patient: It's a sharp pain, right in the center of my chest. It gets worse when I take a deep breath or move around.

Doctor: I see. On a scale of 1 to 10, how would you rate the pain?

Patient: It's about a 7 when it's at its worst, maybe a 4 right now.

Doctor: Any other symptoms? Shortness of breath, nausea, sweating?

Patient: Yes, I've been a bit short of breath, especially when the pain is bad. No nausea though.

Doctor: Are you currently taking any medications?

Patient: I take metformin 500 mg twice daily for my diabetes, and lisinopril 10 mg once daily for blood pressure.

Doctor: Any drug allergies?

Patient: I'm allergic to penicillin - I get a rash.

Doctor: Let me check your vital signs. Your blood pressure is 145/90, heart rate is 88, temperature is 98.6, and oxygen saturation is 97%.

Doctor: I'm going to do a physical exam now. I hear some mild wheezing in your left lung base. Your heart sounds are regular without murmurs.

Doctor: Based on your symptoms and examination, I'm concerned about possible pleuritis or costochondritis. We'll need to do a chest X-ray and an EKG to rule out any cardiac issues. I'm going to prescribe ibuprofen 600 mg three times daily for the pain and inflammation. 

Doctor: Please follow up in one week, or sooner if the pain worsens or you develop new symptoms. Any questions?

Patient: No, that makes sense. Thank you, doctor.
"""


async def create_test_audio_file():
    """Create a test audio file (we'll simulate with a text file for testing)"""
    # In a real scenario, this would be an actual audio file
    # For testing, we'll create a temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(TEST_TRANSCRIPTION)
        return f.name


async def test_batch_processing():
    """Test the batch processing system"""
    print("Starting batch agent system test...")
    
    # Initialize supervisor
    supervisor = BatchMedicalScribeSupervisor()
    
    # Give the system a moment to initialize
    await asyncio.sleep(1)
    
    # Create test audio file
    test_file = await create_test_audio_file()
    print(f"Created test file: {test_file}")
    
    try:
        # Start processing
        result = await supervisor.process_audio_file(
            audio_file_path=test_file,
            encounter_id="test-encounter-123",
            options={"format_preference": "soap"}
        )
        
        print(f"\nProcessing started: {result}")
        transcription_id = result["transcription_id"]
        
        # Poll for status
        print("\nPolling for status...")
        completed = False
        
        for i in range(30):  # Poll for up to 30 seconds
            await asyncio.sleep(1)
            status = await supervisor.get_transcription_status(transcription_id)
            
            print(f"Status update {i+1}: {status['status']} - {status['current_stage']} ({status['progress']}%)")
            
            if status['status'] == 'completed':
                completed = True
                break
            elif status['status'] == 'error':
                print(f"Error occurred: {status['errors']}")
                break
                
        if completed:
            # Get final result
            final_result = await supervisor.get_completed_transcription(transcription_id)
            
            print("\n" + "="*50)
            print("TRANSCRIPTION COMPLETED SUCCESSFULLY!")
            print("="*50)
            
            if "results" in final_result:
                results = final_result["results"]
                
                # Print transcription
                if "text" in results:
                    print("\nTRANSCRIPTION:")
                    print("-"*30)
                    print(results["text"][:500] + "..." if len(results["text"]) > 500 else results["text"])
                    
                # Print clinical sections
                if "clinical_sections" in results:
                    print("\nCLINICAL SECTIONS IDENTIFIED:")
                    print("-"*30)
                    for section, content in results["clinical_sections"].items():
                        if content:
                            print(f"\n{section.upper()}:")
                            if isinstance(content, dict) and "formatted" in content:
                                print(content["formatted"])
                            else:
                                print(str(content)[:200] + "..." if len(str(content)) > 200 else str(content))
                            
                # Print formatted note
                if "formatted_note" in results:
                    print("\nFORMATTED CLINICAL NOTE:")
                    print("-"*30)
                    print(results["formatted_note"])
                    
                # Print quality metrics
                if "quality_metrics" in results:
                    print("\nQUALITY METRICS:")
                    print("-"*30)
                    metrics = results["quality_metrics"]
                    print(f"Completeness: {metrics.get('completeness_score', 0)*100:.1f}%")
                    print(f"Quality Grade: {metrics.get('quality_grade', 'N/A')}")
                    print(f"Word Count: {metrics.get('word_count', 0)}")
                    
        else:
            print("\nTranscription did not complete in time")
            
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)
            
        # Shutdown supervisor
        await supervisor.shutdown()
        print("\nTest completed.")


# Override the transcription agent to handle text files for testing
async def mock_transcribe_audio(audio_file_path: str):
    """Mock transcription for testing with text files"""
    if audio_file_path.endswith('.txt'):
        with open(audio_file_path, 'r') as f:
            text = f.read()
        return {
            "text": text,
            "language": "en",
            "duration": 180,  # 3 minutes
            "segments": []
        }
    else:
        # Would call real Whisper API here
        raise NotImplementedError("Real audio transcription not implemented in test")


# Monkey patch for testing
import app.agents.batch_transcription_agent
app.agents.batch_transcription_agent.BatchTranscriptionAgent._transcribe_audio = mock_transcribe_audio


if __name__ == "__main__":
    # Check if OpenAI API key is set
    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in environment")
        print("Please set it in your .env file or environment variables")
        exit(1)
        
    asyncio.run(test_batch_processing())