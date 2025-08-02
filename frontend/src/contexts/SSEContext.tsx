import React, { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';

interface SSEContextType {
  subscribeToTranscription: (transcriptionId: string) => void;
  unsubscribeFromTranscription: (transcriptionId: string) => void;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastEvent: any;
}

const SSEContext = createContext<SSEContextType | undefined>(undefined);

export const useSSE = () => {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSE must be used within an SSEProvider');
  }
  return context;
};

interface SSEProviderProps {
  children: React.ReactNode;
}

export const SSEProvider: React.FC<SSEProviderProps> = ({ children }) => {
  const { getToken } = useAuth();
  const eventSourceRef = useRef<EventSource | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastEvent, setLastEvent] = useState<any>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const subscribeToTranscription = useCallback(async (transcriptionId: string) => {
    console.log('[SSE] Starting subscription for transcription:', transcriptionId);
    try {
      // Close existing connection if any
      if (eventSourceRef.current) {
        console.log('[SSE] Closing existing connection');
        eventSourceRef.current.close();
      }

      // Get auth token
      const token = await getToken();
      if (!token) {
        console.error('[SSE] No auth token available');
        setConnectionStatus('error');
        return;
      }

      // Create EventSource with token as query parameter
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/v1/sse/transcription/${transcriptionId}?token=${encodeURIComponent(token)}`;
      
      console.log('[SSE] Creating EventSource with URL:', url);
      setConnectionStatus('connecting');
      
      // Create EventSource with withCredentials for CORS
      const eventSource = new EventSource(url, {
        withCredentials: false  // Set to false for cross-origin requests without cookies
      });
      eventSourceRef.current = eventSource;
      
      // Add readyState logging
      console.log('[SSE] EventSource readyState after creation:', eventSource.readyState);

      eventSource.onopen = () => {
        console.log('[SSE] Connection established successfully');
        setConnectionStatus('connected');
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      eventSource.onerror = (error) => {
        console.error('[SSE] Connection error:', {
          error,
          readyState: eventSource.readyState,
          timestamp: new Date().toISOString()
        });
        setConnectionStatus('error');
        eventSource.close();
        
        // Attempt to reconnect after 5 seconds
        if (!reconnectTimeoutRef.current) {
          console.log('[SSE] Scheduling reconnection in 5 seconds');
          reconnectTimeoutRef.current = setTimeout(() => {
            subscribeToTranscription(transcriptionId);
          }, 5000);
        }
      };

      // Handle specific event types
      eventSource.addEventListener('connected', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Connected event received:', data);
      });

      eventSource.addEventListener('processing_started', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Processing started event:', data);
        setLastEvent({ type: 'processing_started', data });
      });

      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Progress event:', data);
        setLastEvent({ type: 'progress', data });
      });

      eventSource.addEventListener('transcription_chunk', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Transcription chunk event:', data);
        setLastEvent({ type: 'transcription_chunk', data });
      });

      eventSource.addEventListener('section_completed', (event) => {
        console.log('[SSE] Raw section_completed event:', event);
        try {
          const data = JSON.parse(event.data);
          console.log('[SSE] Section completed event:', {
            section: data.section,
            contentLength: data.content?.length,
            confidence: data.confidence
          });
          setLastEvent({ type: 'section_completed', data });
        } catch (e) {
          console.error('[SSE] Error parsing section_completed event:', e, event.data);
        }
      });
      
      // Add a generic message handler to catch any events
      eventSource.onmessage = (event) => {
        console.log('[SSE] Generic message received:', event);
        try {
          const data = JSON.parse(event.data);
          console.log('[SSE] Parsed generic message:', data);
        } catch (e) {
          console.log('[SSE] Raw message:', event.data);
        }
      };

      eventSource.addEventListener('completed', (event) => {
        const data = JSON.parse(event.data);
        console.log('[SSE] Completed event:', data);
        setLastEvent({ type: 'completed', data });
        eventSource.close();
        setConnectionStatus('disconnected');
      });

      // Error events from the server (not connection errors)
      eventSource.addEventListener('error', (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data);
          console.error('[SSE] Server error event:', data);
          setLastEvent({ type: 'error', data });
        } catch (e) {
          console.error('[SSE] Error parsing server error event:', e);
          setLastEvent({ type: 'error', data: { error: 'Server error' } });
        }
      });

      eventSource.addEventListener('heartbeat', (event) => {
        // Keep connection alive
        console.debug('[SSE] Heartbeat received');
      });

      console.log('[SSE] EventSource created successfully');
      
    } catch (error) {
      console.error('[SSE] Failed to subscribe to transcription:', error);
      setConnectionStatus('error');
    }
  }, [getToken]);

  const unsubscribeFromTranscription = useCallback((transcriptionId: string) => {
    console.log('[SSE] Unsubscribing from transcription:', transcriptionId);
    if (eventSourceRef.current) {
      console.log('[SSE] Closing EventSource connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnectionStatus('disconnected');
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const value: SSEContextType = {
    subscribeToTranscription,
    unsubscribeFromTranscription,
    connectionStatus,
    lastEvent,
  };

  return <SSEContext.Provider value={value}>{children}</SSEContext.Provider>;
};