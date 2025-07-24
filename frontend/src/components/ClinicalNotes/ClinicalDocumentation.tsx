import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Divider,
  Alert,
  Checkbox,
  FormControlLabel,
  LinearProgress,
  Fade,
  Collapse,
  IconButton,
  Tooltip
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import AddIcon from '@mui/icons-material/Add';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SettingsIcon from '@mui/icons-material/Settings';
import webSocketService from '../../services/websocket';
import NoteSettings, { NoteFormat } from './NoteSettings';

interface ClinicalDocumentationProps {
  encounterId: string;
  patientId: string;
  onAddToSection?: (section: string, content: string, transcriptionId?: string) => void;
}

interface Symptom {
  id: string;
  text: string;
  severity: 'high' | 'medium' | 'low';
  duration?: string;
}

interface Diagnosis {
  id: string;
  primary: string;
  code: string;
  isPrimary: boolean;
}

interface PlanItem {
  id: string;
  text: string;
  completed: boolean;
  category: 'action' | 'medication' | 'followup' | 'education';
}

const severityColors = {
  high: '#dc3545',
  medium: '#ffc107',
  low: '#28a745'
};

const ClinicalDocumentation: React.FC<ClinicalDocumentationProps> = ({ 
  encounterId, 
  patientId,
  onAddToSection 
}) => {
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionConfidence, setTranscriptionConfidence] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [noteFormat, setNoteFormat] = useState<NoteFormat>(
    (localStorage.getItem('noteFormat') as NoteFormat) || 'long'
  );
  
  // Clinical Notes State
  const [presentIllness, setPresentIllness] = useState<Symptom[]>([
    { id: '1', text: 'Dyspnea on exertion, progressively worsening', severity: 'high', duration: 'Improved after thoracentesis' },
    { id: '2', text: 'Productive cough - yellowish sputum with hemoptysis', severity: 'high', duration: 'Concerning for malignancy' },
    { id: '3', text: 'Chest pain, non-radiating', severity: 'medium' },
    { id: '4', text: 'No fever reported', severity: 'low' }
  ]);
  
  const [riskFactors, setRiskFactors] = useState<Symptom[]>([
    { id: '1', text: 'Heavy smoking history (20+ pack-years)', severity: 'high' },
    { id: '2', text: 'Age >50 (exact age pending verification)', severity: 'medium' },
    { id: '3', text: 'Occupational exposure unknown', severity: 'medium' }
  ]);
  
  const [previousInterventions, setPreviousInterventions] = useState(
    'Thoracentesis performed: Fluid removed from pleural space with temporary symptom improvement'
  );
  
  // Assessment & Plan State
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([
    { id: '1', primary: 'Suspected Primary Lung Malignancy', code: 'C78.00', isPrimary: true },
    { id: '2', primary: 'Pleural Effusion, Malignant vs. Parapneumonic', code: 'J94.8', isPrimary: false }
  ]);
  
  const [planItems, setPlanItems] = useState<PlanItem[]>([
    { id: '1', text: 'CT Chest with contrast - evaluate lesion extent', completed: true, category: 'action' },
    { id: '2', text: 'PET scan for staging if CT confirms malignancy', completed: true, category: 'action' },
    { id: '3', text: 'Pulmonology referral for bronchoscopy + biopsy', completed: false, category: 'action' },
    { id: '4', text: 'Oncology referral pending pathology results', completed: false, category: 'action' },
    { id: '5', text: 'Albuterol inhaler - 2 puffs q4h PRN for dyspnea', completed: false, category: 'medication' },
    { id: '6', text: 'Sodium chloride tabs - 1g PO BID for hyponatremia', completed: false, category: 'medication' },
    { id: '7', text: 'Smoking cessation counseling - urgent priority', completed: true, category: 'education' },
    { id: '8', text: 'Nutritional counseling for cancer prevention', completed: false, category: 'education' }
  ]);
  
  // Collapsed sections state - start collapsed to show the feature
  const [collapsedSections, setCollapsedSections] = useState({
    clinicalNotes: true,
    assessment: true,
    plan: false
  });
  
  const toggleSection = (section: keyof typeof collapsedSections) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

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
    switch (sectionType) {
      case 'present_illness':
        if (content.symptoms) {
          setPresentIllness(content.symptoms);
        }
        break;
      case 'risk_factors':
        if (content.factors) {
          setRiskFactors(content.factors);
        }
        break;
      case 'assessment':
        if (content.diagnoses) {
          setDiagnoses(content.diagnoses);
        }
        break;
      case 'plan':
        if (content.items) {
          setPlanItems(content.items);
        }
        break;
    }
  };

  const handlePlanItemToggle = (itemId: string) => {
    setPlanItems(prev => 
      prev.map(item => 
        item.id === itemId ? { ...item, completed: !item.completed } : item
      )
    );
  };

  const handleGenerateOrders = () => {
    // Generate electronic orders for checked items
    const checkedItems = planItems.filter(item => item.completed);
    console.log('Generating orders for:', checkedItems);
  };

  // Override the onAddToSection to include note format
  const handleAddToSection = (section: string, content: string, transcriptionId?: string) => {
    if (onAddToSection) {
      onAddToSection(section, content, transcriptionId);
    }
    
    // Send update via WebSocket with note format preference
    webSocketService.emit('notes:update', {
      type: 'notes:update',
      noteFormat: noteFormat,
      section: section,
      content: { text: content, action: 'append' }
    });
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
          <DescriptionIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Clinical Documentation
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Auto-transcribed
          </Typography>
          <Tooltip title="Note Format Settings">
            <IconButton
              size="small"
              onClick={() => setSettingsOpen(true)}
              sx={{ 
                color: 'text.secondary',
                '&:hover': {
                  bgcolor: 'action.hover'
                }
              }}
            >
              <SettingsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={handleGenerateOrders}
            sx={{ textTransform: 'none' }}
          >
            Generate Orders
          </Button>
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
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
              <Typography variant="body2">
                {currentTranscription}
              </Typography>
              <LinearProgress variant="indeterminate" sx={{ mt: 1 }} />
            </Box>
          </Fade>
        )}

        {/* Clinical Notes Section */}
        <Box sx={{ mb: 4 }}>
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              mb: 2,
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              p: 1,
              borderRadius: 1,
              ml: -1
            }}
            onClick={() => toggleSection('clinicalNotes')}
          >
            <IconButton size="small" sx={{ mr: 1 }}>
              {collapsedSections.clinicalNotes ? <ExpandMoreIcon /> : <ExpandLessIcon />}
            </IconButton>
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 600,
                color: 'text.primary'
              }}
            >
              Clinical Notes & History
            </Typography>
          </Box>
          
          <Collapse in={!collapsedSections.clinicalNotes}>

          {/* Present Illness */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                PRESENT ILLNESS
              </Typography>
              <Chip label="Duration: >1 month" size="small" color="error" />
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {presentIllness.map((symptom) => (
                <Box key={symptom.id} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Box
                    sx={{
                      width: 4,
                      height: 16,
                      bgcolor: severityColors[symptom.severity],
                      borderRadius: 1,
                      flexShrink: 0,
                      mt: 0.25
                    }}
                  />
                  <Box>
                    <Typography variant="body2">{symptom.text}</Typography>
                    {symptom.duration && (
                      <Typography variant="caption" color="text.secondary">
                        {symptom.duration}
                      </Typography>
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>

          {/* Risk Factors */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              RISK FACTORS
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {riskFactors.map((factor) => (
                <Box key={factor.id} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Box
                    sx={{
                      width: 4,
                      height: 16,
                      bgcolor: severityColors[factor.severity],
                      borderRadius: 1,
                      flexShrink: 0,
                      mt: 0.25
                    }}
                  />
                  <Typography variant="body2">{factor.text}</Typography>
                </Box>
              ))}
            </Box>
          </Box>

          {/* Previous Interventions */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              PREVIOUS INTERVENTIONS
            </Typography>
            <Alert 
              severity="info" 
              sx={{ 
                bgcolor: '#d1ecf1',
                color: '#004085',
                '& .MuiAlert-icon': { display: 'none' }
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {previousInterventions}
              </Typography>
            </Alert>
          </Box>
          </Collapse>
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Assessment & Plan Section */}
        <Box>
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              mb: 2,
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              p: 1,
              borderRadius: 1,
              ml: -1
            }}
            onClick={() => toggleSection('assessment')}
          >
            <IconButton size="small" sx={{ mr: 1 }}>
              {collapsedSections.assessment ? <ExpandMoreIcon /> : <ExpandLessIcon />}
            </IconButton>
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 600,
                color: 'text.primary'
              }}
            >
              Assessment & Plan
            </Typography>
          </Box>
          
          <Collapse in={!collapsedSections.assessment}>

          {/* Working Diagnosis */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              WORKING DIAGNOSIS
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {diagnoses.map((diagnosis) => (
                <Alert
                  key={diagnosis.id}
                  severity={diagnosis.isPrimary ? 'warning' : 'info'}
                  sx={{
                    bgcolor: diagnosis.isPrimary ? '#fff3cd' : '#e2e3e5',
                    color: diagnosis.isPrimary ? '#856404' : '#383d41',
                    border: 1,
                    borderColor: diagnosis.isPrimary ? '#ffeaa7' : '#d6d8db',
                    '& .MuiAlert-icon': { display: 'none' }
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {diagnosis.id}. {diagnosis.primary}
                  </Typography>
                  <Typography variant="caption">
                    ICD-10: {diagnosis.code}
                  </Typography>
                </Alert>
              ))}
            </Box>
          </Box>

          {/* Plan Items */}
          <Box>
            {/* Immediate Actions */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              IMMEDIATE ACTIONS
            </Typography>
            <Box sx={{ mb: 2 }}>
              {planItems
                .filter(item => item.category === 'action')
                .map(item => (
                  <FormControlLabel
                    key={item.id}
                    control={
                      <Checkbox
                        size="small"
                        checked={item.completed}
                        onChange={() => handlePlanItemToggle(item.id)}
                      />
                    }
                    label={<Typography variant="body2">{item.text}</Typography>}
                    sx={{ display: 'flex', mb: 0.5 }}
                  />
                ))}
            </Box>

            {/* Medications */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              MEDICATIONS
            </Typography>
            <Box sx={{ mb: 2 }}>
              {planItems
                .filter(item => item.category === 'medication')
                .map(item => (
                  <Alert
                    key={item.id}
                    severity="info"
                    sx={{
                      bgcolor: '#e7f3ff',
                      color: '#004085',
                      border: 1,
                      borderColor: '#b8daff',
                      mb: 1,
                      '& .MuiAlert-icon': { display: 'none' }
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {item.text.split(' - ')[0]}
                    </Typography>
                    <Typography variant="caption">
                      {item.text.split(' - ')[1]}
                    </Typography>
                  </Alert>
                ))}
            </Box>

            {/* Follow-up */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              FOLLOW-UP
            </Typography>
            <Alert 
              severity="warning"
              sx={{
                bgcolor: '#fff3cd',
                color: '#856404',
                border: 1,
                borderColor: '#ffeaa7',
                mb: 2,
                '& .MuiAlert-icon': { display: 'none' }
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Next Visit: 10 days (sooner if symptoms worsen)
              </Typography>
              <Typography variant="body2">
                Purpose: Review imaging, discuss biopsy results, initiate treatment plan
              </Typography>
              <Typography variant="body2">
                Instructions: Return to ED if severe dyspnea, chest pain, or hemoptysis worsens
              </Typography>
            </Alert>

            {/* Patient Education */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', mb: 1 }}>
              PATIENT EDUCATION
            </Typography>
            <Box>
              {planItems
                .filter(item => item.category === 'education')
                .map(item => (
                  <FormControlLabel
                    key={item.id}
                    control={
                      <Checkbox
                        size="small"
                        checked={item.completed}
                        onChange={() => handlePlanItemToggle(item.id)}
                      />
                    }
                    label={<Typography variant="body2">{item.text}</Typography>}
                    sx={{ display: 'flex', mb: 0.5 }}
                  />
                ))}
            </Box>
          </Box>
          </Collapse>
        </Box>
      </Box>
      
      {/* Note Settings Dialog */}
      <NoteSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        noteFormat={noteFormat}
        onFormatChange={(format) => {
          setNoteFormat(format);
          // Store preference in localStorage
          localStorage.setItem('noteFormat', format);
          // Notify WebSocket service about format change
          webSocketService.emit('settings:update', {
            type: 'settings:update',
            noteFormat: format
          });
        }}
      />
    </Paper>
  );
};

export default ClinicalDocumentation;