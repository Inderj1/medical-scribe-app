import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Chip,
  Button,
  Divider,
  CircularProgress,
  Fade,
  Alert,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip
} from '@mui/material';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import HistoryIcon from '@mui/icons-material/History';
import AssignmentIcon from '@mui/icons-material/Assignment';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import MedicationIcon from '@mui/icons-material/Medication';
import NoteAddIcon from '@mui/icons-material/NoteAdd';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import MenuIcon from '@mui/icons-material/Menu';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import webSocketService from '../../services/websocket';
import audioRecorderService from '../../services/audioRecorder';
import { useUser, useAuth } from '@clerk/clerk-react';

interface LiveTranscriptionProps {
  encounterId: string;
  onAddToSection?: (section: string, content: string, transcriptionId?: string) => void;
}

interface TranscriptionSegment {
  id: string;
  text: string;
  timestamp: Date;
  confidence: number;
  status: 'pending' | 'processed' | 'added';
  suggestedSection?: string;
}

const SECTION_MAPPINGS = [
  { key: 'chief_complaint', label: 'Chief Complaint', icon: <AssignmentIcon /> },
  { key: 'present_illness', label: 'Present Illness', icon: <LocalHospitalIcon /> },
  { key: 'medications', label: 'Medications', icon: <MedicationIcon /> },
  { key: 'physical_exam', label: 'Physical Exam', icon: <AssignmentIcon /> },
  { key: 'assessment_plan', label: 'Assessment & Plan', icon: <NoteAddIcon /> },
  { key: 'history', label: 'Medical History', icon: <HistoryIcon /> }
];

