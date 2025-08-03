import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  Fade,
  Alert,
  LinearProgress,
  Chip,
  Stack,
  Divider,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
  CircularProgress
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import StopIcon from '@mui/icons-material/Stop';
import NotesIcon from '@mui/icons-material/Notes';
import FormatListBulletedIcon from '@mui/icons-material/FormatListBulleted';
import ArticleIcon from '@mui/icons-material/Article';
import PersonIcon from '@mui/icons-material/Person';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import { useAuth } from '../../hooks/useAuthWrapper';
import { useAudioStream } from '../../hooks/useAudioStream';
import { streamingAPI } from '../../services/streaming-api';
import { useSSE } from '../../contexts/SSEContext';

interface AudioStreamingTranscriptionProps {
  sessionId: string;
  encounterId: string;
  patientId: string;
  onTranscriptionUpdate?: (transcription: string, speaker?: string) => void;
  onError?: (error: string) => void;
}

type NoteFormat = 'soap' | 'bullet' | 'narrative';

interface TranscriptionSegment {
  text: string;
  speaker: string;
  timestamp: number;
  chunkNumber?: number;
  startTime?: number;
  endTime?: number;
}

// Speaker label mapping
const SPEAKER_LABELS: Record<string, { label: string; color: string; icon: React.ReactElement }> = {
  'SPEAKER_00': { 
    label: 'Doctor', 
    color: '#2196f3',
    icon: <LocalHospitalIcon fontSize="small" />
  },
  'SPEAKER_01': { 
    label: 'Patient', 
    color: '#4caf50',
    icon: <PersonIcon fontSize="small" />
  },
  'SPEAKER_02': { 
    label: 'Nurse', 
    color: '#ff9800',
    icon: <LocalHospitalIcon fontSize="small" />
  },
  'SPEAKER_03': { 
    label: 'Other', 
    color: '#9c27b0',
    icon: <PersonIcon fontSize="small" />
  },
};

