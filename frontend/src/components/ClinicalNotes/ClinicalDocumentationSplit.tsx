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
  Tooltip,
  Grid
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import AddIcon from '@mui/icons-material/Add';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SettingsIcon from '@mui/icons-material/Settings';
import AssignmentIcon from '@mui/icons-material/Assignment';
import webSocketService from '../../services/websocket';
import NoteSettings, { NoteFormat } from './NoteSettings';

interface ClinicalDocumentationSplitProps {
  encounterId: string;
  patientId: string;
  onAddToSection?: (section: string, content: string, transcriptionId?: string) => void;
  prefilledSections?: any;
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

const ClinicalDocumentationSplit: React.FC<ClinicalDocumentationSplitProps> = ({ 
  encounterId, 
  patientId,
  onAddToSection,
  prefilledSections 
}) => {
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionConfidence, setTranscriptionConfidence] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [noteFormat, setNoteFormat] = useState<NoteFormat>(
    (localStorage.getItem('noteFormat') as NoteFormat) || 'long'
  );
  
  // Format-specific clinical data
  const getFormattedPresentIllness = (): Symptom[] => {
    if (noteFormat === 'long') {
      return [
        { id: '1', text: 'Patient presents with progressive exertional dyspnea over the past 3 months, initially occurring with moderate activity but now precipitated by minimal exertion. Symptoms demonstrate marked improvement following recent therapeutic thoracentesis, suggesting significant pleural component to respiratory compromise.', severity: 'high' as const, duration: 'Progressive over 3 months' },
        { id: '2', text: 'Productive cough with yellowish-green mucopurulent sputum, accompanied by intermittent hemoptysis (approximately 5-10ml of bright red blood per episode). The presence of blood-tinged sputum raises concern for underlying malignancy or significant bronchial irritation.', severity: 'high' as const, duration: 'Hemoptysis x 2 weeks' },
        { id: '3', text: 'Patient reports pleuritic chest pain localized to the right hemithorax, characterized as sharp and exacerbated by deep inspiration. Pain does not radiate to other regions and is not associated with diaphoresis or nausea.', severity: 'medium' as const },
        { id: '4', text: 'Denies constitutional symptoms including fever, chills, or night sweats. No significant unintentional weight loss reported, though appetite has been diminished secondary to dyspnea.', severity: 'low' as const }
      ];
    } else if (noteFormat === 'short') {
      return [
        { id: '1', text: 'Progressive DOE x3 months, improved post-thoracentesis', severity: 'high' as const, duration: '3 months' },
        { id: '2', text: 'Productive cough with hemoptysis, yellow-green sputum', severity: 'high' as const, duration: '2 weeks' },
        { id: '3', text: 'Right-sided pleuritic chest pain, non-radiating', severity: 'medium' as const },
        { id: '4', text: 'Afebrile, no constitutional symptoms', severity: 'low' as const }
      ];
    } else {
      return [
        { id: '1', text: '• DOE: Progressive x3mo\n• Improved post-thoracentesis\n• Now with minimal exertion', severity: 'high' as const, duration: '3 months' },
        { id: '2', text: '• Productive cough\n• Yellow-green sputum\n• Hemoptysis: 5-10ml bright red blood', severity: 'high' as const, duration: '2 weeks' },
        { id: '3', text: '• Right pleuritic CP\n• Sharp quality\n• Worse with inspiration', severity: 'medium' as const },
        { id: '4', text: '• No fever/chills\n• No night sweats\n• Appetite ↓ 2° to dyspnea', severity: 'low' as const }
      ];
    }
  };