const LiveTranscription: React.FC<LiveTranscriptionProps> = ({ 
  encounterId, 
  onAddToSection 
}) => {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [isListening, setIsListening] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionSegments, setTranscriptionSegments] = useState<TranscriptionSegment[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSegment, setSelectedSegment] = useState<TranscriptionSegment | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false); // For hiding to sidebar
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const transcriptionEndRef = useRef<null | HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    
    // Connect to WebSocket when component mounts
    const connectWebSocket = async () => {
      try {
        if (!mounted) return;
        
        if (user?.id && !webSocketService.isConnected()) {
          const token = await getToken();
          console.log('Got auth token:', token ? 'yes' : 'no');
          
          if (token && mounted) {
            // Reset connection state in case it's stuck
            webSocketService.resetConnection();
            await webSocketService.connect(token);
            
            // Small delay to ensure connection is established
            await new Promise(resolve => setTimeout(resolve, 100));
            
            if (mounted && webSocketService.isConnected()) {
              // Start encounter
              webSocketService.startEncounter(encounterId, user.id);
            }
          }
        }
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        // Only set error if not "Already connecting" or timeout
        const errorMessage = error instanceof Error ? error.message : String(error);
        if (!errorMessage.includes('Already connecting') && 
            !errorMessage.includes('Connection timeout')) {
          setRecordingError('Failed to connect to server');
        }
      }
    };

    connectWebSocket();

    // Listen for connection status
    const handleConnectionStatus = (data: any) => {
      setIsConnected(data.status === 'connected');
      if (data.status === 'error') {
        setRecordingError('Connection error');
      }
    };

    // Listen for transcription updates
    const handlePartialTranscription = (data: any) => {
      console.log('Received partial transcription:', data);
      setCurrentTranscription(data.text);
      setIsListening(true);
    };

    const handleFinalTranscription = (data: any) => {
      console.log('Received final transcription:', data);
      // Add to segments
      const newSegment: TranscriptionSegment = {
        id: Date.now().toString(),
        text: data.text,
        timestamp: new Date(data.timestamp),
        confidence: data.confidence || 0.95,
        status: 'pending',
        suggestedSection: data.suggestedSection || 'history'
      };
      setTranscriptionSegments(prev => [...prev, newSegment]);
      setCurrentTranscription('');
    };

    const handleNotesUpdate = (data: any) => {
      console.log('Received notes update:', data);
      // Handle clinical notes updates if needed
    };

    // Register event listeners
    webSocketService.on('connection:status', handleConnectionStatus);
    webSocketService.on('transcription:partial', handlePartialTranscription);
    webSocketService.on('transcription:final', handleFinalTranscription);
    webSocketService.on('notes:update', handleNotesUpdate);

    // Check initial connection status
    const checkConnection = () => {
      const connected = webSocketService.isConnected();
      setIsConnected(connected);
      console.log('WebSocket connection status:', connected);
    };
    
    checkConnection();
    // Check again after a short delay to catch delayed connections
    const connectionCheckTimer = setTimeout(checkConnection, 1000);

    return () => {
      mounted = false;
      clearTimeout(connectionCheckTimer);
      webSocketService.off('connection:status', handleConnectionStatus);
      webSocketService.off('transcription:partial', handlePartialTranscription);
      webSocketService.off('transcription:final', handleFinalTranscription);
      webSocketService.off('notes:update', handleNotesUpdate);
      
      // Stop recording if active
      if (isRecording) {
        audioRecorderService.stop();
      }
      
      // End encounter
      webSocketService.endEncounter(user?.id);
    };
  }, [encounterId, user]);

  useEffect(() => {
    // Auto-scroll to bottom when new segments are added
    transcriptionEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcriptionSegments]);

  const handleAddToSection = (segment: TranscriptionSegment, section: string) => {
    if (onAddToSection) {
      onAddToSection(section, segment.text, segment.id);
    }
    
    // Mark segment as added
    setTranscriptionSegments(prev => 
      prev.map(s => s.id === segment.id ? { ...s, status: 'added' } : s)
    );
    
    handleCloseMenu();
  };

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, segment: TranscriptionSegment) => {
    setAnchorEl(event.currentTarget);
    setSelectedSegment(segment);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
    setSelectedSegment(null);
  };

  const handleCopyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getSegmentColor = (segment: TranscriptionSegment) => {
    if (segment.status === 'added') return '#d4edda';
    if (segment.confidence < 0.8) return '#fff3cd';
    return '#f8f9fa';
  };

  // Recording controls
  const startRecording = async () => {
    try {
      setRecordingError(null);
      
      if (!isConnected) {
        setRecordingError('Not connected to server. Please wait...');
        return;
      }

      await audioRecorderService.start({
        onError: (error) => {
          console.error('Recording error:', error);
          setRecordingError('Microphone access denied or unavailable');
          setIsRecording(false);
          setIsListening(false);
        },
        onStop: () => {
          setIsRecording(false);
          setIsListening(false);
        }
      });

      setIsRecording(true);
      setIsListening(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      setRecordingError('Failed to start recording');
    }
  };

  const stopRecording = () => {
    audioRecorderService.stop();
    setIsRecording(false);
    setIsListening(false);
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // When collapsed, show just a vertical sidebar
  if (isCollapsed) {
    return (
      <Paper
        elevation={3}
        sx={{
          bgcolor: 'white',
          borderRadius: 2,
          height: '100%',
          width: '60px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid',
          borderColor: 'divider',
          transition: 'width 0.3s ease'
        }}
      >
        <Box
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            px: 1,
            py: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            height: '100%'
          }}
        >
          <IconButton 
            size="small" 
            onClick={() => setIsCollapsed(false)}
            sx={{ 
              p: 0.5,
              color: 'white',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.1)'
              }
            }}
          >
            <MenuIcon sx={{ fontSize: 20 }} />
          </IconButton>
          
          <Box sx={{ 
            writingMode: 'vertical-rl',
            textOrientation: 'mixed',
            display: 'flex',
            alignItems: 'center',
            gap: 1
          }}>
            <RecordVoiceOverIcon sx={{ fontSize: 20, color: 'white', transform: 'rotate(90deg)' }} />
            <Typography variant="caption" sx={{ fontWeight: 600, color: 'white', letterSpacing: 1 }}>
              Live Transcription
            </Typography>
          </Box>

          {isRecording && (
            <Box sx={{ 
              width: 8, 
              height: 8, 
              borderRadius: '50%', 
              bgcolor: '#ff4444',
              animation: 'pulse 1.5s ease-in-out infinite'
            }} />
          )}
        </Box>
      </Paper>
    );
  }

  return (
    <Paper
      elevation={3}
      sx={{
        bgcolor: 'white',
        borderRadius: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid',
        borderColor: 'divider',
        transition: 'width 0.3s ease'
      }}
    >
      <Box
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          transition: 'all 0.2s ease',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)'
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <RecordVoiceOverIcon sx={{ fontSize: 20, color: 'white' }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'white' }}>
            Live Transcription
          </Typography>
          {isRecording && (
            <Chip 
              label="● LIVE" 
              size="small" 
              sx={{ 
                bgcolor: '#ff4444',
                color: 'white',
                animation: 'pulse 1.5s ease-in-out infinite',
                height: 22,
                fontWeight: 600,
                fontSize: '0.65rem'
              }}
            />
          )}
        </Box>
        
        {/* Hamburger Menu for Collapse - Right Aligned */}
        <IconButton 
          size="small" 
          onClick={() => setIsCollapsed(true)}
          sx={{ 
            p: 0.5,
            color: 'white',
            '&:hover': {
              bgcolor: 'rgba(255,255,255,0.1)'
            }
          }}
        >
          <MenuIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      <Box sx={{ 
        flex: 1,
        overflow: 'auto', 
        p: 2,
        bgcolor: '#fafbfc'
      }}>
        {/* Current transcription */}
        {currentTranscription && (
          <Fade in={true}>
            <Box 
              sx={{ 
                mb: 2,
                p: 2,
                bgcolor: '#e3f2fd',
                borderRadius: 2,
                border: '2px solid #2196f3',
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '3px',
                  background: 'linear-gradient(90deg, #2196f3, #21cbf3, #2196f3)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 2s linear infinite',
                  borderRadius: '2px 2px 0 0'
                },
                '@keyframes shimmer': {
                  '0%': { backgroundPosition: '-200% 0' },
                  '100%': { backgroundPosition: '200% 0' }
                }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <CircularProgress size={16} sx={{ color: '#2196f3' }} />
                <Typography variant="caption" sx={{ fontWeight: 600, color: '#2196f3' }}>
                  Live Transcription in Progress...
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ lineHeight: 1.6, fontWeight: 500 }}>
                {currentTranscription}
              </Typography>
            </Box>
          </Fade>
        )}

        {/* Error display */}
        {recordingError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setRecordingError(null)}>
            {recordingError}
          </Alert>
        )}

        {/* Recording controls */}
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            size="large"
            onClick={toggleRecording}
            disabled={!isConnected}
            startIcon={isRecording ? <MicOffIcon /> : <MicIcon />}
            sx={{
              bgcolor: isRecording ? '#dc3545' : '#1976d2',
              '&:hover': {
                bgcolor: isRecording ? '#c82333' : '#1565c0'
              },
              px: 3,
              py: 1.5
            }}
          >
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </Button>
        </Box>

        {/* Connection status */}
        {!isConnected && (
          <Box sx={{ mb: 2 }}>
            <Alert severity="warning" sx={{ mb: 1 }}>
              Connecting to server...
            </Alert>
            <Button 
              size="small" 
              variant="outlined" 
              onClick={async () => {
                try {
                  webSocketService.resetConnection();
                  const token = await getToken();
                  if (token) {
                    await webSocketService.connect(token);
                    if (user?.id) {
                      webSocketService.startEncounter(encounterId, user.id);
                    }
                  }
                } catch (error) {
                  console.error('Manual connection failed:', error);
                }
              }}
            >
              Retry Connection
            </Button>
          </Box>
        )}

        {/* Transcription segments */}
        {transcriptionSegments.length === 0 && !currentTranscription ? (
          <Box sx={{ 
            textAlign: 'center', 
            py: 6,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '200px',
            bgcolor: 'white',
            borderRadius: 2,
            border: '2px dashed #e0e0e0'
          }}>
            <Box sx={{ 
              width: 60, 
              height: 60, 
              borderRadius: '50%', 
              bgcolor: '#f5f5f5', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              mb: 2
            }}>
              <RecordVoiceOverIcon sx={{ fontSize: 28, color: '#9e9e9e' }} />
            </Box>
            <Typography variant="subtitle1" color="text.secondary" gutterBottom sx={{ fontWeight: 500, fontSize: '1rem' }}>
              {!isConnected ? 'Connecting...' : (isRecording ? 'Listening...' : 'Ready to Transcribe')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 220, lineHeight: 1.4, fontSize: '0.85rem' }}>
              {!isConnected 
                ? 'Please wait while we connect to the server'
                : (isRecording ? 'Speak clearly into your microphone' : 'Click "Start Recording" to begin')
              }
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {transcriptionSegments.map((segment) => (
              <Box
                key={segment.id}
                sx={{
                  p: 2.5,
                  bgcolor: segment.status === 'added' ? '#e8f5e8' : 'white',
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: segment.status === 'added' ? '#4caf50' : '#e0e0e0',
                  position: 'relative',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    borderColor: segment.status === 'added' ? '#4caf50' : '#2196f3'
                  }
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(segment.timestamp).toLocaleTimeString()}
                    </Typography>
                    {segment.confidence < 0.8 && (
                      <Chip 
                        label="Low Confidence" 
                        size="small" 
                        sx={{ 
                          bgcolor: '#fff3e0', 
                          color: '#f57c00',
                          fontSize: '0.7rem',
                          fontWeight: 500,
                          border: '1px solid #ffcc02'
                        }}
                      />
                    )}
                    {segment.status === 'added' && (
                      <Chip 
                        label="✓ Added" 
                        size="small" 
                        sx={{ 
                          bgcolor: '#e8f5e8',
                          color: '#2e7d32',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          border: '1px solid #4caf50'
                        }}
                      />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Tooltip title="Copy to clipboard">
                      <IconButton 
                        size="small"
                        onClick={() => handleCopyToClipboard(segment.text)}
                        sx={{ 
                          padding: 0.75,
                          bgcolor: '#f5f5f5',
                          '&:hover': {
                            bgcolor: '#e3f2fd',
                            color: '#2196f3'
                          }
                        }}
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {segment.status !== 'added' && (
                      <Tooltip title="Add to section">
                        <IconButton
                          size="small"
                          onClick={(e) => handleOpenMenu(e, segment)}
                          sx={{ 
                            padding: 0.75,
                            bgcolor: '#e3f2fd',
                            color: '#2196f3',
                            '&:hover': {
                              bgcolor: '#2196f3',
                              color: 'white'
                            }
                          }}
                        >
                          <AddCircleOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </Box>
                <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
                  {segment.text}
                </Typography>
                {segment.suggestedSection && segment.status !== 'added' && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Suggested: {segment.suggestedSection}
                    </Typography>
                  </Box>
                )}
              </Box>
            ))}
            <div ref={transcriptionEndRef} />
          </Box>
        )}
        </Box>

      {/* Add to section menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleCloseMenu}
      >
        {SECTION_MAPPINGS.map((section) => (
          <MenuItem
            key={section.key}
            onClick={() => selectedSegment && handleAddToSection(selectedSegment, section.key)}
          >
            <ListItemIcon>{section.icon}</ListItemIcon>
            <ListItemText>{section.label}</ListItemText>
          </MenuItem>
        ))}
        <Divider />
        <MenuItem
          onClick={() => selectedSegment && handleAddToSection(selectedSegment, 'new')}
        >
          <ListItemIcon><NoteAddIcon /></ListItemIcon>
          <ListItemText>Create New Section</ListItemText>
        </MenuItem>
      </Menu>
    </Paper>
  );
};

export default LiveTranscription;