const AudioStreamingTranscription: React.FC<AudioStreamingTranscriptionProps> = ({
  sessionId,
  encounterId,
  patientId,
  onTranscriptionUpdate,
  onError
}) => {
  console.log('[AudioStreamingTranscription] Component mounted with props:', {
    sessionId,
    encounterId,
    patientId
  });
  const { getToken } = useAuth();
  const { subscribeToTranscription, unsubscribeFromTranscription, lastEvent } = useSSE();
  
  // State
  const [isRecording, setIsRecording] = useState(false);
  const [transcriptionSegments, setTranscriptionSegments] = useState<TranscriptionSegment[]>([]);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [speakersDetected, setSpeakersDetected] = useState<string[]>([]);
  const [noteFormat, setNoteFormat] = useState<NoteFormat>('soap');
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  
  // Refs
  const transcriptionRef = useRef<HTMLDivElement>(null);
  const audioChunkQueue = useRef<Blob[]>([]);
  const isUploadingRef = useRef(false);
  
  // Audio streaming hook
  const {
    isRecording: isAudioRecording,
    isSupported,
    startRecording,
    stopRecording,
    audioLevel: currentAudioLevel,
    chunkCount,
    error: audioError
  } = useAudioStream({
    chunkDurationMs: 3000, // 3 second chunks
    onAudioChunk: handleAudioChunk,
    onError: handleAudioError
  });
  
  // Update audio level
  useEffect(() => {
    setAudioLevel(currentAudioLevel);
  }, [currentAudioLevel]);
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (transcriptionRef.current) {
      transcriptionRef.current.scrollTop = transcriptionRef.current.scrollHeight;
    }
  }, [transcriptionSegments, currentTranscription]);
  
  // Auto-start recording when component mounts with a valid session
  useEffect(() => {
    console.log('[AudioStreaming] useEffect triggered:', { sessionId, isRecording, error, isSupported });
    if (sessionId && !isRecording && !error && isSupported) {
      console.log('[AudioStreaming] Auto-starting recording for session:', sessionId);
      handleStartRecording();
    }
  }, [sessionId]); // Only depend on sessionId to run once when mounted
  
  // Subscribe to SSE events
  useEffect(() => {
    if (sessionId && isRecording) {
      // Extract transcription ID from session ID
      const transcriptionId = sessionId.replace('session_', '');
      subscribeToTranscription(transcriptionId);
    }
    
    return () => {
      if (sessionId) {
        const transcriptionId = sessionId.replace('session_', '');
        unsubscribeFromTranscription(transcriptionId);
      }
    };
  }, [sessionId, isRecording, subscribeToTranscription, unsubscribeFromTranscription]);
  
  // Handle SSE events via lastEvent
  useEffect(() => {
    if (lastEvent && lastEvent.type === 'transcript_chunk' && lastEvent.data) {
      const segment: TranscriptionSegment = {
        text: lastEvent.data.text,
        speaker: lastEvent.data.speaker || 'SPEAKER_00',
        timestamp: Date.now(),
        chunkNumber: lastEvent.data.chunk_number,
        startTime: lastEvent.data.start_time,
        endTime: lastEvent.data.end_time
      };
      
      setTranscriptionSegments(prev => [...prev, segment]);
      
      // Update speakers list
      if (!speakersDetected.includes(segment.speaker)) {
        setSpeakersDetected(prev => [...prev, segment.speaker]);
      }
      
      // Notify parent
      if (onTranscriptionUpdate) {
        onTranscriptionUpdate(segment.text, segment.speaker);
      }
    }
  }, [lastEvent, onTranscriptionUpdate, speakersDetected]);
  
  // Handle audio chunk
  async function handleAudioChunk(audioBlob: Blob, chunkNumber: number) {
    console.log(`[AudioStreaming] Received audio chunk ${chunkNumber}, size: ${audioBlob.size} bytes, sessionId: ${sessionId}`);
    
    // Add to queue
    audioChunkQueue.current.push(audioBlob);
    
    // Process queue if not already processing
    if (!isUploadingRef.current) {
      processAudioQueue();
    }
  }
  
  // Process audio queue
  async function processAudioQueue() {
    if (audioChunkQueue.current.length === 0 || isUploadingRef.current) {
      return;
    }
    
    isUploadingRef.current = true;
    
    while (audioChunkQueue.current.length > 0) {
      const audioBlob = audioChunkQueue.current.shift();
      if (!audioBlob) continue;
      
      try {
        const token = await getToken();
        if (!token) {
          throw new Error('No authentication token');
        }
        
        // Upload audio chunk
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'audio.webm');
        formData.append('chunk_number', chunkCount.toString());
        
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/streaming/${sessionId}/audio`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Audio chunk processed:', result);
        
      } catch (err) {
        console.error('Error uploading audio chunk:', err);
        handleError(err instanceof Error ? err.message : 'Failed to upload audio');
      }
    }
    
    isUploadingRef.current = false;
  }
  
  // Handle audio error
  function handleAudioError(error: Error) {
    console.error('Audio error:', error);
    handleError(error.message);
  }
  
  // Handle error
  function handleError(message: string) {
    setError(message);
    if (onError) {
      onError(message);
    }
  }
  
  // Start recording
  const handleStartRecording = async () => {
    try {
      console.log('[AudioStreaming] Starting recording with sessionId:', sessionId);
      setError(null);
      setTranscriptionSegments([]);
      setSpeakersDetected([]);
      
      // Start audio recording
      await startRecording();
      setIsRecording(true);
      console.log('[AudioStreaming] Recording started successfully');
      
    } catch (err) {
      console.error('Failed to start recording:', err);
      handleError(err instanceof Error ? err.message : 'Failed to start recording');
    }
  };
  
  // Stop recording
  const handleStopRecording = async () => {
    try {
      // Stop audio recording
      stopRecording();
      setIsRecording(false);
      
      // Process any remaining audio chunks
      setIsProcessing(true);
      await processAudioQueue();
      
      // End the streaming session
      const token = await getToken();
      if (token && sessionId) {
        await streamingAPI.endSession(sessionId, token);
      }
      
      setIsProcessing(false);
      
    } catch (err) {
      console.error('Failed to stop recording:', err);
      handleError(err instanceof Error ? err.message : 'Failed to stop recording');
      setIsProcessing(false);
    }
  };
  
  // Format change
  const handleFormatChange = (event: React.MouseEvent<HTMLElement>, newFormat: NoteFormat | null) => {
    if (newFormat !== null) {
      setNoteFormat(newFormat);
    }
  };
  
  // Get speaker info
  const getSpeakerInfo = (speaker: string) => {
    return SPEAKER_LABELS[speaker] || {
      label: speaker,
      color: '#757575',
      icon: <PersonIcon fontSize="small" />
    };
  };
  
  // Merge consecutive segments from same speaker
  const getMergedSegments = () => {
    const merged: TranscriptionSegment[] = [];
    
    transcriptionSegments.forEach((segment, index) => {
      if (index === 0 || segment.speaker !== transcriptionSegments[index - 1].speaker) {
        merged.push({ ...segment });
      } else {
        // Merge with previous segment
        merged[merged.length - 1].text += ' ' + segment.text;
        merged[merged.length - 1].endTime = segment.endTime;
      }
    });
    
    return merged;
  };
  
  if (!isSupported) {
    return (
      <Alert severity="error">
        Audio recording is not supported in your browser. Please use Chrome, Edge, or Safari.
      </Alert>
    );
  }
  
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', color: 'white' }}>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap">
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Audio Streaming Mode
          </Typography>
          
          <Stack direction="row" spacing={1} alignItems="center">
            {/* Recording Status */}
            {isRecording && (
              <Chip
                size="small"
                label="Recording"
                color="error"
                icon={<FiberManualRecordIcon />}
              />
            )}
            
            {/* Processing Status */}
            {isProcessing && (
              <Chip
                size="small"
                label="Processing"
                color="primary"
                icon={<CircularProgress size={16} />}
              />
            )}
            
            {/* Speakers Detected */}
            {speakersDetected.length > 0 && (
              <Chip
                size="small"
                label={`${speakersDetected.length} speaker${speakersDetected.length > 1 ? 's' : ''}`}
                variant="outlined"
              />
            )}
            
          </Stack>
        </Stack>
        
        {/* Audio Level Indicator */}
        {isRecording && (
          <LinearProgress 
            variant="determinate" 
            value={audioLevel} 
            sx={{ mt: 1, height: 4, borderRadius: 2 }}
          />
        )}
      </Box>
      
      <Divider sx={{ mb: 2, borderColor: 'rgba(255,255,255,0.2)' }} />
      
      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {/* Audio Error Alert */}
      {audioError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {audioError.message}
        </Alert>
      )}
      
      {/* Transcription Display */}
      <Box
        ref={transcriptionRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          bgcolor: 'rgba(255,255,255,0.05)',
          borderRadius: 1,
          p: 2,
          mb: 2,
          minHeight: 200,
          position: 'relative'
        }}
      >
        {/* Merged Transcription Segments with Speaker Attribution */}
        {getMergedSegments().map((segment, index) => {
          const speakerInfo = getSpeakerInfo(segment.speaker);
          return (
            <Box key={index} sx={{ mb: 2 }}>
              <Stack direction="row" spacing={1} alignItems="flex-start">
                <Chip
                  size="small"
                  label={speakerInfo.label}
                  icon={speakerInfo.icon}
                  sx={{
                    bgcolor: speakerInfo.color + '40',
                    color: 'white',
                    border: `1px solid ${speakerInfo.color}`,
                    '& .MuiChip-icon': { color: 'white' }
                  }}
                />
              </Stack>
              <Typography
                variant="body1"
                sx={{
                  mt: 0.5,
                  pl: 2,
                  color: 'rgba(255,255,255,0.95)',
                  lineHeight: 1.6
                }}
              >
                {segment.text}
              </Typography>
              {segment.startTime !== undefined && segment.endTime !== undefined && (
                <Typography
                  variant="caption"
                  sx={{
                    pl: 2,
                    color: 'rgba(255,255,255,0.6)',
                    display: 'block',
                    mt: 0.5
                  }}
                >
                  {new Date(segment.timestamp).toLocaleTimeString()} 
                  {' • '}
                  {Math.round(segment.endTime - segment.startTime)}s
                </Typography>
              )}
            </Box>
          );
        })}
        
        {/* Current Transcription (if any) */}
        {currentTranscription && (
          <Fade in>
            <Box sx={{ opacity: 0.7 }}>
              <Typography variant="body1" sx={{ fontStyle: 'italic' }}>
                {currentTranscription}
              </Typography>
            </Box>
          </Fade>
        )}
        
        {/* Empty State */}
        {transcriptionSegments.length === 0 && !currentTranscription && !isRecording && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'rgba(255,255,255,0.7)'
            }}
          >
            <Typography variant="body2">
              Click the microphone to start recording
            </Typography>
          </Box>
        )}
      </Box>
      
      {/* Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        {!isRecording ? (
          <Button
            variant="contained"
            size="large"
            startIcon={<MicIcon />}
            onClick={handleStartRecording}
            disabled={isProcessing}
            sx={{
              bgcolor: 'rgba(255,255,255,0.2)',
              color: 'white',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.3)' }
            }}
          >
            Start Recording
          </Button>
        ) : (
          <Button
            variant="contained"
            size="large"
            startIcon={<StopIcon />}
            onClick={handleStopRecording}
            disabled={isProcessing}
            color="error"
            sx={{
              animation: 'pulse 2s infinite',
              '@keyframes pulse': {
                '0%': { opacity: 1 },
                '50%': { opacity: 0.8 },
                '100%': { opacity: 1 }
              }
            }}
          >
            Stop Recording
          </Button>
        )}
      </Box>
      
      {/* Recording Info */}
      {isRecording && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
            Audio chunks sent: {chunkCount}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default AudioStreamingTranscription;