# Audio Streaming Implementation Plan: Web Speech API to OpenAI Whisper

## Executive Summary

This document outlines the plan to replace the current Web Speech API implementation with direct audio streaming to OpenAI's Whisper API. This change is necessary to enable speaker diarization and improve transcription accuracy for medical documentation.

## Current State Analysis

### What We Have Now
1. **Frontend Speech Recognition**
   - Using Web Speech API (`useWebSpeech` hook)
   - Browser-based speech recognition
   - Text-only output sent to backend
   - No audio data preserved

2. **Backend Text Processing**
   - Receives text via `/streaming/{session_id}/text` endpoint
   - Processes text through agents for medical documentation
   - No access to original audio
   - No speaker identification capability

### Problems with Current Approach

1. **No Speaker Diarization**
   - Web Speech API doesn't identify speakers
   - Critical for medical encounters (doctor vs patient)
   - Cannot distinguish between multiple speakers
   - Lost context about who said what

2. **Limited Accuracy**
   - Browser speech recognition varies by browser
   - No medical vocabulary optimization
   - No ability to improve transcription quality
   - Cannot reprocess audio if needed

3. **No Audio Record**
   - Original audio is not preserved
   - Cannot verify transcriptions
   - No audit trail for medical records
   - Cannot retranscribe with improved models

4. **Browser Limitations**
   - Dependent on browser implementation
   - Inconsistent across different browsers
   - Limited control over recognition parameters
   - No access to confidence scores

## Proposed Solution

### Architecture Overview

```
┌─────────────┐     Audio Chunks      ┌─────────────┐     OpenAI      ┌─────────────┐
│   Frontend  │ ──────────────────►   │   Backend   │ ────────────►  │   Whisper   │
│ MediaRecorder│    HTTP POST         │  Audio API  │                 │     API     │
└─────────────┘                       └─────────────┘                 └─────────────┘
      │                                      │                               │
      │                                      │◄──────────────────────────────┘
      │                                      │    Transcription + Speakers
      │◄─────────────────────────────────────┘
           Display with Speaker Labels
```

### Implementation Details

#### 1. Frontend Audio Capture
- Use MediaRecorder API for audio capture
- Record in 3-5 second chunks for real-time processing
- Send audio data via HTTP POST (not WebSocket)
- Maintain simple request/response pattern

#### 2. Backend Audio Processing
- New endpoint: `POST /streaming/{session_id}/audio`
- Accept audio chunks as base64 or multipart/form-data
- Forward to OpenAI Whisper API with diarization enabled
- Return transcribed text with speaker identification

#### 3. Speaker Diarization
- OpenAI Whisper can identify different speakers
- Label speakers as SPEAKER_01, SPEAKER_02, etc.
- Backend can map to roles (Doctor, Patient, Nurse)
- Preserve speaker information throughout processing

## Benefits of This Approach

### 1. Medical Context Preservation
- Know who said what (doctor vs patient)
- Better clinical documentation
- Accurate attribution of symptoms, instructions
- Legal compliance for medical records

### 2. Improved Accuracy
- OpenAI Whisper trained on diverse data
- Better medical terminology recognition
- Consistent transcription quality
- Can be improved over time

### 3. Audio Preservation
- Store original audio chunks
- Enable quality assurance reviews
- Retranscribe with improved models
- Audit trail for compliance

### 4. Scalability
- Process audio on powerful servers
- Not limited by client device capabilities
- Can handle multiple concurrent sessions
- Better resource utilization

## Technical Implementation Steps

### Phase 1: Audio Capture (Frontend)
```typescript
// New hook: useAudioStream.ts
- Initialize MediaRecorder with audio constraints
- Capture audio in chunks (3-5 seconds)
- Convert to suitable format for upload
- Handle recording state management
```

### Phase 2: Audio Upload (Frontend → Backend)
```typescript
// HTTP POST with audio data
POST /api/v1/streaming/{session_id}/audio
Content-Type: multipart/form-data
Body: audio_chunk (blob/base64)
```

### Phase 3: Audio Processing (Backend)
```python
# New endpoint in streaming_v2.py
@router.post("/{session_id}/audio")
async def process_audio_chunk():
    # Receive audio data
    # Send to OpenAI Whisper
    # Return transcription with speakers
```

### Phase 4: Display Results (Frontend)
```typescript
// Update UI components
- Show speaker labels
- Color-code by speaker
- Display confidence scores
- Real-time updates
```

## Migration Strategy

1. **Parallel Implementation**
   - Keep existing Web Speech API code
   - Add new audio streaming alongside
   - Feature flag to switch between them

2. **Testing Phase**
   - Test with small group of users
   - Compare accuracy between methods
   - Validate speaker diarization

3. **Gradual Rollout**
   - Enable for new sessions first
   - Migrate existing users gradually
   - Monitor performance and feedback

4. **Deprecation**
   - Remove Web Speech API code
   - Clean up unused dependencies
   - Update documentation

## Considerations

### Performance
- Audio chunks: 3-5 seconds optimal
- Compression: Use opus/webm for smaller size
- Latency: Expect 1-2 second delay
- Bandwidth: ~16KB/s for audio

### Privacy & Security
- Audio data encrypted in transit
- Temporary storage only
- HIPAA compliance considerations
- User consent for audio recording

### Error Handling
- Network interruption recovery
- Chunk reupload on failure
- Graceful degradation
- User feedback on issues

### Cost
- OpenAI Whisper API pricing
- Storage for audio chunks
- Increased bandwidth usage
- Server processing resources

## Success Metrics

1. **Accuracy**
   - Transcription accuracy > 95%
   - Speaker identification accuracy > 90%
   - Medical term recognition improved

2. **Performance**
   - Latency < 2 seconds per chunk
   - 99% uptime for service
   - Support 100+ concurrent sessions

3. **User Satisfaction**
   - Positive feedback on speaker labels
   - Reduced manual corrections
   - Improved clinical documentation

## Timeline

- Week 1: Implement audio capture frontend
- Week 2: Create backend audio processing
- Week 3: Integrate OpenAI Whisper API
- Week 4: Testing and refinement
- Week 5: Gradual rollout
- Week 6: Full deployment

## Conclusion

Replacing Web Speech API with OpenAI Whisper audio streaming will significantly improve the medical scribe application by enabling speaker diarization, improving accuracy, and providing better clinical documentation. The implementation uses simple HTTP chunking without WebSockets, making it easier to maintain and scale.