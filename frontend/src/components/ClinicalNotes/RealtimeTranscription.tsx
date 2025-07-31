import React, { useState, useEffect, useRef } from 'react';
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
  Tooltip
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import StopIcon from '@mui/icons-material/Stop';
import NotesIcon from '@mui/icons-material/Notes';
import FormatListBulletedIcon from '@mui/icons-material/FormatListBulleted';
import ArticleIcon from '@mui/icons-material/Article';
import { useUser, useAuth } from '@clerk/clerk-react';
import { agentWebSocketService, TranscriptionEvent } from '../../services/agentWebSocket';

interface RealtimeTranscriptionProps {
  encounterId: string;
  patientId: string;
  onTranscriptionUpdate?: (transcription: string, analysis?: any) => void;
}

type NoteFormat = 'soap' | 'bullet' | 'narrative';

interface TranscriptionSegment {
  text: string;
  speaker_id: string;
  speaker_role?: 'healthcare_provider' | 'patient' | 'nurse' | 'other';
  timestamp: string;
}

const RealtimeTranscription: React.FC<RealtimeTranscriptionProps> = ({
  encounterId,
  patientId,
  onTranscriptionUpdate
}) => {
  const { user } = useUser();
  const { getToken } = useAuth();
  
  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [fullTranscription, setFullTranscription] = useState('');
  const [transcriptionSegments, setTranscriptionSegments] = useState<TranscriptionSegment[]>([]);
  const [currentSpeaker, setCurrentSpeaker] = useState<string>('');
  const [speakerCount, setSpeakerCount] = useState(0);
  const [noteFormat, setNoteFormat] = useState<NoteFormat>('soap');
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  
  // Refs
  const transcriptionRef = useRef<HTMLDivElement>(null);
  const partialTextRef = useRef('');
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (transcriptionRef.current) {
      transcriptionRef.current.scrollTop = transcriptionRef.current.scrollHeight;
    }
  }, [currentTranscription, fullTranscription]);
  
  // Set up WebSocket connection
  useEffect(() => {
    const setupConnection = async () => {
      try {
        const token = await getToken();
        if (!token) {
          setError('Authentication required');
          return;
        }
        
        // Set up event handlers
        agentWebSocketService.on('connected', () => {
          setIsConnected(true);
          setConnectionStatus('connected');
          setError(null);
        });
        
        agentWebSocketService.on('disconnected', () => {
          setIsConnected(false);
          setConnectionStatus('disconnected');
          setIsRecording(false);
        });
        
        agentWebSocketService.on('transcription', handleTranscription);
        
        agentWebSocketService.on('error', (error) => {
          console.error('WebSocket error:', error);
          setError(error.message);
        });
        
        // Connect
        setConnectionStatus('connecting');
        await agentWebSocketService.connect(token);
        
      } catch (err) {
        console.error('Failed to connect:', err);
        setError('Failed to connect to transcription service');
        setConnectionStatus('disconnected');
      }
    };
    
    if (user?.id) {
      setupConnection();
    }
    
    // Cleanup
    return () => {
      if (isRecording) {
        handleStopRecording();
      }
      agentWebSocketService.disconnect();
    };
  }, [user?.id]);
  
  const handleTranscription = (event: TranscriptionEvent) => {
    if (event.type === 'partial') {
      // Update partial transcription with speaker
      partialTextRef.current = event.text;
      setCurrentTranscription(event.text);
      if (event.speaker_id) {
        setCurrentSpeaker(event.speaker_id);
      }
      if (event.speaker_count) {
        setSpeakerCount(event.speaker_count);
      }
    } else if (event.type === 'complete') {
      // Add to transcription segments
      const newSegment: TranscriptionSegment = {
        text: event.text,
        speaker_id: event.speaker_id || 'SPEAKER_00',
        speaker_role: event.speaker_role,
        timestamp: event.timestamp
      };
      
      setTranscriptionSegments(prev => [...prev, newSegment]);
      
      // Update full transcription
      const newText = event.text;
      setFullTranscription(prev => prev + (prev ? ' ' : '') + newText);
      setCurrentTranscription(''); // Clear partial
      partialTextRef.current = '';
      
      // Update speaker count
      if (event.speaker_count) {
        setSpeakerCount(event.speaker_count);
      }
      
      // Notify parent with analysis
      if (onTranscriptionUpdate) {
        onTranscriptionUpdate(newText, event.analysis);
      }
    }
  };
  
  const handleStartRecording = async () => {
    try {
      setError(null);
      await agentWebSocketService.startEncounter(encounterId, patientId);
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Failed to start recording. Please check microphone permissions.');
    }
  };
  
  const handleStopRecording = async () => {
    try {
      await agentWebSocketService.endEncounter();
      setIsRecording(false);
    } catch (err) {
      console.error('Failed to stop recording:', err);
    }
  };
  
  const handleFormatChange = (event: React.MouseEvent<HTMLElement>, newFormat: NoteFormat | null) => {
    if (newFormat !== null) {
      setNoteFormat(newFormat);
      agentWebSocketService.setFormatPreference(newFormat);
    }
  };
  
  // Helper function to get speaker label and color
  const getSpeakerInfo = (speaker_id: string, role?: string) => {
    const speakerColors = ['#1976d2', '#388e3c', '#d32f2f', '#f57c00', '#7b1fa2'];
    const speakerIndex = parseInt(speaker_id.replace('SPEAKER_', '')) || 0;
    const color = speakerColors[speakerIndex % speakerColors.length];
    
    let label = speaker_id;
    if (role === 'healthcare_provider') label = 'Provider';
    else if (role === 'patient') label = 'Patient';
    else if (role === 'nurse') label = 'Nurse';
    
    return { label, color };
  };
  
  return (
    <Paper elevation={2} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" gutterBottom>
            Real-time Transcription
          </Typography>
          
          <Stack direction="row" spacing={1} alignItems="center">
            {/* Connection Status */}
            <Chip
              size="small"
              label={connectionStatus}
              color={connectionStatus === 'connected' ? 'success' : 'default'}
              variant={connectionStatus === 'connecting' ? 'outlined' : 'filled'}
            />
            
            {/* Speaker Count */}
            {speakerCount > 0 && (
              <Chip
                size="small"
                label={`${speakerCount} speaker${speakerCount > 1 ? 's' : ''}`}
                variant="outlined"
              />
            )}
            
            {/* Format Selection */}
            <ToggleButtonGroup
              value={noteFormat}
              exclusive
              onChange={handleFormatChange}
              size="small"
            >
              <ToggleButton value="soap">
                <Tooltip title="SOAP Format">
                  <NotesIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="bullet">
                <Tooltip title="Bullet Points">
                  <FormatListBulletedIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="narrative">
                <Tooltip title="Narrative">
                  <ArticleIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </Stack>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Error Alert */}
      {error && (
        <Fade in>
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        </Fade>
      )}
      
      {/* Transcription Display */}
      <Box
        ref={transcriptionRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          bgcolor: 'background.default',
          borderRadius: 1,
          p: 2,
          mb: 2,
          minHeight: 200,
          position: 'relative'
        }}
      >
        {/* Transcription Segments with Speaker Attribution */}
        {transcriptionSegments.map((segment, index) => {
          const speakerInfo = getSpeakerInfo(segment.speaker_id, segment.speaker_role);
          return (
            <Box key={index} sx={{ mb: 2 }}>
              <Chip
                size="small"
                label={speakerInfo.label}
                sx={{
                  bgcolor: speakerInfo.color,
                  color: 'white',
                  mb: 0.5,
                  fontWeight: 'medium'
                }}
              />
              <Typography variant="body1" sx={{ ml: 1 }}>
                {segment.text}
              </Typography>
            </Box>
          );
        })}
        
        {/* Current/Partial Transcription */}
        {currentTranscription && (
          <Box sx={{ mt: 2 }}>
            {currentSpeaker && (
              <Chip
                size="small"
                label={getSpeakerInfo(currentSpeaker).label}
                sx={{
                  bgcolor: getSpeakerInfo(currentSpeaker).color,
                  color: 'white',
                  mb: 0.5,
                  fontWeight: 'medium',
                  opacity: 0.7
                }}
              />
            )}
            <Typography 
              variant="body1" 
              sx={{ 
                color: 'text.secondary',
                fontStyle: 'italic',
                ml: 1
              }}
            >
              {currentTranscription}
            </Typography>
          </Box>
        )}
        
        {/* Empty State */}
        {transcriptionSegments.length === 0 && !currentTranscription && !isRecording && (
          <Typography variant="body2" color="text.secondary" align="center">
            Click the microphone to start real-time transcription
          </Typography>
        )}
        
        {/* Recording Indicator */}
        {isRecording && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <FiberManualRecordIcon 
              sx={{ 
                color: 'error.main',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%': { opacity: 1 },
                  '50%': { opacity: 0.5 },
                  '100%': { opacity: 1 }
                }
              }} 
            />
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              Listening...
            </Typography>
          </Box>
        )}
      </Box>
      
      {/* Recording Progress */}
      {isRecording && (
        <LinearProgress 
          sx={{ mb: 2 }} 
          color="primary"
          variant="indeterminate"
        />
      )}
      
      {/* Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Button
          variant="contained"
          size="large"
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          disabled={!isConnected}
          startIcon={isRecording ? <StopIcon /> : <MicIcon />}
          color={isRecording ? 'error' : 'primary'}
          sx={{ minWidth: 150 }}
        >
          {isRecording ? 'Stop' : 'Start'} Recording
        </Button>
      </Box>
    </Paper>
  );
};

export default RealtimeTranscription;