# Speaker Diarization Usage Guide

## Current Limitations with Browser-Based Recording

The multi-speaker system is implemented and working, but **browser-based Web Speech API does not support speaker diarization**. When using the browser's microphone:

- All speech is attributed to a single speaker (SPEAKER_01)
- The browser cannot distinguish between different speakers
- This is a fundamental limitation of the Web Speech API

## When Speaker Diarization Works

Speaker diarization is fully functional in these scenarios:

### 1. Audio File Upload
When users upload pre-recorded audio files:
- The system processes the audio server-side
- pyannote.audio identifies different speakers
- Each speaker gets a unique ID (SPEAKER_01, SPEAKER_02, etc.)
- Speaker roles are identified based on conversation content

### 2. Direct API Integration
When using the API directly with audio streams:
```python
# Example: Sending audio with speaker info
response = requests.post(
    f"{API_URL}/api/v1/streaming/{session_id}/audio",
    data=audio_data,
    headers={"speaker-id": "SPEAKER_02"}
)
```

### 3. Multi-Channel Audio
When recording with multiple microphones:
- Each microphone can be assigned to a speaker
- Requires custom audio capture implementation
- Not supported by standard Web Speech API

## How to Test Speaker Diarization

### Option 1: Upload Audio File
1. Record a conversation with multiple speakers
2. Save as WAV or MP3
3. Upload through the file upload API
4. System will identify and separate speakers

### Option 2: Simulate Multiple Speakers
Use the test script to simulate multi-speaker conversation:
```bash
cd backend
source venv/bin/activate
python test_frontend_speaker_display.py
```

### Option 3: Manual Speaker Assignment
For browser-based recording, you could add UI controls to:
1. Let users manually switch speakers
2. Add a "Speaker" dropdown next to the microphone
3. Tag segments with speaker identity

## Implementation for Manual Speaker Selection

To add manual speaker selection to the frontend:

```typescript
// Add speaker state
const [currentSpeaker, setCurrentSpeaker] = useState('SPEAKER_01');

// Add speaker selector UI
<Select value={currentSpeaker} onChange={(e) => setCurrentSpeaker(e.target.value)}>
  <MenuItem value="SPEAKER_01">Healthcare Provider</MenuItem>
  <MenuItem value="SPEAKER_02">Patient</MenuItem>
  <MenuItem value="SPEAKER_03">Nurse</MenuItem>
</Select>

// Update text sending
body: JSON.stringify({
  text,
  is_final: isFinal,
  timestamp: new Date().toISOString(),
  speaker_id: currentSpeaker, // Use selected speaker
})
```

## Future Enhancements

1. **WebRTC Multi-User Sessions**: Each participant joins with their own microphone
2. **Voice Fingerprinting**: Train the system to recognize specific voices
3. **Automatic Speaker Change Detection**: Use acoustic features to detect when speaker changes (partially implemented but needs audio access)
4. **Mobile App Integration**: Native apps can access multiple audio sources

## Current Working Features

Even with single-speaker browser recording, the system still:
- Tracks all text with speaker attribution
- Identifies speaker roles based on content
- Displays speaker information in the UI
- Stores speaker data in the database
- Includes speaker info in clinical notes

The infrastructure is ready - it just needs multi-source audio input to fully utilize the speaker diarization capabilities.