import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Grid, 
  Alert, 
  Button, 
  CircularProgress, 
  Backdrop, 
  Typography, 
  Paper,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Chip,
  Stack,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormControlLabel
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PatientHeader from '../components/ClinicalNotes/PatientHeader';
import ClinicalDocumentationClean from '../components/ClinicalNotes/ClinicalDocumentationClean';
import RealtimeTranscriptionWrapper from '../components/ClinicalNotes/RealtimeTranscriptionWrapper';
import ActionBar from '../components/ClinicalNotes/ActionBar';
import webSocketService from '../services/websocket';
import { usePatient } from '../contexts/PatientContext';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MicIcon from '@mui/icons-material/Mic';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AssessmentIcon from '@mui/icons-material/Assessment';
import NotesIcon from '@mui/icons-material/Notes';
import SaveIcon from '@mui/icons-material/Save';
import PrintIcon from '@mui/icons-material/Print';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

interface PatientData {
  id: string;
  ehr_id?: string;
  first_name: string;
  last_name: string;
  mrn: string;
  date_of_birth: string;
  gender: string;
  age?: number;
  smoking_history?: string;
  allergies?: string;
  phone?: string;
  email?: string;
  // Additional clinical context from recent encounters
  recent_diagnosis?: string[];
  recent_chief_complaint?: string;
  recent_clinical_notes?: string;
}

interface EncounterData {
  id: string;
  patient_id: string;
  chief_complaint: string;
  provider_name: string;
  referring_physician?: string;
  encounter_date: string;
  encounter_type: string;
  status: string;
  risk_factors?: string[];
  vitals?: any;
  diagnosis?: string[];
  notes?: string;
}

