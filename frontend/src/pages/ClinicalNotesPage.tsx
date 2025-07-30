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
import RealtimeTranscription from '../components/ClinicalNotes/RealtimeTranscription';
import ActionBar from '../components/ClinicalNotes/ActionBar';
import { useSSE } from '../contexts/SSEContext';
import { ehrbaseAPI } from '../services/ehrbase-api';
import { useWebSpeech } from '../hooks/useWebSpeech';
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
  allergies?: string | any[];
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
  const { selectedPatient, selectedEncounter, recentVitals, setSelectedEncounter } = usePatient();
  const { subscribeToTranscription, unsubscribeFromTranscription, lastEvent, connectionStatus } = useSSE();
  
  // State and refs
  const [currentTranscriptionId, setCurrentTranscriptionId] = useState<string | null>(null);

  // Define handleEndSession function before useWebSpeech hook
  const handleEndSession = async () => {
    if (!currentTranscriptionId) {
      console.log('No active session to end');
      return;
    }

    try {
      const token = await (window as any).Clerk?.session?.getToken();
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/end`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        console.log('Session ended successfully, agents will now process the transcript');
      } else {
        console.error('Failed to end session:', response.statusText);
      }
    } catch (error) {
      console.error('Failed to end streaming session:', error);
    }
  };
  
  // Check Web Speech API support directly
  const [webSpeechSupported, setWebSpeechSupported] = useState(false);
  
  useEffect(() => {
    const checkSpeechSupport = () => {
      const supported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
      console.log('Direct Web Speech API check:', {
        SpeechRecognition: !!window.SpeechRecognition,
        webkitSpeechRecognition: !!window.webkitSpeechRecognition,
        supported
      });
      setWebSpeechSupported(supported);
    };
    
    checkSpeechSupport();
    // Check again after a delay in case it takes time to load
    setTimeout(checkSpeechSupport, 500);
  }, []);

  // Web Speech API for real-time transcription
  const { 
    isListening, 
    isSupported, 
    startListening, 
    stopListening, 
    transcript: speechTranscript,
    interimTranscript 
  } = useWebSpeech({
    continuous: true,
    interimResults: true,
    language: 'en-US',
    silenceTimeoutMs: 5000, // 5 seconds of silence ends session
    onTranscript: async (text, isFinal) => {
      if (currentTranscriptionId && isFinal) {
        // Send text chunk to backend
        try {
          const token = await (window as any).Clerk?.session?.getToken();
          await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/text`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              text,
              is_final: isFinal,
              timestamp: new Date().toISOString(),
            }),
          });
        } catch (error) {
          console.error('Failed to send text chunk:', error);
        }
      }
    },
    onSilenceTimeout: async () => {
      console.log('Speech ended due to silence, triggering clinical analysis...');
      await handleEndSession();
    },
    onEnd: async () => {
      console.log('Speech recognition ended, triggering clinical analysis...');
      await handleEndSession();
    },
  });

  // Use patient data from context
  const patient: PatientData | null = selectedPatient ? {
    id: selectedPatient.ehr_id || selectedPatient.id || '',
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
  } : null;

  const encounter: EncounterData | null = selectedEncounter ? {
    id: selectedEncounter.id,
    patient_id: selectedEncounter.patient_id,
    chief_complaint: selectedEncounter.chief_complaint || '',
    provider_name: selectedEncounter.provider_name,
    referring_physician: selectedEncounter.provider_name,
    encounter_date: selectedEncounter.encounter_date,
    encounter_type: selectedEncounter.encounter_type,
    status: selectedEncounter.status,
    risk_factors: patient?.smoking_history ? ['smoker'] : [],
    vitals: selectedEncounter.vitals,
    diagnosis: selectedEncounter.diagnosis,
    notes: selectedEncounter.notes
  } : null;

  const [vitals, setVitals] = useState(recentVitals || {});

  const [isDraftSaved, setIsDraftSaved] = useState(true);
  const [lastSaveTime, setLastSaveTime] = useState(new Date());
  const [transcriptionLinks, setTranscriptionLinks] = useState<Map<string, string>>(new Map());
  
  // New state for agent-based system
  const [isLoadingEHR, setIsLoadingEHR] = useState(false);
  const [activeAgents, setActiveAgents] = useState<any[]>([]);
  const [currentSection, setCurrentSection] = useState<string | null>(null);
  const [sections, setSections] = useState<any>({});
  const [showSummaryReview, setShowSummaryReview] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);

  // Define this function early so it can be used throughout the component
  const processClinicalNotesPrefill = (data: any) => {
    console.log('Clinical notes prefill received:', data);
    setIsLoadingEHR(false);
    
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
      console.log('Setting sections state with:', sanitizedSections);
      
      // Handle vitals separately if they exist
      if (prefillSections.vital_signs && typeof prefillSections.vital_signs === 'object') {
        setVitals(prefillSections.vital_signs);
      }
      
      // Store the full prefill data for reference
      console.log('Processed sections:', sanitizedSections);
      console.log('Full prefill data:', data.data);
      console.log('Sections state will be updated with keys:', Object.keys(sanitizedSections));
    }
  };

  useEffect(() => {
    // Handle SSE events
    if (lastEvent) {
      console.log('SSE Event received:', lastEvent);
      
      switch (lastEvent.type) {
        case 'processing_started':
          setIsLoadingEHR(false);
                break;
          
        case 'progress':
          setTranscriptionProgress(lastEvent.data.progress);
          if (lastEvent.data.message) {
            console.log('Progress update:', lastEvent.data.message);
          }
          break;
          
        case 'transcription_chunk':
          // Handle real-time transcription chunks
          console.log('Transcription chunk:', lastEvent.data);
          break;
          
        case 'section_completed':
          // Handle section completion from agents
          const { section, content, confidence } = lastEvent.data;
          setSections((prev: any) => ({
            ...prev,
            [section]: content
          }));
          
          setActiveAgents((prev) => {
            const existing = prev.find(a => a.section === section);
            if (existing) {
              return prev.map(a => 
                a.section === section 
                  ? { ...a, status: 'completed', confidence }
                  : a
              );
            }
            return [...prev, { 
              section, 
              status: 'completed', 
              confidence 
            }];
          });
          
          setCurrentSection(section);
          break;
          
        case 'completed':
          setIsLoadingEHR(false);
          setTranscriptionProgress(100);
          console.log('Transcription completed:', lastEvent.data);
          break;
          
        case 'error':
          setIsLoadingEHR(false);
          console.error('Transcription error:', lastEvent.data.error);
          break;
      }
    }
  }, [lastEvent]);

  // Load EHR data when patient is selected
  useEffect(() => {
    if (patient?.id) {
      handleStartClinicalNotes();
    }
  }, [patient?.id]);

  useEffect(() => {
    // Auto-save draft every 5 minutes
    const autoSaveInterval = setInterval(() => {
      handleSaveDraft();
    }, 300000);

    return () => {
      clearInterval(autoSaveInterval);
      
      // Stop listening if active
      if (isListening) {
        stopListening();
      }
      
      // End streaming session if active
      if (currentTranscriptionId) {
        // End the streaming session
        (async () => {
          try {
            const token = await (window as any).Clerk?.session?.getToken();
            await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/end`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
              },
            });
          } catch (error) {
            console.error('Failed to end streaming session:', error);
          }
        })();
        
        // Unsubscribe from SSE
        unsubscribeFromTranscription(currentTranscriptionId);
      }
    };
  }, [currentTranscriptionId, unsubscribeFromTranscription, isListening, stopListening]);

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
    
    // Initialize ehrData in the function scope
    let ehrData: Record<string, any> = {};
    
    try {
      // Fetch patient data from EHRBase if available
      if (patient.ehr_id) {
        try {
          // Get patient summary from EHRBase using EHR ID
          const summary = await ehrbaseAPI.getPatientSummary(patient.ehr_id);
          console.log('EHRBase patient summary:', summary);
          console.log('Summary active_problems:', summary?.active_problems);
          console.log('Summary latest_record:', summary?.latest_record);
          
          // Get patient records using EHR ID
          const records = await ehrbaseAPI.getPatientRecords(patient.ehr_id);
          console.log('EHRBase patient records:', records);
          console.log('Records data:', records?.records);
          
          // Get recent sections from EHRBase
          let recentHistory = '';
          let recentMedications = '';
          let recentAllergies = patient.allergies || '';
          
          if (records?.records && records.records.length > 0) {
            // Get the most recent record
            const recentRecord = records.records[0];
            console.log('Recent record:', recentRecord);
            
            // Check if the record has direct content
            if (recentRecord.content) {
              recentHistory = recentRecord.content;
            }
            
            // Try to fetch detailed sections if record has an ID
            if (recentRecord.id || recentRecord.record_id) {
              const recordId = recentRecord.id || recentRecord.record_id;
              console.log('Fetching sections for record ID:', recordId);
              
              try {
                // Fetch all sections
                const [historySection, examinationSection, assessmentSection, planSection] = await Promise.all([
                  ehrbaseAPI.getRecordSection(recordId, 'history').catch(e => null),
                  ehrbaseAPI.getRecordSection(recordId, 'examination').catch(e => null),
                  ehrbaseAPI.getRecordSection(recordId, 'assessment').catch(e => null),
                  ehrbaseAPI.getRecordSection(recordId, 'plan').catch(e => null)
                ]);
                
                console.log('History section:', historySection);
                console.log('Examination section:', examinationSection);
                console.log('Assessment section:', assessmentSection);
                console.log('Plan section:', planSection);
                
                if (historySection) {
                  recentHistory = historySection.content || historySection.text || historySection.history_present_illness || recentHistory;
                }
                
                if (assessmentSection) {
                  // Assessment might contain diagnoses
                  if (assessmentSection.diagnoses) {
                    summary.active_problems = assessmentSection.diagnoses;
                  }
                }
              } catch (sectionError) {
                console.warn('Failed to fetch some record sections:', sectionError);
              }
            }
          }
          
          // Compile EHR data - check latest_record for actual content
          const latestRecord = summary?.latest_record;
          console.log('Active problems from summary:', summary?.active_problems);
          console.log('Latest record content:', latestRecord);
          
          // Check if latest record has the full clinical data
          let chiefComplaint = 'Patient presents for evaluation';
          let reviewOfSystems = 'Review of systems negative except as noted in HPI';
          let physicalExam = 'Physical examination pending';
          let vitalSigns = {};
          
          // Extract from latest record if available
          if (latestRecord) {
            if (latestRecord.chief_complaint) chiefComplaint = latestRecord.chief_complaint;
            if (latestRecord.review_of_systems) reviewOfSystems = latestRecord.review_of_systems;
            if (latestRecord.physical_examination) physicalExam = latestRecord.physical_examination;
            if (latestRecord.vital_signs) vitalSigns = latestRecord.vital_signs;
            
            // Also check nested structure
            if (latestRecord.sections) {
              if (latestRecord.sections.chief_complaint) chiefComplaint = latestRecord.sections.chief_complaint;
              if (latestRecord.sections.ros) reviewOfSystems = latestRecord.sections.ros;
              if (latestRecord.sections.physical_exam) physicalExam = latestRecord.sections.physical_exam;
            }
          }
          
          ehrData = {
            chief_complaint: selectedEncounter?.chief_complaint || chiefComplaint || summary?.recent_chief_complaint || 'Patient presents for evaluation',
            history_present_illness: recentHistory || latestRecord?.history_present_illness || summary?.history_present_illness || latestRecord?.content || '',
            medications: recentMedications || (Array.isArray(summary?.medications) ? summary.medications.join(', ') : summary?.medications) || 'No current medications',
            allergies: recentAllergies || (Array.isArray(summary?.allergies) ? summary.allergies.join(', ') : summary?.allergies) || 'NKDA',
            past_medical_history: (Array.isArray(summary?.active_problems) && summary.active_problems.length > 0) 
              ? summary.active_problems.map((problem: any) => {
                  if (typeof problem === 'string') return problem;
                  if (problem.name) return problem.name;
                  if (problem.description) return problem.description;
                  if (problem.diagnosis) return problem.diagnosis;
                  if (problem.condition) return problem.condition;
                  // Handle structured problem data with ICD code and plan
                  if (problem.problem && problem.icd_code) {
                    return `${problem.problem} (ICD-10: ${problem.icd_code})${problem.plan ? `\n   Plan: ${problem.plan}` : ''}`;
                  }
                  // Fallback for unstructured data
                  return JSON.stringify(problem);
                }).join('\n\n')
              : (summary?.past_medical_history || patient.recent_diagnosis?.join(', ') || 'No significant past medical history'),
            social_history: summary?.social_history || patient.smoking_history || 'Not documented',
            family_history: summary?.family_history || 'Not documented',
            vital_signs: vitalSigns || latestRecord?.vitals || selectedEncounter?.vitals || recentVitals || summary?.vitals || {},
            review_of_systems: reviewOfSystems || latestRecord?.review_of_systems || summary?.review_of_systems || 'Review of systems negative except as noted in HPI',
            physical_examination: physicalExam || latestRecord?.physical_examination || summary?.physical_examination || 'Physical examination pending'
          };
          
          console.log('Compiled EHR data for agents:', ehrData);
          
          // Process the prefill data for UI
          processClinicalNotesPrefill({
            type: 'clinical_notes:prefill',
            data: {
              sections: ehrData,
              patient_data: patient
            }
          });
          
          // Update vitals state
          if (ehrData.vital_signs && Object.keys(ehrData.vital_signs).length > 0) {
            setVitals(ehrData.vital_signs);
          }
        } catch (ehrError) {
          console.error('Failed to fetch EHRBase data:', ehrError);
          // Continue without EHR data
        }
      }
      
      // Use existing encounter ID or create a temporary one
      let encounterId = encounter?.id || `temp-${Date.now()}`;
      
      // Start streaming session with agent system
      const token = await (window as any).Clerk?.session?.getToken();
      console.log('Starting streaming session with encounter:', encounterId);
      
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          encounter_id: encounterId,
          format_preference: 'soap',
          ehr_sections: ehrData || {}, // Send the actual EHR data that was fetched, not current UI sections
          // Include patient info for temporary encounters
          patient_ehr_id: patient.ehr_id,
          patient_mrn: patient.mrn,
          patient_first_name: patient.first_name,
          patient_last_name: patient.last_name,
          patient_gender: patient.gender,
          provider_name: encounter?.provider_name || 'Dr. Provider'
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Streaming session error:', response.status, errorText);
        throw new Error(`Failed to start streaming session: ${response.status} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Streaming session started:', data);
      
      // Subscribe to SSE updates
      setCurrentTranscriptionId(data.session_id);
      subscribeToTranscription(data.session_id);
      
      // Start speech recognition
      const speechSupported = isSupported || webSpeechSupported;
      console.log('Speech recognition support status:', {
        hookSupport: isSupported,
        directSupport: webSpeechSupported,
        finalSupport: speechSupported
      });
      
      if (speechSupported) {
        console.log('Starting speech recognition...');
        startListening();
      } else {
        console.warn('Speech recognition not supported in this browser');
        // Try starting anyway in case it's a timing issue
        setTimeout(() => {
          const recheckSupport = isSupported || webSpeechSupported;
          console.log('Rechecking speech support after delay:', {
            hookSupport: isSupported,
            directSupport: webSpeechSupported,
            finalSupport: recheckSupport
          });
          if (recheckSupport) {
            console.log('Speech recognition now supported, starting...');
            startListening();
          }
        }, 500);
      }
      
      setIsLoadingEHR(false);
        
    } catch (error) {
      console.error('Failed to start clinical notes:', error);
      setIsLoadingEHR(false);
    }
  };

  const handleAddToSection = (section: string, content: string, transcriptionId?: string) => {
    // This function will be called when user adds transcription to a section
    console.log(`Adding to section ${section}:`, content);
    
    // Store link between note text and transcription
    if (transcriptionId) {
      setTranscriptionLinks(prev => new Map(prev).set(`${section}-${Date.now()}`, transcriptionId));
    }
    
    // Update local state
    setSections((prev: any) => ({
      ...prev,
      [section]: prev[section] ? `${prev[section]}\n${content}` : content
    }));
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
      {/* Check if patient is selected */}
      {!patient ? (
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          gap: 2
        }}>
          <Typography variant="h6" color="text.secondary">
            No patient selected
          </Typography>
          <Button
            variant="contained"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/patients')}
          >
            Select a Patient
          </Button>
        </Box>
      ) : (
        <>
          {/* Patient Header - Full Width */}
          <Box sx={{ px: 2, py: 1, bgcolor: '#ffffff', borderBottom: '1px solid #e0e0e0' }}>
            <PatientHeader 
              patient={{
                ...patient,
                allergies: Array.isArray(patient.allergies) 
                  ? patient.allergies.join(', ')
                  : patient.allergies
              }} 
              encounter={encounter || {
                id: '',
                patient_id: patient.id,
                chief_complaint: '',
                provider_name: '',
                referring_physician: '',
                encounter_date: new Date().toISOString(),
                encounter_type: 'Unknown',
                status: 'Active',
                risk_factors: []
              }}
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
                gap: 2,
                overflowY: 'auto'
              }}>
                {/* Transcription controls */}
                <Box sx={{ textAlign: 'center' }}>
                  <Box sx={{
                    width: 80,
                    height: 80,
                    borderRadius: '50%',
                    border: '3px solid rgba(255,255,255,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto',
                    mb: 2,
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    bgcolor: isListening ? 'rgba(255,255,255,0.2)' : 'transparent',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.1)',
                      transform: 'scale(1.05)'
                    }
                  }}
                  onClick={() => isListening ? stopListening() : startListening()}
                  >
                    <MicIcon sx={{ 
                      fontSize: 40, 
                      opacity: isListening ? 1 : 0.7,
                      animation: isListening ? 'pulse 2s infinite' : 'none'
                    }} />
                  </Box>
                  
                  <Typography variant="h6" sx={{ opacity: 0.9, mb: 1 }}>
                    {isListening ? 'Listening...' : 'Ready to Transcribe'}
                  </Typography>
                  
                  {!isSupported && (
                    <Alert severity="warning" sx={{ mx: 2 }}>
                      Speech recognition not supported. Please use Chrome or Edge.
                    </Alert>
                  )}
                </Box>
                
                {/* Live transcript display */}
                {(speechTranscript || interimTranscript) && (
                  <Box sx={{ 
                    px: 2,
                    flex: 1,
                    overflowY: 'auto'
                  }}>
                    <Typography variant="body2" sx={{ 
                      color: 'rgba(255,255,255,0.9)',
                      lineHeight: 1.6
                    }}>
                      {speechTranscript}
                    </Typography>
                    {interimTranscript && (
                      <Typography variant="body2" sx={{ 
                        color: 'rgba(255,255,255,0.6)',
                        fontStyle: 'italic',
                        display: 'inline'
                      }}>
                        {' ' + interimTranscript}
                      </Typography>
                    )}
                  </Box>
                )}
                
                {/* Word count */}
                {speechTranscript && (
                  <Box sx={{ 
                    px: 2, 
                    py: 1, 
                    borderTop: '1px solid rgba(255,255,255,0.2)' 
                  }}>
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>
                      {speechTranscript.split(' ').filter(w => w.length > 0).length} words
                    </Typography>
                  </Box>
                )}
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
                {/* Debug: Show available sections */}
                {process.env.NODE_ENV === 'development' && (
                  <Box sx={{ mb: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Debug - Available sections: {Object.keys(sections).filter(k => sections[k]).join(', ') || 'none'}
                    </Typography>
                  </Box>
                )}

                {/* Chief Complaint */}
                {(sections.chief_complaint || encounter?.chief_complaint) && (
                  <Accordion expanded defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        CHIEF COMPLAINT
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2">
                        {sections.chief_complaint || encounter?.chief_complaint}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* History of Present Illness */}
                {sections.history_present_illness && (
                  <Accordion expanded defaultExpanded sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        HISTORY OF PRESENT ILLNESS
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.history_present_illness}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Past Medical History */}
                {sections.past_medical_history && (
                  <Accordion defaultExpanded sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        PAST MEDICAL HISTORY
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {sections.past_medical_history && typeof sections.past_medical_history === 'string' 
                          ? sections.past_medical_history.split('\n\n').map((problem: string, index: number) => (
                          <Box key={index} sx={{ 
                            p: 1.5, 
                            bgcolor: 'grey.50', 
                            borderRadius: 1,
                            borderLeft: '3px solid',
                            borderLeftColor: 'primary.main'
                          }}>
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                              {problem}
                            </Typography>
                          </Box>
                        ))
                          : sections.past_medical_history}
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Medications */}
                {sections.medications && (
                  <Accordion defaultExpanded sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        MEDICATIONS
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.medications}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Allergies */}
                {sections.allergies && (
                  <Accordion defaultExpanded sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        ALLERGIES
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.allergies}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Review of Systems */}
                {sections.review_of_systems && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        REVIEW OF SYSTEMS
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.review_of_systems}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Physical Examination */}
                {sections.physical_examination && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        PHYSICAL EXAMINATION
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.physical_examination}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Additional Notes */}
                {sections.additional_notes && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        ADDITIONAL NOTES
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.additional_notes}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Care Coordination */}
                {sections.care_coordination && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        CARE COORDINATION
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.care_coordination}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Show placeholder if no sections have data yet */}
                {!Object.values(sections).some(v => v) && !encounter?.chief_complaint && (
                  <Box sx={{ 
                    textAlign: 'center', 
                    py: 4, 
                    px: 2,
                    color: 'text.secondary' 
                  }}>
                    <Typography variant="body1" gutterBottom>
                      Clinical notes will appear here as you speak
                    </Typography>
                    <Typography variant="body2">
                      Start speaking to begin documentation
                    </Typography>
                  </Box>
                )}
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
                {/* Assessment */}
                {sections.assessment && (
                  <Accordion expanded defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        ASSESSMENT
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.assessment}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Plan */}
                {sections.plan && (
                  <Accordion expanded defaultExpanded sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        PLAN
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.plan}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Diagnostic Results */}
                {sections.diagnostic_results && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        DIAGNOSTIC RESULTS
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.diagnostic_results}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Show placeholder if no assessment/plan yet */}
                {!sections.assessment && !sections.plan && (
                  <Box sx={{ 
                    textAlign: 'center', 
                    py: 4, 
                    px: 2,
                    color: 'text.secondary' 
                  }}>
                    <Typography variant="body1" gutterBottom>
                      Assessment and plan will be generated
                    </Typography>
                    <Typography variant="body2">
                      Based on the clinical information provided
                    </Typography>
                  </Box>
                )}

                {/* Progress indicator */}
                {transcriptionProgress > 0 && transcriptionProgress < 100 && (
                  <Box sx={{ mt: 2, p: 2, bgcolor: '#f0f8ff', borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={20} />
                      <Typography variant="body2">
                        Processing clinical notes... {transcriptionProgress}%
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>
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
            {isDraftSaved ? `Last saved: ${new Date(lastSaveTime).toLocaleTimeString()}` : 'Unsaved changes'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: isListening ? '#f44336' : '#4caf50',
              animation: isListening ? 'pulse 1.5s infinite' : 'none'
            }} />
            <Typography variant="body2">
              Voice recording: {isListening ? 'Recording' : 'Ready'}
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
        </>
      )}
    </Box>
  );
}

export default ClinicalNotesPage;