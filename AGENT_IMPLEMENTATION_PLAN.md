# Agent-Based Real-Time Transcription Implementation Plan

## Overview
Transform the medical scribe application to use OpenAI's Realtime API with an agent-based architecture for continuous, low-latency transcription without chunking.

## Key Changes from Current Architecture
- **Remove 3-second buffering** - Process audio in real-time as it streams
- **Replace chunk-based processing** with continuous WebSocket streaming
- **Use OpenAI Realtime API** instead of batch Whisper API calls
- **Implement agent handoff** pattern for modular processing
- **Enable simultaneous processing** without waiting for chunks

## Agent Architecture

### 1. **Realtime Transcription Agent**
- Maintains persistent WebSocket connection to OpenAI Realtime API
- Handles bidirectional audio streaming
- Manages session lifecycle and interruptions
- Outputs continuous transcription stream

### 2. **Audio Stream Agent**
- Manages browser WebRTC/WebSocket connection
- Handles audio format conversion if needed
- Implements backpressure and flow control
- Monitors audio quality metrics

### 3. **Clinical Context Agent**
- Processes transcription output in real-time
- Maintains medical context and terminology
- Identifies medical entities as they appear
- Handles context switching for different encounter types

### 4. **Note Structuring Agent**
- Routes transcribed content to appropriate sections
- Maintains note structure and formatting
- Handles real-time updates to clinical documentation
- Manages format preferences (long/short/bullet)

### 5. **Supervisor Agent**
- Orchestrates agent handoffs
- Manages error recovery and fallbacks
- Monitors system performance
- Handles session state management

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. Set up OpenAI Realtime API connection
2. Implement WebSocket infrastructure for continuous streaming
3. Create base agent framework
4. Remove chunking/buffering logic

### Phase 2: Agent Development (Week 2)
1. Build Realtime Transcription Agent
2. Implement Audio Stream Agent
3. Create agent handoff mechanism
4. Add error handling and recovery

### Phase 3: Clinical Features (Week 3)
1. Develop Clinical Context Agent
2. Build Note Structuring Agent
3. Implement medical terminology enhancement
4. Add section routing logic

### Phase 4: Integration & Testing (Week 4)
1. Update frontend for continuous streaming
2. Implement performance monitoring
3. Add comprehensive testing
4. Deploy and iterate

## Technical Implementation Details

### Backend Changes

#### 1. Replace Enhanced WebSocket Handler
```python
# New: Realtime streaming handler
class RealtimeTranscriptionHandler:
    def __init__(self):
        self.openai_ws = None  # WebSocket to OpenAI Realtime API
        self.client_ws = None  # WebSocket to browser
        self.session_id = None
        
    async def handle_audio_stream(self, audio_data: bytes):
        # Direct streaming to OpenAI without buffering
        await self.openai_ws.send(audio_data)
```

#### 2. Agent Implementation Pattern
```python
from swarm import Swarm, Agent

class TranscriptionAgent(Agent):
    def __init__(self):
        super().__init__(
            name="TranscriptionAgent",
            instructions="Handle real-time audio transcription"
        )
        
    async def process_audio(self, audio_stream):
        # Connect to OpenAI Realtime API
        # Stream audio directly
        # Emit transcription events
```

### Frontend Changes

#### 1. Continuous Audio Streaming
```typescript
// Replace chunk-based recording with continuous stream
class RealtimeAudioStreamer {
    private mediaStream: MediaStream;
    private audioContext: AudioContext;
    private processor: ScriptProcessorNode;
    
    async startStreaming() {
        // Get continuous audio stream
        // Send raw PCM data via WebSocket
        // No buffering or chunking
    }
}
```

#### 2. Real-time UI Updates
```typescript
// Update transcription display in real-time
const LiveTranscription = () => {
    const [transcription, setTranscription] = useState('');
    
    useEffect(() => {
        ws.on('transcription:partial', (data) => {
            // Update UI immediately with partial results
            setTranscription(prev => prev + data.text);
        });
    }, []);
};
```

## Configuration Updates

### Environment Variables
```env
# OpenAI Realtime API
OPENAI_REALTIME_API_KEY=<key>
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
ENABLE_INPUT_TRANSCRIPTION=true
ENABLE_FUNCTION_CALLING=true

# Audio Settings
AUDIO_SAMPLE_RATE=24000  # 24kHz for Realtime API
AUDIO_CHANNELS=1
AUDIO_FORMAT=pcm16
```

### Dependencies
```python
# requirements.txt additions
openai>=1.12.0  # Latest with Realtime API support
swarm-sdk>=0.1.0  # Agent orchestration
websockets>=12.0
aiortc>=1.6.0  # WebRTC support
```

## Performance Targets
- **Latency**: < 300ms end-to-end
- **Transcription accuracy**: > 95% for medical terms
- **Concurrent sessions**: Unlimited (per OpenAI's 2025 update)
- **Audio quality**: 24kHz, 16-bit PCM
- **Network resilience**: Auto-reconnect within 2s

## Testing Strategy
1. **Unit tests** for each agent
2. **Integration tests** for agent handoffs
3. **Load testing** for concurrent sessions
4. **Medical accuracy testing** with sample consultations
5. **Network resilience testing** with connection drops

## Monitoring & Observability
- Real-time latency metrics
- Transcription confidence scores
- Agent performance tracking
- WebSocket connection health
- Audio quality metrics

## Rollback Plan
- Feature flag for agent-based system
- Maintain existing chunked system in parallel
- Gradual rollout by user/organization
- Quick switch back if issues detected