  const getFormattedRiskFactors = (): Symptom[] => {
    if (noteFormat === 'long') {
      return [
        { id: '1', text: 'Significant tobacco use history with 40 pack-year smoking history (1 PPD x 40 years). Patient continues to smoke despite respiratory symptoms, representing major modifiable risk factor for pulmonary malignancy and COPD exacerbation.', severity: 'high' as const },
        { id: '2', text: 'Advanced age (68 years old) places patient in high-risk demographic for primary lung malignancy. Age-related immune senescence may contribute to increased susceptibility to malignant transformation.', severity: 'medium' as const },
        { id: '3', text: 'Potential occupational asbestos exposure during 20-year career in construction industry. No formal industrial hygiene monitoring documented. Additional exposure history pending comprehensive occupational assessment.', severity: 'medium' as const }
      ];
    } else if (noteFormat === 'short') {
      return [
        { id: '1', text: '40 pack-year smoking history, current smoker', severity: 'high' as const },
        { id: '2', text: 'Age 68 years, high-risk demographic', severity: 'medium' as const },
        { id: '3', text: 'Possible asbestos exposure in construction', severity: 'medium' as const }
      ];
    } else {
      return [
        { id: '1', text: '• Tobacco: 40 pack-years\n• Current smoker\n• Major risk factor', severity: 'high' as const },
        { id: '2', text: '• Age: 68 years\n• ↑ Risk for malignancy', severity: 'medium' as const },
        { id: '3', text: '• Construction work x20y\n• Possible asbestos\n• No monitoring documented', severity: 'medium' as const }
      ];
    }
  };

  const getFormattedPreviousInterventions = () => {
    if (noteFormat === 'long') {
      return 'Patient underwent therapeutic thoracentesis 5 days prior to current evaluation with removal of 1.2L serosanguineous fluid from right pleural space. Procedure was performed without complication, and patient experienced significant symptomatic improvement with reduced dyspnea and improved exercise tolerance. Pleural fluid analysis revealed: pH 7.35, LDH 580 U/L, protein 4.2 g/dL, glucose 45 mg/dL. Cytology pending at time of encounter.';
    } else if (noteFormat === 'short') {
      return 'Thoracentesis 5 days ago: 1.2L serosanguineous fluid removed. Symptomatic improvement noted. Fluid: pH 7.35, LDH 580, protein 4.2, glucose 45. Cytology pending.';
    } else {
      return '• Thoracentesis (5 days ago)\n• 1.2L serosanguineous fluid\n• pH: 7.35, LDH: 580\n• Protein: 4.2, Glucose: 45\n• Cytology: Pending';
    }
  };

  // Clinical Notes State
  const [presentIllness, setPresentIllness] = useState<Symptom[]>(getFormattedPresentIllness());
  
  const [riskFactors, setRiskFactors] = useState<Symptom[]>(getFormattedRiskFactors());
  
  const [previousInterventions, setPreviousInterventions] = useState(getFormattedPreviousInterventions());
  
  const getFormattedDiagnoses = (): Diagnosis[] => {
    if (noteFormat === 'long') {
      return [
        { id: '1', primary: 'Suspected primary bronchogenic carcinoma with secondary malignant pleural effusion, pending histopathological confirmation', code: 'C78.00', isPrimary: true },
        { id: '2', primary: 'Large right-sided pleural effusion, likely malignant etiology given serosanguineous nature and exudative characteristics', code: 'J94.8', isPrimary: false }
      ];
    } else if (noteFormat === 'short') {
      return [
        { id: '1', primary: 'Suspected primary lung CA with malignant effusion', code: 'C78.00', isPrimary: true },
        { id: '2', primary: 'Right pleural effusion, likely malignant', code: 'J94.8', isPrimary: false }
      ];
    } else {
      return [
        { id: '1', primary: '• Primary lung CA (suspected)\n• Secondary malignant effusion\n• Pending tissue Dx', code: 'C78.00', isPrimary: true },
        { id: '2', primary: '• Right pleural effusion\n• Exudative, serosanguineous\n• Likely malignant', code: 'J94.8', isPrimary: false }
      ];
    }
  };

