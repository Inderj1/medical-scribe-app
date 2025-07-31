import { useState, useEffect, useCallback, useRef } from 'react';

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface UseWebSpeechOptions {
  continuous?: boolean;
  interimResults?: boolean;
  language?: string;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: any) => void;
  onSilenceTimeout?: () => void;
  onEnd?: () => void;
  silenceTimeoutMs?: number;
}

interface UseWebSpeechReturn {
  isListening: boolean;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
  transcript: string;
  interimTranscript: string;
}

// Extend the Window interface to include SpeechRecognition
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export const useWebSpeech = (options: UseWebSpeechOptions = {}): UseWebSpeechReturn => {
  const {
    continuous = true,
    interimResults = true,
    language = 'en-US',
    onTranscript,
    onError,
    onSilenceTimeout,
    onEnd,
    silenceTimeoutMs = 5000,
  } = options;

  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');

  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef('');
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Check if Web Speech API is supported
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = continuous;
      recognition.interimResults = interimResults;
      recognition.lang = language;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        console.log('Speech recognition started');
        setIsListening(true);
      };

      recognition.onend = () => {
        console.log('Speech recognition ended');
        setIsListening(false);
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        if (onEnd) {
          onEnd();
        }
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcriptText = result[0].transcript;

          if (result.isFinal) {
            final += transcriptText + ' ';
          } else {
            interim += transcriptText;
          }
        }

        if (final) {
          finalTranscriptRef.current += final;
          setTranscript(finalTranscriptRef.current);
          if (onTranscript) {
            onTranscript(final.trim(), true);
          }
        }

        setInterimTranscript(interim);
        if (interim && onTranscript) {
          onTranscript(interim, false);
        }

        // Reset silence timer when we get speech
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }

        // Start a new silence timer if we're in continuous mode
        if (continuous && isListening && (final || interim)) {
          silenceTimerRef.current = setTimeout(() => {
            console.log('Stopping due to silence timeout');
            if (onSilenceTimeout) {
              onSilenceTimeout();
            }
            if (recognitionRef.current) {
              recognitionRef.current.stop();
            }
          }, silenceTimeoutMs);
        }
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        
        // Handle network errors specifically
        if (event.error === 'network') {
          console.log('Network error detected, will retry when connection is restored');
          // Don't call onError for network issues to avoid stopping the session
          // The browser will handle reconnection automatically
          return;
        }
        
        if (onError) {
          onError(event.error);
        }

        // Auto-restart for certain errors
        if (event.error === 'no-speech' || event.error === 'audio-capture' || event.error === 'network') {
          setTimeout(() => {
            if (recognitionRef.current && event.error !== 'network') {
              try {
                recognitionRef.current.start();
              } catch (e) {
                console.error('Failed to restart recognition:', e);
              }
            }
          }, 1000);
        }
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
    };
  }, [continuous, interimResults, language, onTranscript, onError, onSilenceTimeout, onEnd, silenceTimeoutMs]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      try {
        finalTranscriptRef.current = '';
        setTranscript('');
        setInterimTranscript('');
        recognitionRef.current.start();
      } catch (error) {
        console.error('Failed to start recognition:', error);
        if (onError) {
          onError(error);
        }
      }
    }
  }, [isListening, onError]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, [isListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    transcript,
    interimTranscript,
  };
};