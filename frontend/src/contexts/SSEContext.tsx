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
    try {
      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Get auth token
      const token = await getToken();
      if (!token) {
        console.error('No auth token available');
        setConnectionStatus('error');
        return;
      }

      // Create EventSource with token as query parameter
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/v1/sse/transcription/${transcriptionId}?token=${encodeURIComponent(token)}`;
      
      setConnectionStatus('connecting');
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection established');
        setConnectionStatus('connected');
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        setConnectionStatus('error');
        eventSource.close();
        
        // Attempt to reconnect after 5 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            subscribeToTranscription(transcriptionId);
          }, 5000);
        }
      };

      // Handle specific event types
      eventSource.addEventListener('connected', (event) => {
        const data = JSON.parse(event.data);
        console.log('Connected to transcription updates:', data);
      });

      eventSource.addEventListener('processing_started', (event) => {
        const data = JSON.parse(event.data);
        setLastEvent({ type: 'processing_started', data });
      });

      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        setLastEvent({ type: 'progress', data });
      });

      eventSource.addEventListener('transcription_chunk', (event) => {
        const data = JSON.parse(event.data);
        setLastEvent({ type: 'transcription_chunk', data });
      });

      eventSource.addEventListener('section_completed', (event) => {
        const data = JSON.parse(event.data);
        setLastEvent({ type: 'section_completed', data });
      });

      eventSource.addEventListener('completed', (event) => {
        const data = JSON.parse(event.data);
        setLastEvent({ type: 'completed', data });
        eventSource.close();
        setConnectionStatus('disconnected');
      });

      // Error events from the server (not connection errors)
      eventSource.addEventListener('error', (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data);
          setLastEvent({ type: 'error', data });
        } catch (e) {
          console.error('Error parsing server error event:', e);
          setLastEvent({ type: 'error', data: { error: 'Server error' } });
        }
      });

      eventSource.addEventListener('heartbeat', (event) => {
        // Keep connection alive
        console.debug('SSE heartbeat received');
      });

    } catch (error) {
      console.error('Failed to subscribe to transcription:', error);
      setConnectionStatus('error');
    }
  }, [getToken]);

  const unsubscribeFromTranscription = useCallback((transcriptionId: string) => {
    if (eventSourceRef.current) {
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