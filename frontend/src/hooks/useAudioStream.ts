import { useState, useEffect, useCallback, useRef } from 'react';

interface UseAudioStreamOptions {
  // Audio chunk duration in milliseconds
  chunkDurationMs?: number;
  // Audio format (webm/opus is recommended for size and compatibility)
  mimeType?: string;
  // Callback when audio chunk is ready
  onAudioChunk?: (audioBlob: Blob, chunkNumber: number) => void;
  // Callback for errors
  onError?: (error: Error) => void;
  // Audio constraints
  audioConstraints?: MediaTrackConstraints;
}

interface UseAudioStreamReturn {
  isRecording: boolean;
  isSupported: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  audioLevel: number;
  chunkCount: number;
  error: Error | null;
}

export const useAudioStream = (options: UseAudioStreamOptions = {}): UseAudioStreamReturn => {
  const {
    chunkDurationMs = 3000, // 3 seconds by default
    mimeType = 'audio/webm;codecs=opus', // Opus codec for better compression
    onAudioChunk,
    onError,
    audioConstraints = {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 16000 // 16kHz is sufficient for speech
    }
  } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [chunkCount, setChunkCount] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const chunkNumberRef = useRef(0);
  const audioChunksRef = useRef<Blob[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Check browser support
  useEffect(() => {
    const checkSupport = () => {
      const hasGetUserMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      const hasMediaRecorder = !!window.MediaRecorder;
      const supportsMimeType = hasMediaRecorder && MediaRecorder.isTypeSupported(mimeType);
      
      setIsSupported(hasGetUserMedia && hasMediaRecorder && supportsMimeType);
      
      if (!hasGetUserMedia) {
        setError(new Error('getUserMedia is not supported in this browser'));
      } else if (!hasMediaRecorder) {
        setError(new Error('MediaRecorder is not supported in this browser'));
      } else if (!supportsMimeType) {
        setError(new Error(`MIME type ${mimeType} is not supported`));
      }
    };

    checkSupport();
  }, [mimeType]);

  // Audio level monitoring
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current || !isRecording) {
      return;
    }

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average volume
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    const normalizedLevel = Math.min(100, (average / 255) * 100);
    setAudioLevel(normalizedLevel);

    // Continue monitoring
    animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
  }, [isRecording]);

  // Start recording
  const startRecording = useCallback(async () => {
    if (!isSupported || isRecording) {
      return;
    }

    try {
      // Reset state
      setError(null);
      chunkNumberRef.current = 0;
      setChunkCount(0);
      audioChunksRef.current = [];

      // Get audio stream
      console.log('[useAudioStream] Requesting microphone permission...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
        video: false
      });
      console.log('[useAudioStream] Microphone permission granted, stream obtained');
      audioStreamRef.current = stream;

      // Setup audio level monitoring
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      // Create MediaRecorder
      const options: MediaRecorderOptions = {
        mimeType,
        audioBitsPerSecond: 128000 // 128kbps for good quality
      };

      console.log('[useAudioStream] Creating MediaRecorder with options:', options);
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      console.log('[useAudioStream] MediaRecorder created successfully');

      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle recording stop
      mediaRecorder.onstop = () => {
        // Create final blob from accumulated chunks
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          if (audioBlob.size > 0 && onAudioChunk) {
            chunkNumberRef.current++;
            setChunkCount(chunkNumberRef.current);
            onAudioChunk(audioBlob, chunkNumberRef.current);
          }
          audioChunksRef.current = [];
        }
      };

      // Handle errors
      mediaRecorder.onerror = (event: any) => {
        const error = new Error(`MediaRecorder error: ${event.error}`);
        setError(error);
        if (onError) {
          onError(error);
        }
        stopRecording();
      };

      // Start recording with time slicing
      mediaRecorder.start(chunkDurationMs);
      setIsRecording(true);

      // Start audio level monitoring
      monitorAudioLevel();

      console.log('Audio recording started', {
        mimeType,
        chunkDurationMs,
        audioBitsPerSecond: options.audioBitsPerSecond
      });

    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to start recording');
      setError(error);
      if (onError) {
        onError(error);
      }
      console.error('Failed to start recording:', err);
    }
  }, [isSupported, isRecording, audioConstraints, mimeType, chunkDurationMs, onAudioChunk, onError, monitorAudioLevel]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (!isRecording) {
      return;
    }

    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    // Stop audio stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    setIsRecording(false);
    setAudioLevel(0);

    console.log('Audio recording stopped', {
      totalChunks: chunkNumberRef.current
    });
  }, [isRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, [stopRecording]);

  return {
    isRecording,
    isSupported,
    startRecording,
    stopRecording,
    audioLevel,
    chunkCount,
    error
  };
};