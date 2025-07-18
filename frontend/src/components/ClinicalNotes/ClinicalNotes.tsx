import React, { useEffect, useState, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  LinearProgress,
  Fade,
  IconButton,
  Tooltip,
} from '@mui/material';
import NotesIcon from '@mui/icons-material/Description';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import webSocketService from '../../services/websocket';

interface Symptom {
  text: string;
  severity: 'high' | 'medium' | 'low';
  duration?: string;
}

interface NoteSection {
  title: string;
  symptoms?: Symptom[];
  content?: string;
  items?: string[];
}

interface ClinicalNotesProps {
  encounterId: string;
}

const ClinicalNotes: React.FC<ClinicalNotesProps> = ({ encounterId }) => {
  const [sections, setSections] = useState<NoteSection[]>([
    {
      title: 'Present Illness',
      symptoms: []
    },
    {
      title: 'Risk Factors',
      items: []
    },
    {
      title: 'Previous Interventions',
      content: ''
    }
  ]);
  
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionConfidence, setTranscriptionConfidence] = useState(0);
  const transcriptionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Listen for transcription updates
    const handleTranscriptionUpdate = (data: any) => {
      if (data.type === 'transcription:partial') {
        setCurrentTranscription(data.text);
        setTranscriptionConfidence(data.confidence);
        setIsTranscribing(true);
      } else if (data.type === 'transcription:final') {
        setCurrentTranscription('');
        setIsTranscribing(false);
      }
    };

    // Listen for clinical notes updates
    const handleNotesUpdate = (data: any) => {
      if (data.type === 'notes:update') {
        updateSection(data.section, data.content);
      }
    };

    webSocketService.on('transcription:partial', handleTranscriptionUpdate);
    webSocketService.on('transcription:final', handleTranscriptionUpdate);
    webSocketService.on('notes:update', handleNotesUpdate);

    return () => {
      webSocketService.off('transcription:partial', handleTranscriptionUpdate);
      webSocketService.off('transcription:final', handleTranscriptionUpdate);
      webSocketService.off('notes:update', handleNotesUpdate);
    };
  }, []);

  const updateSection = (sectionType: string, content: any) => {
    setSections(prevSections => {
      const newSections = [...prevSections];
      
      switch (sectionType) {
        case 'history':
          const historySection = newSections.find(s => s.title === 'Present Illness');
          if (historySection && content.symptoms) {
            historySection.symptoms = content.symptoms.map((s: any) => ({
              text: s.description,
              severity: s.severity || 'medium',
              duration: s.duration
            }));
          }
          break;
          
        case 'risk_factors':
          const riskSection = newSections.find(s => s.title === 'Risk Factors');
          if (riskSection && content.factors) {
            riskSection.items = content.factors;
          }
          break;
          
        case 'interventions':
          const interventionSection = newSections.find(s => s.title === 'Previous Interventions');
          if (interventionSection && content.description) {
            interventionSection.content = content.description;
          }
          break;
      }
      
      return newSections;
    });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return '#dc3545';
      case 'medium':
        return '#ffc107';
      case 'low':
        return '#28a745';
      default:
        return '#6c757d';
    }
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, bgcolor: '#f8f9fa', borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <NotesIcon />
          <Typography variant="h6" fontWeight={600}>
            Clinical Notes & History
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isTranscribing && (
            <Chip
              icon={<FiberManualRecordIcon sx={{ color: '#dc3545 !important' }} />}
              label="Recording"
              size="small"
              color="error"
              variant="outlined"
            />
          )}
          <Typography variant="caption" color="text.secondary">
            Auto-transcribed
          </Typography>
        </Box>
      </Box>
      
      <Box sx={{ p: 2, flex: 1, overflow: 'auto' }}>
        {/* Live Transcription Display */}
        {isTranscribing && currentTranscription && (
          <Fade in={true}>
            <Box sx={{ 
              mb: 2, 
              p: 2, 
              bgcolor: '#e3f2fd', 
              borderRadius: 1,
              border: '1px solid #90caf9'
            }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="caption" fontWeight={600} color="primary">
                  Live Transcription
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Confidence: {Math.round(transcriptionConfidence * 100)}%
                </Typography>
              </Box>
              <Typography variant="body2" ref={transcriptionRef}>
                {currentTranscription}
              </Typography>
              <LinearProgress variant="indeterminate" sx={{ mt: 1 }} />
            </Box>
          </Fade>
        )}

        {/* Clinical Note Sections */}
        {sections.map((section, index) => (
          <Box key={index} sx={{ mb: 3, pb: 3, borderBottom: index < sections.length - 1 ? 1 : 0, borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                {section.title}
              </Typography>
              {section.title === 'Present Illness' && (
                <Chip label="Duration: >1 month" size="small" color="error" />
              )}
            </Box>
            
            {section.symptoms && (
              <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
                {section.symptoms.map((symptom, idx) => (
                  <Box key={idx} component="li" sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 1 }}>
                    <Box sx={{ 
                      width: 4, 
                      height: 16, 
                      bgcolor: getSeverityColor(symptom.severity),
                      borderRadius: 1,
                      flexShrink: 0,
                      mt: 0.25
                    }} />
                    <Box>
                      <Typography variant="body2">
                        {symptom.text}
                      </Typography>
                      {symptom.duration && (
                        <Typography variant="caption" color="text.secondary">
                          {symptom.duration}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
            
            {section.items && (
              <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
                {section.items.map((item, idx) => (
                  <Box key={idx} component="li" sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 1 }}>
                    <Box sx={{ 
                      width: 4, 
                      height: 16, 
                      bgcolor: '#6c757d',
                      borderRadius: 1,
                      flexShrink: 0,
                      mt: 0.25
                    }} />
                    <Typography variant="body2">{item}</Typography>
                  </Box>
                ))}
              </Box>
            )}
            
            {section.content && (
              <Box sx={{ 
                bgcolor: '#d1ecf1', 
                border: '1px solid #bee5eb', 
                borderRadius: 1, 
                p: 1.5, 
                mt: 1 
              }}>
                <Typography variant="body2">{section.content}</Typography>
              </Box>
            )}
          </Box>
        ))}
      </Box>
    </Paper>
  );
};

export default ClinicalNotes;