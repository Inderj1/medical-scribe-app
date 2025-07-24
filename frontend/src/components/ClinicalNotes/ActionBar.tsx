import React from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  CircularProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PrintIcon from '@mui/icons-material/Print';
import AddIcon from '@mui/icons-material/Add';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '@clerk/clerk-react';
import webSocketService from '../../services/websocket';
import authService from '../../services/auth';

interface ActionBarProps {
  onSaveDraft: () => void;
  onSignEncounter: () => void;
  isDraftSaved: boolean;
  lastSaveTime: Date;
  encounterId?: string;
  patientId?: string;
}

const ActionBar: React.FC<ActionBarProps> = ({
  onSaveDraft,
  onSignEncounter,
  isDraftSaved,
  lastSaveTime,
  encounterId = 'enc-001',
  patientId = 'patient-001'
}) => {
  const { getToken } = useAuth();
  const [isSaving, setIsSaving] = React.useState(false);
  const [isSigningOff, setIsSigningOff] = React.useState(false);
  const [isRecording, setIsRecording] = React.useState(false);
  const [mediaRecorder, setMediaRecorder] = React.useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = React.useState<Blob[]>([]);
  const [isWebSocketConnected, setIsWebSocketConnected] = React.useState(false);
  const [connectionError, setConnectionError] = React.useState<string | null>(null);

  React.useEffect(() => {
    // Listen for WebSocket connection status
    const handleConnectionStatus = (data: any) => {
      setIsWebSocketConnected(data.status === 'connected');
      if (data.status === 'error') {
        setConnectionError('WebSocket connection failed');
      } else {
        setConnectionError(null);
      }
    };

    webSocketService.on('connection:status', handleConnectionStatus);
    
    // Check initial connection status
    setIsWebSocketConnected(webSocketService.isConnected());
    
    return () => {
      webSocketService.off('connection:status', handleConnectionStatus);
    };
  }, []);

  const handleSaveDraft = async () => {
    setIsSaving(true);
    await onSaveDraft();
    setTimeout(() => setIsSaving(false), 500);
  };

  const handleSignEncounter = async () => {
    const confirmed = window.confirm(
      'Are you ready to sign and close this encounter? All documentation will be finalized.'
    );
    
    if (confirmed) {
      setIsSigningOff(true);
      await onSignEncounter();
      setTimeout(() => {
        setIsSigningOff(false);
        alert('Encounter signed and submitted to EMR');
      }, 1000);
    }
  };

  const handlePrintSummary = () => {
    window.print();
  };

  const handleAddAddendum = () => {
    console.log('Opening addendum editor...');
  };

  const getTimeSinceLastSave = () => {
    return formatDistanceToNow(lastSaveTime, { addSuffix: true });
  };

  const startRecording = async () => {
    try {
      // Check if WebSocket is connected
      if (!webSocketService.isConnected()) {
        console.log('WebSocket not connected, attempting to connect...');
        
        // Get authentication token from Clerk
        const clerkToken = await getToken();
        
        if (!clerkToken) {
          console.error('No Clerk token available');
          setConnectionError('Authentication failed. Please sign in.');
          return;
        }
        
        try {
          // Use Clerk token for WebSocket connection
          await webSocketService.connect(clerkToken);
          // Start encounter after connection
          webSocketService.startEncounter(encounterId, patientId);
        } catch (error) {
          console.error('WebSocket connection failed:', error);
          setConnectionError('Failed to connect to server');
          return;
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      // Check supported mime types
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      
      const recorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 16000
      });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          // Only send if WebSocket is connected
          if (webSocketService.isConnected()) {
            event.data.arrayBuffer().then(buffer => {
              try {
                webSocketService.sendAudioChunk(buffer);
              } catch (error) {
                console.error('Error sending audio chunk:', error);
              }
            });
          } else {
            // Store locally for now
            console.log('Storing audio chunk locally, WebSocket not connected');
          }
          setAudioChunks(prev => [...prev, event.data]);
        }
      };

      recorder.onstart = () => {
        console.log('Recording started');
        setIsRecording(true);
      };

      recorder.onstop = () => {
        console.log('Recording stopped');
        setIsRecording(false);
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
        
        // End encounter if connected
        if (webSocketService.isConnected()) {
          webSocketService.endEncounter();
        }
      };

      // Start recording with 3 second chunks to get complete webm files
      recorder.start(3000);
      setMediaRecorder(recorder);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setMediaRecorder(null);
      setAudioChunks([]);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <Paper
      elevation={3}
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        bgcolor: 'white',
        borderTop: 1,
        borderColor: 'divider',
        px: 3,
        py: 1.5,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 1200,
        boxShadow: '0 -2px 4px rgba(0,0,0,0.05)'
      }}
    >
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSignEncounter}
          disabled={isSigningOff}
          startIcon={isSigningOff ? <CircularProgress size={16} /> : <CheckCircleIcon />}
          sx={{ textTransform: 'none' }}
        >
          {isSigningOff ? 'Signing...' : 'Sign & Close Encounter'}
        </Button>
        
        <Button
          variant="contained"
          color="secondary"
          onClick={handleSaveDraft}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
          sx={{ 
            textTransform: 'none',
            bgcolor: '#6c757d',
            '&:hover': {
              bgcolor: '#5a6268'
            }
          }}
        >
          {isSaving ? 'Saving...' : 'Save Draft'}
        </Button>
        
        <Button
          variant="outlined"
          onClick={handlePrintSummary}
          startIcon={<PrintIcon />}
          sx={{ 
            textTransform: 'none',
            borderColor: '#6c757d',
            color: '#6c757d',
            '&:hover': {
              borderColor: '#5a6268',
              bgcolor: 'rgba(108, 117, 125, 0.04)'
            }
          }}
        >
          Print Summary
        </Button>
        
        <Button
          variant="outlined"
          onClick={handleAddAddendum}
          startIcon={<AddIcon />}
          sx={{ 
            textTransform: 'none',
            borderColor: '#6c757d',
            color: '#6c757d',
            '&:hover': {
              borderColor: '#5a6268',
              bgcolor: 'rgba(108, 117, 125, 0.04)'
            }
          }}
        >
          Add Addendum
        </Button>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Tooltip 
          title={
            connectionError
              ? connectionError
              : !isWebSocketConnected 
                ? "Click to connect and start recording" 
                : isRecording 
                  ? "Stop recording" 
                  : "Start recording"
          }
        >
          <IconButton
            onClick={toggleRecording}
            sx={{
              bgcolor: isRecording ? '#dc3545' : '#28a745',
              color: 'white',
              '&:hover': {
                bgcolor: isRecording ? '#c82333' : '#218838'
              },
              animation: isRecording ? 'pulse 1s ease-in-out infinite' : 'none'
            }}
          >
            {isRecording ? <MicOffIcon /> : <MicIcon />}
          </IconButton>
        </Tooltip>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Last saved:
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {isDraftSaved ? getTimeSinceLastSave() : 'Not saved'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Voice recording:
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <FiberManualRecordIcon 
              sx={{ 
                fontSize: 12, 
                color: isRecording ? '#dc3545' : '#6c757d',
                animation: isRecording ? 'pulse 1s ease-in-out infinite' : 'none'
              }} 
            />
            <Typography 
              variant="body2" 
              sx={{ 
                color: isRecording ? '#dc3545' : '#6c757d', 
                fontWeight: 500
              }}
            >
              {isRecording ? 'Recording' : 'Inactive'}
              {!isWebSocketConnected && ' (Not Connected)'}
            </Typography>
          </Box>
        </Box>
      </Box>

      <style>
        {`
          @keyframes pulse {
            0% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
            100% {
              opacity: 1;
            }
          }
        `}
      </style>
    </Paper>
  );
};

export default ActionBar;