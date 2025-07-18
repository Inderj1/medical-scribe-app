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
  ListItemText
} from '@mui/material';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import HistoryIcon from '@mui/icons-material/History';
import AssignmentIcon from '@mui/icons-material/Assignment';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import MedicationIcon from '@mui/icons-material/Medication';
import NoteAddIcon from '@mui/icons-material/NoteAdd';
import webSocketService from '../../services/websocket';

interface LiveTranscriptionProps {
  encounterId: string;
  onAddToSection?: (section: string, content: string) => void;
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
  const [isListening, setIsListening] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionSegments, setTranscriptionSegments] = useState<TranscriptionSegment[]>([
    // Demo transcription segments for display
    {
      id: '1',
      text: 'Patient presents with chest pain that started 3 days ago. The pain is described as sharp and intermittent, primarily on the left side.',
      timestamp: new Date(Date.now() - 300000),
      confidence: 0.95,
      status: 'pending',
      suggestedSection: 'chief_complaint'
    },
    {
      id: '2',
      text: 'Patient reports taking aspirin 81mg daily and lisinopril 10mg for hypertension. No known drug allergies.',
      timestamp: new Date(Date.now() - 240000),
      confidence: 0.92,
      status: 'added',
      suggestedSection: 'medications'
    },
    {
      id: '3',
      text: 'Blood pressure is elevated at 150/95. Heart rate is 88 beats per minute, regular rhythm. No murmurs appreciated on auscultation.',
      timestamp: new Date(Date.now() - 180000),
      confidence: 0.88,
      status: 'pending',
      suggestedSection: 'physical_exam'
    }
  ]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSegment, setSelectedSegment] = useState<TranscriptionSegment | null>(null);
  const transcriptionEndRef = useRef<null | HTMLDivElement>(null);

  useEffect(() => {
    // Listen for transcription updates
    const handleTranscriptionUpdate = (data: any) => {
      if (data.type === 'transcription:partial') {
        setCurrentTranscription(data.text);
        setIsListening(true);
      } else if (data.type === 'transcription:final') {
        // Add to segments
        const newSegment: TranscriptionSegment = {
          id: Date.now().toString(),
          text: data.text,
          timestamp: new Date(),
          confidence: data.confidence || 0.95,
          status: 'pending',
          suggestedSection: data.suggestedSection
        };
        setTranscriptionSegments(prev => [...prev, newSegment]);
        setCurrentTranscription('');
        setIsListening(false);
      }
    };

    webSocketService.on('transcription:partial', handleTranscriptionUpdate);
    webSocketService.on('transcription:final', handleTranscriptionUpdate);

    return () => {
      webSocketService.off('transcription:partial', handleTranscriptionUpdate);
      webSocketService.off('transcription:final', handleTranscriptionUpdate);
    };
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom when new segments are added
    transcriptionEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcriptionSegments]);

  const handleAddToSection = (segment: TranscriptionSegment, section: string) => {
    if (onAddToSection) {
      onAddToSection(section, segment.text);
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

  return (
    <Paper
      elevation={2}
      sx={{
        bgcolor: 'white',
        borderRadius: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}
    >
      <Box
        sx={{
          bgcolor: '#f8f9fa',
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <RecordVoiceOverIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Live Transcription
          </Typography>
          {isListening && (
            <Chip 
              label="Listening..." 
              size="small" 
              color="error" 
              sx={{ animation: 'pulse 1.5s ease-in-out infinite' }}
            />
          )}
        </Box>
        <Typography variant="caption" color="text.secondary">
          {transcriptionSegments.length} segments
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {/* Current transcription */}
        {currentTranscription && (
          <Fade in={true}>
            <Alert 
              severity="info" 
              sx={{ 
                mb: 2,
                '& .MuiAlert-message': { width: '100%' }
              }}
              icon={<CircularProgress size={20} />}
            >
              <Typography variant="body2">
                {currentTranscription}
              </Typography>
            </Alert>
          </Fade>
        )}

        {/* Transcription segments */}
        {transcriptionSegments.length === 0 ? (
          <Box sx={{ 
            textAlign: 'center', 
            py: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%'
          }}>
            <RecordVoiceOverIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 3 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Start speaking to see live transcription
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Click the microphone button in the action bar to begin recording
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {transcriptionSegments.map((segment, index) => (
              <Box
                key={segment.id}
                sx={{
                  p: 2,
                  bgcolor: getSegmentColor(segment),
                  borderRadius: 1,
                  border: 1,
                  borderColor: segment.status === 'added' ? '#c3e6cb' : 'divider',
                  position: 'relative'
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(segment.timestamp).toLocaleTimeString()}
                    </Typography>
                    {segment.confidence < 0.8 && (
                      <Chip 
                        label="Low confidence" 
                        size="small" 
                        sx={{ bgcolor: '#ffeaa7', fontSize: '0.7rem' }}
                      />
                    )}
                    {segment.status === 'added' && (
                      <Chip 
                        label="Added" 
                        size="small" 
                        color="success"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <IconButton 
                      size="small"
                      onClick={() => handleCopyToClipboard(segment.text)}
                      sx={{ padding: 0.5 }}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                    {segment.status !== 'added' && (
                      <IconButton
                        size="small"
                        onClick={(e) => handleOpenMenu(e, segment)}
                        sx={{ padding: 0.5 }}
                      >
                        <AddCircleOutlineIcon fontSize="small" />
                      </IconButton>
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