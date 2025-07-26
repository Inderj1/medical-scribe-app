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
      // Update partial transcription
      partialTextRef.current = event.text;
      setCurrentTranscription(event.text);
    } else if (event.type === 'complete') {
      // Add to full transcription
      const newText = event.text;
      setFullTranscription(prev => prev + (prev ? ' ' : '') + newText);
      setCurrentTranscription(''); // Clear partial
      partialTextRef.current = '';
      
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
        {/* Full Transcription */}
        {fullTranscription && (
          <Typography variant="body1" paragraph>
            {fullTranscription}
          </Typography>
        )}
        
        {/* Current/Partial Transcription */}
        {currentTranscription && (
          <Typography 
            variant="body1" 
            sx={{ 
              color: 'text.secondary',
              fontStyle: 'italic'
            }}
          >
            {currentTranscription}
          </Typography>
        )}
        
        {/* Empty State */}
        {!fullTranscription && !currentTranscription && !isRecording && (
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