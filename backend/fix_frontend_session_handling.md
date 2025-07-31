# Frontend Session Handling Fix

## Issues Identified

1. **409 Conflict Error**: The frontend is trying to end streaming sessions multiple times
   - Called on silence timeout
   - Called on speech end
   - Called in cleanup effect
   - No state tracking to prevent duplicate calls

2. **Speech Recognition Issues**: Browser intermittently reports speech recognition as not supported

3. **404 Error for EHRBase**: Assessment section not found (this is expected if no data exists)

## Recommended Fixes

### 1. Fix Duplicate End Session Calls

Add a ref to track if session is ending:

```typescript
// Add after other refs
const isEndingSessionRef = useRef(false);

// Update handleEndSession
const handleEndSession = async () => {
  if (!currentTranscriptionId || isEndingSessionRef.current) {
    console.log('No active session to end or already ending');
    return;
  }
  
  isEndingSessionRef.current = true;
  
  try {
    const token = await (window as any).Clerk?.session?.getToken();
    const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/end`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (response.ok) {
      console.log('Session ended successfully');
      setCurrentTranscriptionId(null); // Clear the ID
    } else if (response.status === 409) {
      console.log('Session already ended');
    } else {
      console.error('Failed to end session:', response.statusText);
    }
  } catch (error) {
    console.error('Failed to end session:', error);
  } finally {
    isEndingSessionRef.current = false;
  }
};
```

### 2. Fix Speech Recognition Hook

Update the `useWebSpeech` hook to handle only one end event:

```typescript
// In useWebSpeech hook
onSilenceTimeout: async () => {
  console.log('Speech ended due to silence');
  // Don't call handleEndSession here - let onEnd handle it
},
onEnd: async () => {
  console.log('Speech recognition ended, triggering clinical analysis...');
  await handleEndSession();
},
```

### 3. Backend Session State Management

The backend should also be more defensive about session state transitions:

```python
# In end_streaming_session endpoint
if transcription.status in ["completed", "processing"]:
    # Don't raise error, just return success
    return {
        "message": f"Session already {transcription.status}",
        "session_id": session_id,
        "status": transcription.status
    }
```

### 4. Cleanup Effect Fix

Update the cleanup effect to check if already ending:

```typescript
useEffect(() => {
  return () => {
    if (isListening) {
      stopListening();
    }
    
    // End streaming session if active
    if (currentTranscriptionId && !isEndingSessionRef.current) {
      // ... existing cleanup code
    }
  };
}, [currentTranscriptionId, unsubscribeFromTranscription, isListening, stopListening]);
```

## Testing the Fix

1. Start a recording session
2. Speak and then stop
3. Verify only one end session call is made
4. Check that no 409 errors appear in console
5. Start another session to verify state is reset properly