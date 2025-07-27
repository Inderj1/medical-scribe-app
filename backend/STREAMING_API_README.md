# Streaming Transcription API

This document describes the streaming transcription system that processes audio in real-time using OpenAI's Whisper API without WebSockets.

## Overview

The streaming transcription system allows clients to:
1. Start a transcription session
2. Send audio chunks via REST API calls
3. Get progressive transcription results
4. Receive structured clinical notes

## Architecture

### Key Components

1. **StreamingTranscriptionAgent**: Manages audio buffering and Whisper API calls
2. **AudioBuffer**: Intelligently buffers audio chunks (5-30 seconds)
3. **ClinicalContextAgent**: Extracts medical entities from transcripts
4. **NoteStructuringAgent**: Formats content into clinical sections
5. **StreamingMedicalScribeSupervisor**: Orchestrates the entire pipeline

### How It Works

```
Client → API → AudioBuffer → Whisper API → Clinical Analysis → Structured Note
         ↑                                                              ↓
         └──────────────── Progressive Updates ←───────────────────────┘
```

## API Endpoints

### 1. Start Session
```http
POST /api/v1/streaming/session/start
Content-Type: application/json
Authorization: Bearer <token>

{
  "encounter_id": "encounter-123",
  "audio_config": {
    "sample_rate": 16000,
    "channels": 1,
    "format": "pcm16"
  }
}

Response:
{
  "session_id": "uuid",
  "status": "active",
  "message": "Transcription session started successfully"
}
```

### 2. Send Audio Chunk
```http
POST /api/v1/streaming/session/audio-chunk
Content-Type: application/json
Authorization: Bearer <token>

{
  "session_id": "uuid",
  "audio_data": "base64_encoded_audio",
  "duration_ms": 1000,
  "sequence_number": 1  // optional
}

Response:
{
  "status": "success",
  "chunks_received": 5,
  "total_duration_ms": 5000,
  "current_transcript_preview": "Doctor: Good morning..."
}
```

### 3. Get Session Status
```http
GET /api/v1/streaming/session/{session_id}/status
Authorization: Bearer <token>

Response:
{
  "session_id": "uuid",
  "status": "active",
  "duration_seconds": 120,
  "audio_chunks_received": 60,
  "total_duration_ms": 120000,
  "transcript_length": 1500,
  "clinical_sections_identified": ["chief_complaint", "medications"]
}
```

### 4. Get Current Transcript
```http
GET /api/v1/streaming/session/{session_id}/transcript
Authorization: Bearer <token>

Response:
{
  "session_id": "uuid",
  "current_transcript": "Full transcript text...",
  "clinical_sections": {
    "chief_complaint": "Chest pain",
    "medications": "Aspirin 81mg daily",
    "vital_signs": "BP 120/80, HR 72"
  },
  "transcript_length": 1500
}
```

### 5. Trigger Clinical Analysis
```http
POST /api/v1/streaming/session/{session_id}/clinical-update
Authorization: Bearer <token>

Response:
{
  "status": "success",
  "message": "Clinical analysis triggered"
}
```

### 6. End Session
```http
POST /api/v1/streaming/session/end
Content-Type: application/json
Authorization: Bearer <token>

{
  "session_id": "uuid"
}

Response:
{
  "session_id": "uuid",
  "status": "completed",
  "message": "Session ended successfully"
}
```

## Audio Requirements

### Recommended Audio Format
- **Sample Rate**: 16000 Hz (16 kHz)
- **Channels**: 1 (Mono)
- **Bit Depth**: 16-bit
- **Format**: PCM16 (raw PCM data)
- **Chunk Duration**: 1-2 seconds
- **Chunk Size**: 32KB - 320KB

### Audio Encoding
Audio data must be base64 encoded before sending:
```javascript
const audioBuffer = new Int16Array(pcmData);
const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioBuffer.buffer)));
```

## Buffering Strategy

The system intelligently buffers audio to optimize Whisper API calls:

1. **Minimum Buffer**: 5 seconds - Ensures accurate transcription
2. **Maximum Buffer**: 30 seconds - Prevents memory issues
3. **Time-based Trigger**: 10 seconds since last transcription
4. **Context Preservation**: Uses previous text as prompt for consistency

## Clinical Processing

### Automatic Extraction
- Chief Complaint
- History of Present Illness
- Medications (with dosages)
- Vital Signs
- Physical Examination findings
- Assessment and Plan

### Quality Metrics
- Completeness score
- Confidence scores per section
- Abnormal vital sign detection
- Missing required sections alerts

## Client Implementation Example

### JavaScript/TypeScript
```typescript
class StreamingClient {
  private sessionId: string;
  private audioContext: AudioContext;
  private mediaRecorder: MediaRecorder;
  
  async startRecording(encounterId: string) {
    // Start session
    const response = await fetch('/api/v1/streaming/session/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        encounter_id: encounterId,
        audio_config: {
          sample_rate: 16000,
          channels: 1,
          format: 'pcm16'
        }
      })
    });
    
    const data = await response.json();
    this.sessionId = data.session_id;
    
    // Start audio capture
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.setupAudioProcessing(stream);
  }
  
  private setupAudioProcessing(stream: MediaStream) {
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(stream);
    const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (e) => {
      const pcmData = this.convertToPCM16(e.inputBuffer);
      this.sendAudioChunk(pcmData);
    };
    
    source.connect(processor);
    processor.connect(this.audioContext.destination);
  }
  
  private async sendAudioChunk(pcmData: ArrayBuffer) {
    const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcmData)));
    
    await fetch('/api/v1/streaming/session/audio-chunk', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        session_id: this.sessionId,
        audio_data: base64Audio,
        duration_ms: (pcmData.byteLength / 32) // 16kHz, 16-bit mono
      })
    });
  }
}
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_streaming_agents.py -v
python -m pytest tests/test_streaming_supervisor.py -v
```

### Integration Tests
```bash
python -m pytest tests/test_streaming_integration.py -v
```

### API Tests
```bash
python -m pytest tests/test_streaming_api.py -v
```

### Run All Tests
```bash
./run_streaming_tests.py
```

## Performance Considerations

1. **Latency**: ~2-5 seconds from speech to transcription
2. **Accuracy**: Improves with longer audio segments
3. **Concurrent Sessions**: Limited by OpenAI API rate limits
4. **Memory Usage**: ~50MB per active session

## Error Handling

The system handles:
- Invalid audio data
- Network interruptions
- API rate limits
- Session timeouts (30 minutes)
- Concurrent session limits

## Security

1. **Authentication**: Bearer token required
2. **Session Validation**: User can only access their own sessions
3. **Data Encryption**: HTTPS for all API calls
4. **Session Cleanup**: Automatic after 30 minutes of inactivity

## Limitations

1. **Audio Format**: Must be PCM16 at specified sample rate
2. **Language**: Currently English only
3. **Max Session Duration**: Recommended < 1 hour
4. **Concurrent Sessions**: Based on OpenAI API limits

## Future Enhancements

1. Support for multiple languages
2. Real-time speaker diarization
3. Custom medical vocabulary
4. Offline transcription fallback
5. Audio compression support