  const getFormattedPlanItems = (): PlanItem[] => {
    if (noteFormat === 'long') {
      return [
        { id: '1', text: 'High-resolution computed tomography of chest with IV contrast to evaluate extent of pulmonary parenchymal involvement, mediastinal lymphadenopathy, and exclude pulmonary embolism', completed: true, category: 'action' as const },
        { id: '2', text: 'Positron emission tomography with CT correlation for comprehensive staging evaluation if malignancy confirmed on tissue diagnosis', completed: true, category: 'action' as const },
        { id: '3', text: 'Urgent pulmonology consultation for fiber-optic bronchoscopy with endobronchial ultrasound-guided transbronchial needle aspiration of suspicious lesions', completed: false, category: 'action' as const },
        { id: '4', text: 'Oncology referral for multidisciplinary treatment planning pending histopathological confirmation and molecular profiling results', completed: false, category: 'action' as const },
        { id: '5', text: 'Albuterol sulfate HFA inhaler 90mcg/actuation: Inhale 2 puffs every 4 hours as needed for dyspnea or bronchospasm', completed: false, category: 'medication' as const },
        { id: '6', text: 'Sodium chloride tablets 1 gram orally twice daily for correction of mild hyponatremia (serum Na 132 mEq/L)', completed: false, category: 'medication' as const },
        { id: '7', text: 'Comprehensive smoking cessation counseling with nicotine replacement therapy initiation - critical for treatment optimization', completed: true, category: 'education' as const },
        { id: '8', text: 'Nutritional assessment and counseling to address cancer-related cachexia risk and optimize performance status', completed: false, category: 'education' as const }
      ];
    } else if (noteFormat === 'short') {
      return [
        { id: '1', text: 'CT chest w/ contrast - evaluate extent of disease', completed: true, category: 'action' as const },
        { id: '2', text: 'PET scan for staging if CA confirmed', completed: true, category: 'action' as const },
        { id: '3', text: 'Pulm consult for bronch + EBUS-TBNA', completed: false, category: 'action' as const },
        { id: '4', text: 'Onc referral pending path results', completed: false, category: 'action' as const },
        { id: '5', text: 'Albuterol HFA 2 puffs q4h PRN', completed: false, category: 'medication' as const },
        { id: '6', text: 'NaCl 1g PO BID for Na 132', completed: false, category: 'medication' as const },
        { id: '7', text: 'Smoking cessation + NRT', completed: true, category: 'education' as const },
        { id: '8', text: 'Nutrition consult for cachexia prevention', completed: false, category: 'education' as const }
      ];
    } else {
      return [
        { id: '1', text: '• CT chest w/ contrast\n• Evaluate parenchyma\n• R/O PE', completed: true, category: 'action' as const },
        { id: '2', text: '• PET/CT for staging\n• If tissue Dx positive', completed: true, category: 'action' as const },
        { id: '3', text: '• Pulm consult URGENT\n• Bronch + EBUS-TBNA', completed: false, category: 'action' as const },
        { id: '4', text: '• Onc referral\n• Pending path/molecular', completed: false, category: 'action' as const },
        { id: '5', text: '• Albuterol HFA 90mcg\n• 2 puffs q4h PRN', completed: false, category: 'medication' as const },
        { id: '6', text: '• NaCl 1g PO BID\n• For Na 132 mEq/L', completed: false, category: 'medication' as const },
        { id: '7', text: '• Smoking cessation\n• Start NRT\n• URGENT', completed: true, category: 'education' as const },
        { id: '8', text: '• Nutrition assessment\n• Prevent cachexia', completed: false, category: 'education' as const }
      ];
    }
  };

  // Assessment & Plan State
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>(getFormattedDiagnoses());
  
  const [planItems, setPlanItems] = useState<PlanItem[]>(getFormattedPlanItems());
  
  // Collapsed sections state
  const [collapsedSections, setCollapsedSections] = useState({
    presentIllness: false,
    riskFactors: false,
    previousInterventions: false,
    diagnosis: false,
    plan: false
  });
  
  const toggleSection = (section: keyof typeof collapsedSections) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Update data when note format changes
  useEffect(() => {
    setPresentIllness(getFormattedPresentIllness());
    setRiskFactors(getFormattedRiskFactors());
    setPreviousInterventions(getFormattedPreviousInterventions());
    setDiagnoses(getFormattedDiagnoses());
    setPlanItems(getFormattedPlanItems());
  }, [noteFormat]);

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

      <Box sx={{ flex: 1, overflow: 'hidden', p: 2, display: 'flex', flexDirection: 'column' }}>
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