function ClinicalNotesPage() {
  const navigate = useNavigate();
  const { selectedPatient, selectedEncounter, recentVitals } = usePatient();

  // Use patient data from context or fall back to mock data
  const patient: PatientData = selectedPatient ? {
    id: selectedPatient.ehr_id || '123',
    ehr_id: selectedPatient.ehr_id,
    first_name: selectedPatient.first_name,
    last_name: selectedPatient.last_name,
    mrn: selectedPatient.mrn,
    date_of_birth: selectedPatient.date_of_birth,
    gender: selectedPatient.gender,
    age: selectedPatient.age,
    smoking_history: selectedPatient.smoking_history,
    allergies: selectedPatient.allergies,
    phone: selectedPatient.phone,
    email: selectedPatient.email,
    recent_diagnosis: selectedPatient.recent_diagnosis,
    recent_chief_complaint: selectedPatient.recent_chief_complaint,
    recent_clinical_notes: selectedPatient.recent_clinical_notes
  } : {
    id: '123',
    first_name: 'John',
    last_name: 'Doe',
    mrn: 'MRN001234',
    date_of_birth: '1978-05-15',
    gender: 'Male',
    age: 45,
    smoking_history: '20+ pack-years',
    allergies: 'NKDA',
    ehr_id: '123'
  };

  const encounter: EncounterData = selectedEncounter ? {
    id: selectedEncounter.id,
    patient_id: selectedEncounter.patient_id,
    chief_complaint: selectedEncounter.chief_complaint || 'General consultation',
    provider_name: selectedEncounter.provider_name,
    referring_physician: selectedEncounter.provider_name,
    encounter_date: selectedEncounter.encounter_date,
    encounter_type: selectedEncounter.encounter_type,
    status: selectedEncounter.status,
    risk_factors: patient.smoking_history ? ['smoker'] : [],
    vitals: selectedEncounter.vitals,
    diagnosis: selectedEncounter.diagnosis,
    notes: selectedEncounter.notes
  } : {
    id: 'enc-001',
    patient_id: patient.ehr_id || patient.id || '123',
    chief_complaint: 'General consultation',
    provider_name: 'Dr. Smith',
    referring_physician: 'Dr. Smith',
    encounter_date: new Date().toISOString(),
    encounter_type: 'Outpatient',
    status: 'In Progress',
    risk_factors: patient.smoking_history ? ['smoker'] : []
  };

  const [vitals, setVitals] = useState(recentVitals || {
    blood_pressure: '120/80',
    heart_rate: 72,
    respiratory_rate: 16,
    temperature: 98.6,
    oxygen_saturation: 98,
    pain_level: '0/10'
  });

  const [isDraftSaved, setIsDraftSaved] = useState(true);
  const [lastSaveTime, setLastSaveTime] = useState(new Date());
  const [transcriptionLinks, setTranscriptionLinks] = useState<Map<string, string>>(new Map());
  
  // New state for agent-based system
  const [isLoadingEHR, setIsLoadingEHR] = useState(false);
  const [clinicalNotesStarted, setClinicalNotesStarted] = useState(false);
  const [activeAgents, setActiveAgents] = useState<any[]>([]);
  const [currentSection, setCurrentSection] = useState<string | null>(null);
  const [sections, setSections] = useState<any>({});
  const [showSummaryReview, setShowSummaryReview] = useState(false);

  // Define this function early so it can be used throughout the component
  const processClinicalNotesPrefill = (data: any) => {
    console.log('Clinical notes prefill received:', data);
    setIsLoadingEHR(false);
    setClinicalNotesStarted(true);
    
    if (data.data) {
      // Extract sections from the prefill data
      const prefillSections = data.data.sections || {};
      
      // Ensure all section values are strings (not objects or arrays)
      const sanitizedSections = Object.keys(prefillSections).reduce((acc, key) => {
        const value = prefillSections[key];
        
        // Handle different types of values
        if (typeof value === 'object' && value !== null) {
          if (Array.isArray(value)) {
            acc[key] = value.join(', ');
          } else {
            // For objects, convert to readable format
            acc[key] = JSON.stringify(value, null, 2);
          }
        } else {
          acc[key] = value || '';
        }
        
        return acc;
      }, {} as Record<string, string>);
      
      setSections(sanitizedSections);
      
      // Handle vitals separately if they exist
      if (prefillSections.vital_signs && typeof prefillSections.vital_signs === 'object') {
        setVitals(prefillSections.vital_signs);
      }
      
      // Store the full prefill data for reference
      console.log('Processed sections:', sanitizedSections);
      console.log('Full prefill data:', data.data);
    }
  };

  useEffect(() => {
    // Connect WebSocket
    const connectWebSocket = async () => {
      const token = await (window as any).Clerk?.session?.getToken();
      if (token && !webSocketService.isConnected()) {
        try {
          await webSocketService.connect(token);
          console.log('WebSocket connected for clinical notes');
        } catch (error) {
          console.error('Failed to connect WebSocket:', error);
        }
      }
    };
    
    connectWebSocket();

    // Listen for real-time vital updates
    const handleVitalUpdate = (data: any) => {
      if (data.type === 'vitals:update') {
        setVitals((prevVitals: any) => ({ ...prevVitals, ...data.vitals }));
      }
    };

    // Listen for clinical notes prefill
    const handleClinicalNotesPrefill = processClinicalNotesPrefill;


    // Listen for section updates from agents
    const handleSectionUpdate = (data: any) => {
      setSections((prev: any) => ({
        ...prev,
        [data.section]: data.content
      }));
      
      // Update active agents
      setActiveAgents((prev) => {
        const existing = prev.find(a => a.section === data.section);
        if (existing) {
          return prev.map(a => 
            a.section === data.section 
              ? { ...a, status: 'completed', confidence: data.confidence }
              : a
          );
        }
        return [...prev, { 
          section: data.section, 
          status: 'completed', 
          confidence: data.confidence 
        }];
      });
      
      setCurrentSection(data.section);
    };

    webSocketService.on('vitals:update', handleVitalUpdate);
    webSocketService.on('clinical_notes:prefill', handleClinicalNotesPrefill);
    webSocketService.on('section:update', handleSectionUpdate);

    // Auto-save draft every 5 minutes
    const autoSaveInterval = setInterval(() => {
      handleSaveDraft();
    }, 300000);

    return () => {
      webSocketService.off('vitals:update', handleVitalUpdate);
      webSocketService.off('clinical_notes:prefill', handleClinicalNotesPrefill);
      webSocketService.off('section:update', handleSectionUpdate);
      clearInterval(autoSaveInterval);
      
      // Disconnect WebSocket when leaving page
      if (webSocketService.isConnected()) {
        webSocketService.disconnect();
        console.log('WebSocket disconnected from clinical notes');
      }
    };
  }, []);

  const handleSaveDraft = async () => {
    // Save draft logic
    setLastSaveTime(new Date());
    setIsDraftSaved(true);
  };

  const handleSignEncounter = async () => {
    // Sign and close encounter logic
    console.log('Signing encounter...');
  };

  const handleShowSummaryReview = () => {
    // Switch to summary tab for review
    setShowSummaryReview(true);
    // You could also trigger tab switch in ClinicalDocumentationSplit if needed
  };

  const handleStartClinicalNotes = async () => {
    if (!patient?.id) {
      console.error('No patient selected');
      return;
    }
    
    setIsLoadingEHR(true);
    
    // If we have comprehensive patient data from context, use it immediately
    if (selectedPatient && selectedPatient.medical_summary) {
      const ehrData = {
        chief_complaint: selectedPatient.recent_chief_complaint || '',
        history_present_illness: selectedPatient.history_present_illness ? 
          (selectedPatient.history_present_illness.long_version || selectedPatient.history_present_illness.short_version || '') : '',
        assessment_and_plan: {
          diagnoses: selectedPatient.active_problems || [],
          plan: selectedPatient.active_problems?.map((p: any) => p.plan).join('\n') || ''
        },
        medications: selectedPatient.medications?.map((m: any) => 
          typeof m === 'string' ? m : `${m.name || m} - ${m.dosage || ''}`
        ).join('\n') || '',
        allergies: Array.isArray(selectedPatient.allergies) ? 
          selectedPatient.allergies.map((a: any) => typeof a === 'string' ? a : a.substance).join(', ') : 
          (selectedPatient.allergies || 'NKDA'),
        past_medical_history: selectedPatient.past_medical_history?.join(', ') || '',
        social_history: selectedPatient.social_history || '',
        family_history: selectedPatient.family_history?.join(', ') || '',
        vital_signs: selectedPatient.vital_signs || {},
        physical_exam: selectedPatient.physical_examination || {},
        lab_results: selectedPatient.lab_results || [],
        imaging_results: selectedPatient.imaging_results || []
      };
      
      // Simulate the prefill event with real EHR data
      processClinicalNotesPrefill({
        type: 'clinical_notes:prefill',
        data: {
          sections: ehrData,
          patient_data: selectedPatient
        }
      });
    }
    
    // Call backend to fetch full EHR data for the patient
    webSocketService.emit('clinical_notes:start', {
      type: 'clinical_notes:start',
      patient_id: patient.ehr_id || patient.id,
      encounter_type: selectedEncounter?.encounter_type || 'routine_visit'
    });
    
    console.log('Requesting clinical notes data from backend for patient:', patient.ehr_id || patient.id);
  };

  const handleAddToSection = (section: string, content: string, transcriptionId?: string) => {
    // This function will be called when user adds transcription to a section
    console.log(`Adding to section ${section}:`, content);
    
    // Store link between note text and transcription
    if (transcriptionId) {
      setTranscriptionLinks(prev => new Map(prev).set(`${section}-${Date.now()}`, transcriptionId));
    }
    
    // Send update via WebSocket
    webSocketService.emit('notes:update', {
      type: 'notes:update',
      section: section,
      content: { text: content, action: 'append' }
    });
  };


  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      minHeight: '100vh',
      height: '100vh',
      bgcolor: '#f8f9fa',
      overflow: 'hidden'
    }}>
      {/* Patient Header - Full Width */}
      <Box sx={{ px: 2, py: 1, bgcolor: '#ffffff', borderBottom: '1px solid #e0e0e0' }}>
        <PatientHeader 
          patient={patient} 
          encounter={encounter}
          vitals={vitals}
          onBack={() => navigate('/patient-records')}
        />
      </Box>
      
      {/* Main Content Grid - Three Column Layout */}
      <Box sx={{ 
        flex: 1, 
        display: 'flex',
        overflow: 'hidden',
        bgcolor: '#f8f9fa',
        minHeight: 0  // Important for flex child to shrink
      }}>
        {!clinicalNotesStarted ? (
          /* Start Clinical Notes Screen */
          <Box sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Box sx={{
              textAlign: 'center',
              maxWidth: 600
            }}>
              <Button
                variant="contained"
                size="large"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartClinicalNotes}
                disabled={isLoadingEHR}
                sx={{
                  py: 2,
                  px: 4,
                  fontSize: '1.2rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)'
                  }
                }}
              >
                Start Clinical Notes
              </Button>
            </Box>
          </Box>
        ) : (
          <>
            {/* Left Panel: Live Transcription */}
            <Box sx={{ 
              width: 320,
              bgcolor: '#6366f1',
              color: 'white',
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}>
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1, 
                mb: 2,
                pb: 1,
                borderBottom: '1px solid rgba(255,255,255,0.2)'
              }}>
                <MicIcon />
                <Typography variant="h6" fontWeight={600}>
                  Live Transcription
                </Typography>
              </Box>
              
              <Box sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                gap: 2
              }}>
                <Box sx={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  border: '3px solid rgba(255,255,255,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <MicIcon sx={{ fontSize: 40, opacity: 0.7 }} />
                </Box>
                
                <Typography variant="h6" sx={{ opacity: 0.9 }}>
                  Ready to Transcribe
                </Typography>
                
                <Typography variant="body2" sx={{ opacity: 0.7, maxWidth: 200 }}>
                  Click the microphone to begin recording your conversation
                </Typography>
              </Box>
            </Box>

            {/* Center Panel: Clinical Notes & History */}
            <Box sx={{ 
              flex: 1,
              bgcolor: 'white',
              borderLeft: '1px solid #e0e0e0',
              borderRight: '1px solid #e0e0e0',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              minWidth: 0
            }}>
              <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 2,
                borderBottom: '1px solid #e0e0e0',
                bgcolor: '#f8f9fa'
              }}>
                <NotesIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Clinical Notes & History
                </Typography>
                <Box sx={{ ml: 'auto' }}>
                  <Chip label="Auto-transcribed" size="small" color="success" />
                </Box>
              </Box>

              <Box sx={{ p: 2, flex: 1, overflow: 'auto' }}>
                <Accordion expanded defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        PRESENT ILLNESS
                      </Typography>
                      <Chip label="Duration: >1 month" size="small" color="warning" />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ borderLeft: '3px solid #f44336', pl: 2 }}>
                      <Typography variant="body2" paragraph>
                        Patient presents with progressive exertional dyspnea over the past 3 
                        months, initially occurring with moderate activity but now exacerbated by 
                        minimal exertion. Symptoms demonstrate marked improvement following 
                        recent thoracentesis, suggesting significant pleural component 
                        to respiratory compromise.
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Progressive over 3 months
                      </Typography>
                    </Box>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="body2" paragraph>
                      Productive cough with yellowish-green mucopurulent sputum, 
                      accompanied by intermittent hemoptysis (approximately 5-10ml of bright 
                      red blood per episode). The presence of blood-tinged sputum raises 
                      concern for underlying malignancy or significant bronchial irritation.
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Hemoptysis × 2 weeks
                    </Typography>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="body2" paragraph>
                      Patient reports pleuritic chest pain localized to the right hemithorax, 
                      characterized as sharp and exacerbated by deep inspiration. Pain does not 
                      radiate to other regions and is not associated with diaphoresis or nausea.
                    </Typography>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="body2">
                      Denies constitutional symptoms including fever, chills, or night sweats. No 
                      significant unintentional weight loss reported, though appetite has been 
                      diminished secondary to dyspnea.
                    </Typography>
                  </AccordionDetails>
                </Accordion>
              </Box>
            </Box>

            {/* Right Panel: Assessment & Plan */}
            <Box sx={{ 
              width: 400,
              bgcolor: 'white',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}>
              <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 2,
                borderBottom: '1px solid #e0e0e0',
                bgcolor: '#f8f9fa'
              }}>
                <AssessmentIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Assessment & Plan
                </Typography>
              </Box>

              <Box sx={{ p: 2, flex: 1, overflow: 'auto' }}>
                <Accordion expanded defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      WORKING DIAGNOSIS
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ bgcolor: '#fff3cd', p: 2, borderRadius: 1, mb: 2 }}>
                      <Typography variant="body2" fontWeight={600} gutterBottom>
                        1. Suspected primary bronchogenic carcinoma with secondary 
                        malignant pleural effusion, pending histopathological confirmation
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ICD-10: C78.00
                      </Typography>
                    </Box>

                    <Box sx={{ bgcolor: '#f8f9fa', p: 2, borderRadius: 1 }}>
                      <Typography variant="body2" fontWeight={600} gutterBottom>
                        2. Large right-sided pleural effusion, likely malignant etiology given 
                        serosanguineous nature and exudative characteristics
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ICD-10: J94.8
                      </Typography>
                    </Box>
                  </AccordionDetails>
                </Accordion>

                <Accordion expanded defaultExpanded sx={{ mt: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      TREATMENT PLAN
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      IMMEDIATE ACTIONS
                    </Typography>

                    <FormControlLabel
                      control={<Checkbox defaultChecked />}
                      label={
                        <Typography variant="body2">
                          High-resolution computed tomography of chest with IV contrast to 
                          evaluate extent of pulmonary parenchymal involvement, mediastinal 
                          lymphadenopathy, and exclude pulmonary embolism
                        </Typography>
                      }
                    />

                    <FormControlLabel
                      control={<Checkbox defaultChecked />}
                      label={
                        <Typography variant="body2">
                          Positron emission tomography with CT correlation for comprehensive 
                          staging
                        </Typography>
                      }
                    />

                    <Box sx={{ mt: 2, p: 2, bgcolor: '#f0f8ff', borderRadius: 1 }}>
                      <Typography variant="caption" fontWeight={600}>
                        Stop recording
                      </Typography>
                      <Typography variant="body2">
                        malignancy confirmed on tissue diagnosis
                      </Typography>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </Box>
            </Box>
          </>
        )}
      </Box>
      
      {/* Bottom Action Bar */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        p: 2,
        bgcolor: 'white',
        borderTop: '1px solid #e0e0e0'
      }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<CheckCircleIcon />}
            onClick={handleSignEncounter}
            sx={{ bgcolor: '#2196f3' }}
          >
            Sign & Close Encounter
          </Button>
          <Button
            variant="outlined"
            startIcon={<SaveIcon />}
            onClick={handleSaveDraft}
          >
            Save Draft
          </Button>
          <Button
            variant="outlined"
            startIcon={<PrintIcon />}
          >
            Print Summary
          </Button>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
          >
            Add Addendum
          </Button>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Last saved: 2 minutes ago
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#4caf50'
            }} />
            <Typography variant="body2">
              Voice recording: Recording
            </Typography>
          </Box>
        </Box>
      </Box>
      
      {/* Loading Backdrop */}
      <Backdrop
        sx={{ 
          color: '#fff', 
          zIndex: (theme) => theme.zIndex.drawer + 1,
          flexDirection: 'column',
          gap: 2
        }}
        open={isLoadingEHR}
      >
        <CircularProgress color="inherit" size={60} />
        <Typography variant="h6">
          Loading patient data from EHR...
        </Typography>
      </Backdrop>
    </Box>
  );
}

export default ClinicalNotesPage;