        {/* Two Column Layout */}
        <Grid container spacing={2} sx={{ flex: 1, height: '100%', minHeight: 0 }}>
          {/* Left Column: Clinical Notes & History */}
          <Grid item xs={12} md={6} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Paper elevation={3} sx={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column',
              overflow: 'hidden',
              border: '1px solid',
              borderColor: 'divider'
            }}>
              {/* Fixed Header */}
              <Box sx={{ 
                p: 2, 
                borderBottom: 2, 
                borderColor: 'primary.main',
                bgcolor: '#f5f7fa',
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}>
                <DescriptionIcon sx={{ color: 'primary.main', fontSize: 24 }} />
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'primary.main',
                    fontSize: '1.1rem'
                  }}
                >
                  Clinical Notes & History
                </Typography>
              </Box>

              {/* Scrollable Content */}
              <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                {/* Present Illness */}
                <Box sx={{ mb: 3 }}>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    p: 0.5,
                    borderRadius: 1,
                    ml: -0.5
                  }}
                  onClick={() => toggleSection('presentIllness')}
                >
                  <IconButton size="small" sx={{ mr: 0.5 }}>
                    {collapsedSections.presentIllness ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flex: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                      PRESENT ILLNESS
                    </Typography>
                    <Chip label="Duration: >1 month" size="small" color="error" />
                  </Box>
                </Box>
                
                <Collapse in={!collapsedSections.presentIllness}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
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
                </Collapse>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Risk Factors */}
              <Box sx={{ mb: 3 }}>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    p: 0.5,
                    borderRadius: 1,
                    ml: -0.5
                  }}
                  onClick={() => toggleSection('riskFactors')}
                >
                  <IconButton size="small" sx={{ mr: 0.5 }}>
                    {collapsedSections.riskFactors ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    RISK FACTORS
                  </Typography>
                </Box>
                
                <Collapse in={!collapsedSections.riskFactors}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
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
                </Collapse>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Previous Interventions */}
              <Box sx={{ mb: 3 }}>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    p: 0.5,
                    borderRadius: 1,
                    ml: -0.5
                  }}
                  onClick={() => toggleSection('previousInterventions')}
                >
                  <IconButton size="small" sx={{ mr: 0.5 }}>
                    {collapsedSections.previousInterventions ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    PREVIOUS INTERVENTIONS
                  </Typography>
                </Box>
                
                <Collapse in={!collapsedSections.previousInterventions}>
                  <Alert 
                    severity="info" 
                    sx={{ 
                      mt: 1,
                      bgcolor: '#d1ecf1',
                      color: '#004085',
                      '& .MuiAlert-icon': { display: 'none' }
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {previousInterventions}
                    </Typography>
                  </Alert>
                </Collapse>
              </Box>
              </Box>
            </Paper>
          </Grid>

          {/* Right Column: Assessment & Plan */}
          <Grid item xs={12} md={6} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Paper elevation={3} sx={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column',
              overflow: 'hidden',
              border: '1px solid',
              borderColor: 'divider'
            }}>
              {/* Fixed Header */}
              <Box sx={{ 
                p: 2, 
                borderBottom: 2, 
                borderColor: 'primary.main',
                bgcolor: '#f5f7fa',
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}>
                <AssignmentIcon sx={{ color: 'primary.main', fontSize: 24 }} />
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'primary.main',
                    fontSize: '1.1rem'
                  }}
                >
                  Assessment & Plan
                </Typography>
              </Box>

              {/* Scrollable Content */}
              <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>

              {/* Working Diagnosis */}
              <Box sx={{ mb: 3 }}>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    p: 0.5,
                    borderRadius: 1,
                    ml: -0.5
                  }}
                  onClick={() => toggleSection('diagnosis')}
                >
                  <IconButton size="small" sx={{ mr: 0.5 }}>
                    {collapsedSections.diagnosis ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    WORKING DIAGNOSIS
                  </Typography>
                </Box>
                
                <Collapse in={!collapsedSections.diagnosis}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
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
                </Collapse>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Plan Items */}
              <Box>
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    p: 0.5,
                    borderRadius: 1,
                    ml: -0.5,
                    mb: 1
                  }}
                  onClick={() => toggleSection('plan')}
                >
                  <IconButton size="small" sx={{ mr: 0.5 }}>
                    {collapsedSections.plan ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                  </IconButton>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                    TREATMENT PLAN
                  </Typography>
                </Box>
                
                <Collapse in={!collapsedSections.plan}>
                  {/* Immediate Actions */}
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 1 }}>
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
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 1 }}>
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
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 1 }}>
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
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 1 }}>
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
                </Collapse>
              </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
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

export default ClinicalDocumentationSplit;