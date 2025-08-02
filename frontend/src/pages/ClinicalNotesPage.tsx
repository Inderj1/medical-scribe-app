import React, { useState, useEffect, useRef } from 'react';
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

// Map backend section names to frontend section names
const SECTION_NAME_MAP: Record<string, string> = {
  // SOAP format mappings
  'soap_subjective': 'history_present_illness',
  'soap_objective': 'physical_examination',
  'soap_assessment': 'assessment',
  'soap_plan': 'plan',
  // Direct mappings
  'chief_complaint': 'chief_complaint',
  'history_present_illness': 'history_present_illness',
  'past_medical_history': 'past_medical_history',
  'medications': 'medications',
  'allergies': 'allergies',
  'social_history': 'social_history',
  'family_history': 'family_history',
  'review_of_systems': 'review_of_systems',
  'physical_examination': 'physical_examination',
  'assessment': 'assessment',
  'plan': 'plan',
  'diagnostic_results': 'diagnostic_results',
  'care_coordination': 'care_coordination',
  'vital_signs': 'vital_signs'
};

function ClinicalNotesPage() {
  const navigate = useNavigate();
  const { selectedPatient, selectedEncounter, recentVitals, setSelectedEncounter } = usePatient();
  const { subscribeToTranscription, unsubscribeFromTranscription, lastEvent, connectionStatus } = useSSE();
  
  // State and refs
  const [currentTranscriptionId, setCurrentTranscriptionId] = useState<string | null>(null);
  const sessionEndedRef = useRef(false);
  const isStartingSession = useRef(false);

  // Define handleEndSession function before useWebSpeech hook
  const handleEndSession = async () => {
    if (!currentTranscriptionId) {
      console.log('No active session to end');
      return;
    }
    
    // Check if session was already ended
    if (sessionEndedRef.current) {
      console.log('Session already ended, skipping duplicate end call');
      return;
    }

    try {
      let token;
      try {
        token = await (window as any).Clerk?.session?.getToken();
      } catch (authError) {
        console.warn('Failed to get auth token, proceeding without authentication:', authError);
        // Continue without token - the backend will handle unauthorized requests
      }
      
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/end`, {
        method: 'POST',
        headers: token ? {
          'Authorization': `Bearer ${token}`,
        } : {},
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Session end response:', data);
        sessionEndedRef.current = true;
        
        if (data.status === 'ended') {
          console.log('Session ended successfully, agents will now process the transcript');
        } else if (data.status === 'already_processing') {
          console.log('Session already being processed');
        } else if (data.status === 'already_completed') {
          console.log('Session already completed');
        }
      } else {
        console.error('Failed to end session:', response.status, response.statusText);
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
      console.log('[SPEECH] Transcript received:', {
        text,
        isFinal,
        currentTranscriptionId,
        timestamp: new Date().toISOString()
      });
      
      // Update live transcript with everything (interim and final)
      if (text && isFinal) {
        setLiveTranscript(prev => {
          // For final results, append to transcript
          // Add space only if there's existing content
          const separator = prev && prev.trim() ? ' ' : '';
          const newTranscript = (prev || '').trim() + separator + text;
          console.log('[LIVE_TRANSCRIPT] Adding final text:', {
            previous: prev || '',
            adding: text,
            result: newTranscript,
            wordCount: newTranscript.split(' ').filter(w => w.length > 0).length
          });
          return newTranscript;
        });
      }
      
      // Only send final results to backend
      if (currentTranscriptionId && isFinal && !sessionEndedRef.current) {
        // Send text chunk to backend
        try {
          const token = await (window as any).Clerk?.session?.getToken();
          const payload = {
            text,
            is_final: isFinal,
            timestamp: new Date().toISOString(),
            speaker_id: 'SPEAKER_01', // Default speaker for browser-based recording
          };
          
          console.log('[SPEECH] Sending text chunk to backend:', {
            url: `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/text`,
            payload
          });
          
          const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/text`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
          });
          
          if (response.ok) {
            const result = await response.json();
            console.log('[SPEECH] Text chunk sent successfully:', result);
          } else {
            console.error('[SPEECH] Failed to send text chunk:', {
              status: response.status,
              statusText: response.statusText,
              body: await response.text()
            });
          }
        } catch (error) {
          console.error('[SPEECH] Error sending text chunk:', error);
        }
      } else {
        console.log('[SPEECH] Skipping transcript send:', {
          hasTranscriptionId: !!currentTranscriptionId,
          isFinal,
          reason: !currentTranscriptionId ? 'No transcription ID' : 'Not final'
        });
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
    onError: (error: string) => {
      // Don't end session for network errors - they'll auto-recover
      if (error !== 'network') {
        console.error('Speech recognition error:', error);
      }
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
  const [sections, setSections] = useState<any>({
    chief_complaint: '',
    history_present_illness: '',
    past_medical_history: '', 
    medications: '',
    allergies: '',
    family_history: '',
    social_history: '',
    review_of_systems: '',
    physical_examination: '',
    assessment: '',
    plan: '',
    additional_notes: ''
  });
  const [showSummaryReview, setShowSummaryReview] = useState(false);
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState<string>('');

  // Log sections changes
  useEffect(() => {
    console.log('[SECTIONS] Sections state changed:', {
      keys: Object.keys(sections),
      hasContent: Object.keys(sections).filter(k => sections[k]).length,
      chief_complaint: sections.chief_complaint ? 'YES' : 'NO',
      medications: sections.medications ? 'YES' : 'NO',
      allergies: sections.allergies ? 'YES' : 'NO',
      timestamp: new Date().toISOString()
    });
  }, [sections]);

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
      
      // Merge with existing sections to preserve SSE updates
      setSections((prevSections: any) => ({
        ...prevSections,
        ...sanitizedSections
      }));
      console.log('Merging sections state with:', sanitizedSections);
      
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

  // Periodic section polling when recording
  useEffect(() => {
    if (!currentTranscriptionId || !isListening) return;
    
    console.log('[POLLING] Setting up section polling for session:', currentTranscriptionId);
    
    const pollSections = async () => {
      try {
        const token = await (window as any).Clerk?.session?.getToken();
        if (!token) {
          console.log('[POLLING] No auth token available');
          return;
        }
        
        console.log('[POLLING] Fetching sections...');
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/sections`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          const currentSectionCount = Object.keys(sections).filter(k => sections[k]).length;
          const fetchedSectionCount = Object.keys(data.sections || {}).length;
          
          console.log('[POLLING] Section check:', {
            current: currentSectionCount,
            fetched: fetchedSectionCount,
            status: data.transcription_status,
            sections: Object.keys(data.sections || {})
          });
          
          // Check for new or updated sections
          let hasUpdates = false;
          const updates: Record<string, any> = {};
          
          Object.entries(data.sections || {}).forEach(([section, sectionData]: [string, any]) => {
            const mappedSection = SECTION_NAME_MAP[section] || 'additional_notes';
            const newContent = sectionData.content || '';
            const currentContent = sections[mappedSection] || '';
            
            // Check if this is new content or updated content
            if (newContent && newContent !== currentContent) {
              hasUpdates = true;
              updates[mappedSection] = newContent;
              console.log('[POLLING] Section update detected:', {
                section: mappedSection,
                backend_section: section,
                contentLength: newContent.length,
                isNew: !currentContent
              });
            }
          });
          
          if (hasUpdates) {
            console.log('[POLLING] Applying section updates:', Object.keys(updates));
            setSections((prev: any) => ({
              ...prev,
              ...updates
            }));
          }
        }
      } catch (error) {
        console.error('[POLLING] Error polling sections:', error);
      }
    };
    
    // Poll every 3 seconds
    const interval = setInterval(pollSections, 3000);
    
    return () => clearInterval(interval);
  }, [currentTranscriptionId, isListening, sections]);

  useEffect(() => {
    // Handle SSE events
    if (lastEvent) {
      console.log('[SSE] Event received:', {
        type: lastEvent.type,
        data: lastEvent.data,
        timestamp: new Date().toISOString()
      });
      
      switch (lastEvent.type) {
        case 'processing_started':
          console.log('[SSE] Processing started');
          setIsLoadingEHR(false);
          break;
          
        case 'progress':
          console.log('[SSE] Progress update:', {
            progress: lastEvent.data.progress,
            message: lastEvent.data.message
          });
          setTranscriptionProgress(lastEvent.data.progress);
          break;
          
        case 'transcription_chunk':
          // Handle real-time transcription chunks
          console.log('[SSE] Transcription chunk received:', {
            chunk: lastEvent.data,
            timestamp: new Date().toISOString()
          });
          // Don't update live transcript here - it's already updated from speech recognition
          break;
          
        case 'section_completed':
          // Handle section completion from agents
          const { section, content, confidence } = lastEvent.data;
          // Ensure content is a string
          const contentStr = typeof content === 'string' ? content : 
                            typeof content === 'object' ? JSON.stringify(content) : 
                            String(content || '');
          console.log('[SSE] Section completed:', {
            section,
            content: contentStr ? contentStr.substring(0, 100) + '...' : 'empty',
            confidence,
            timestamp: new Date().toISOString()
          });
          
          // Map backend section name to frontend section name
          const mappedSection = SECTION_NAME_MAP[section] || 'additional_notes';
          console.log('[SSE] Section mapping:', {
            backendSection: section,
            frontendSection: mappedSection,
            isKnownSection: !!SECTION_NAME_MAP[section]
          });
          
          setSections((prev: any) => {
            let updated;
            
            if (mappedSection === 'additional_notes') {
              // For unmapped sections, append to additional notes with formatting
              const existingNotes = prev.additional_notes || '';
              const timestamp = new Date().toLocaleTimeString();
              const formattedContent = `[${timestamp}] ${section.replace(/_/g, ' ').toUpperCase()}:\n${contentStr}\n\n`;
              updated = {
                ...prev,
                additional_notes: existingNotes + formattedContent
              };
            } else {
              // For mapped sections, replace content
              updated = {
                ...prev,
                [mappedSection]: contentStr
              };
            }
            
            console.log('[SSE] Updated sections state:', {
              previousKeys: Object.keys(prev),
              newKeys: Object.keys(updated),
              updatedSection: mappedSection,
              isAdditionalNotes: mappedSection === 'additional_notes',
              actualContent: updated[mappedSection]?.substring(0, 50) + '...',
              fullUpdatedObject: updated
            });
            return updated;
          });
          
          // Debug: Log current sections after update
          setTimeout(() => {
            console.log('[SSE] Current sections after update:', sections);
          }, 100);
          
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
          
          setCurrentSection(mappedSection);
          break;
          
        case 'completed':
          console.log('[SSE] Processing completed:', {
            data: lastEvent.data,
            timestamp: new Date().toISOString()
          });
          setIsLoadingEHR(false);
          setTranscriptionProgress(100);
          break;
          
        case 'error':
          console.error('[SSE] Error received:', {
            error: lastEvent.data.error,
            timestamp: new Date().toISOString()
          });
          setIsLoadingEHR(false);
          break;
          
        default:
          console.log('[SSE] Unknown event type:', lastEvent.type);
      }
    }
  }, [lastEvent]);

  // Load EHR data when patient is selected
  useEffect(() => {
    if (patient?.id && !currentTranscriptionId) {
      console.log('[SESSION] Starting clinical notes for patient:', patient.id);
      handleStartClinicalNotes();
    }
  }, [patient?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Auto-save draft every 5 minutes
    const autoSaveInterval = setInterval(() => {
      handleSaveDraft();
    }, 300000);

    return () => {
      clearInterval(autoSaveInterval);
    };
  }, []);

  // Separate effect for cleanup when component unmounts or transcription changes
  useEffect(() => {
    return () => {
      // Only clean up on unmount or when transcription ID changes
      if (currentTranscriptionId) {
        console.log('[CLEANUP] Component unmounting or transcription changing, cleaning up session:', currentTranscriptionId);
        
        // Stop listening if active
        if (isListening) {
          stopListening();
        }
        
        // End the streaming session
        (async () => {
          try {
            let token;
            try {
              token = await (window as any).Clerk?.session?.getToken();
            } catch (authError) {
              console.warn('Failed to get auth token during cleanup:', authError);
            }
            
            const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${currentTranscriptionId}/end`, {
              method: 'POST',
              headers: token ? {
                'Authorization': `Bearer ${token}`,
              } : {},
            });
            
            // Ignore 409 conflicts as they mean the session is already ended/processing
            if (!response.ok && response.status !== 409) {
              console.error('Failed to end streaming session:', response.statusText);
            }
          } catch (error) {
            console.error('Failed to end streaming session:', error);
          }
        })();
        
        // Unsubscribe from SSE
        unsubscribeFromTranscription(currentTranscriptionId);
      }
    };
  }, [currentTranscriptionId]); // Only depend on transcriptionId, not other values

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
    
    // Reset live transcript for new session
    setLiveTranscript('');
    
    // Prevent duplicate session creation
    if (currentTranscriptionId || isStartingSession.current) {
      console.log('[SESSION] Session already active or starting:', currentTranscriptionId);
      return;
    }
    
    isStartingSession.current = true;
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
                // Fetch all sections - these may not exist for all records
                const [historySection, examinationSection, assessmentSection, planSection] = await Promise.all([
                  ehrbaseAPI.getRecordSection(recordId, 'history').catch(e => {
                    console.log('History section not available for this record');
                    return null;
                  }),
                  ehrbaseAPI.getRecordSection(recordId, 'examination').catch(e => {
                    console.log('Examination section not available for this record');
                    return null;
                  }),
                  ehrbaseAPI.getRecordSection(recordId, 'assessment').catch(e => {
                    console.log('Assessment section not available for this record');
                    return null;
                  }),
                  ehrbaseAPI.getRecordSection(recordId, 'plan').catch(e => {
                    console.log('Plan section not available for this record');
                    return null;
                  })
                ]);
                
                if (historySection || examinationSection || assessmentSection || planSection) {
                  console.log('Successfully fetched some sections from EHR');
                }
                
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
      
      // Reset session ended flag for new session
      sessionEndedRef.current = false;
      
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
          enable_speaker_diarization: true, // Enable multi-speaker support
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
      console.log('[SESSION] Setting transcription ID and subscribing to SSE:', {
        sessionId: data.session_id,
        timestamp: new Date().toISOString()
      });
      setCurrentTranscriptionId(data.session_id);
      
      // Subscribe to SSE and wait for connection
      await subscribeToTranscription(data.session_id);
      console.log('[SESSION] SSE subscription initiated for session:', data.session_id);
      
      // Wait a bit for SSE connection to establish
      await new Promise(resolve => setTimeout(resolve, 1000));
      console.log('[SESSION] Waited for SSE connection');
      
      // Fetch any sections that may have already been processed
      try {
        console.log('[SESSION] Fetching existing sections for session:', data.session_id);
        const sectionsResponse = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/streaming/${data.session_id}/sections`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        
        if (sectionsResponse.ok) {
          const sectionsData = await sectionsResponse.json();
          console.log('[SESSION] Fetched sections:', {
            count: Object.keys(sectionsData.sections || {}).length,
            sections: Object.keys(sectionsData.sections || {}),
            status: sectionsData.transcription_status
          });
          
          // Process each section
          if (sectionsData.sections) {
            Object.entries(sectionsData.sections).forEach(([section, data]: [string, any]) => {
              console.log('[SESSION] Processing fetched section:', section);
              
              // Map backend section name to frontend section name
              const mappedSection = SECTION_NAME_MAP[section] || 'additional_notes';
              
              setSections((prev: any) => {
                let updated;
                
                if (mappedSection === 'additional_notes') {
                  // For unmapped sections, append to additional notes
                  const existingNotes = prev.additional_notes || '';
                  const timestamp = new Date().toLocaleTimeString();
                  const formattedContent = `[${timestamp}] ${section.replace(/_/g, ' ').toUpperCase()} (fetched):\n${data.content}\n\n`;
                  updated = {
                    ...prev,
                    additional_notes: existingNotes + formattedContent
                  };
                } else {
                  // For mapped sections, replace content
                  updated = {
                    ...prev,
                    [mappedSection]: data.content
                  };
                }
                
                console.log('[SESSION] Updated sections after fetch:', {
                  section: mappedSection,
                  hasContent: !!data.content,
                  confidence: data.confidence
                });
                
                return updated;
              });
            });
          }
        } else {
          console.warn('[SESSION] Failed to fetch sections:', sectionsResponse.statusText);
        }
      } catch (error) {
        console.error('[SESSION] Error fetching sections:', error);
      }
      
      // Check connection status
      console.log('[SESSION] SSE connection status after wait:', connectionStatus);
      
      // Monitor connection status changes
      const checkConnection = setInterval(() => {
        console.log('[SESSION] Current SSE status:', connectionStatus);
        if (connectionStatus === 'connected') {
          console.log('[SESSION] SSE connected successfully!');
          clearInterval(checkConnection);
        }
      }, 500);
      
      // Clear the interval after 5 seconds
      setTimeout(() => clearInterval(checkConnection), 5000);
      
      // Start speech recognition
      // Check support directly as state might not be updated yet
      const directCheck = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
      const speechSupported = isSupported || webSpeechSupported || directCheck;
      console.log('[SESSION] Speech recognition support status:', {
        hookSupport: isSupported,
        directSupport: webSpeechSupported,
        directCheck: directCheck,
        finalSupport: speechSupported
      });
      
      if (speechSupported) {
        console.log('Starting speech recognition...');
        startListening();
      } else {
        console.warn('Speech recognition not supported in this browser');
        // Try starting anyway in case it's a timing issue
        setTimeout(() => {
          // Re-check support directly
          const currentSupport = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
          const recheckSupport = isSupported || currentSupport;
          console.log('Rechecking speech support after delay:', {
            hookSupport: isSupported,
            directSupport: currentSupport,
            finalSupport: recheckSupport
          });
          if (recheckSupport) {
            console.log('Speech recognition now supported, starting...');
            startListening();
          }
        }, 500);
      }
      
      setIsLoadingEHR(false);
      isStartingSession.current = false;
        
    } catch (error) {
      console.error('Failed to start clinical notes:', error);
      setIsLoadingEHR(false);
      isStartingSession.current = false;
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
                  onClick={async () => {
                    if (isListening) {
                      stopListening();
                      if (currentTranscriptionId) {
                        handleEndSession();
                      }
                    } else {
                      // Start a new session when microphone is clicked
                      if (!currentTranscriptionId || sessionEndedRef.current) {
                        await handleStartClinicalNotes();
                      }
                      startListening();
                    }
                  }}
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
                  
                  {/* Add visible Stop button when recording */}
                  {isListening && (
                    <Button
                      variant="contained"
                      color="error"
                      size="medium"
                      onClick={() => {
                        console.log('[UI] Stop button clicked');
                        stopListening();
                        if (currentTranscriptionId) {
                          handleEndSession();
                        }
                      }}
                      sx={{ 
                        mb: 2,
                        minWidth: 120,
                        fontWeight: 'bold'
                      }}
                    >
                      Stop Recording
                    </Button>
                  )}
                  
                  {!isSupported && (
                    <Alert severity="warning" sx={{ mx: 2 }}>
                      Speech recognition not supported. Please use Chrome or Edge.
                    </Alert>
                  )}
                </Box>
                
                {/* Live transcript display */}
                <Box sx={{ 
                  px: 2,
                  flex: 1,
                  overflowY: 'auto',
                  display: (liveTranscript || interimTranscript) ? 'block' : 'none'
                }}>
                  <Typography variant="body2" sx={{ 
                    color: 'rgba(255,255,255,0.9)',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap'
                  }}>
                    {liveTranscript}
                    {interimTranscript && (
                      <span style={{ 
                        color: 'rgba(255,255,255,0.6)',
                        fontStyle: 'italic'
                      }}>
                        {liveTranscript ? ' ' + interimTranscript : interimTranscript}
                      </span>
                    )}
                  </Typography>
                </Box>
                
                {/* Word count */}
                {liveTranscript && (
                  <Box sx={{ 
                    px: 2, 
                    py: 1, 
                    borderTop: '1px solid rgba(255,255,255,0.2)' 
                  }}>
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>
                      {liveTranscript.split(' ').filter(w => w.length > 0).length} words
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
                {true && (
                  <Box sx={{ mb: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                    <Typography variant="caption" color="primary">
                      Debug - Available sections: {Object.keys(sections).filter(k => sections[k]).join(', ') || 'none'}
                    </Typography>
                    <Typography variant="caption" color="primary" display="block">
                      Debug - Section count: {Object.keys(sections).filter(k => sections[k]).length}
                    </Typography>
                    <Typography variant="caption" color="info.main" display="block">
                      Debug - Chief complaint: {sections.chief_complaint ? 'YES' : 'NO'} | Medications: {sections.medications ? 'YES' : 'NO'} | Allergies: {sections.allergies ? 'YES' : 'NO'}
                    </Typography>
                    <Typography variant="caption" color="warning.main" display="block">
                      Debug - Render time: {new Date().toLocaleTimeString()}
                    </Typography>
                    <Typography variant="caption" color="success.main" display="block">
                      Debug - SSE Status: {connectionStatus} | Last Event: {lastEvent?.type || 'none'}
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

                {/* Social History */}
                {sections.social_history && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        SOCIAL HISTORY
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.social_history}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Family History */}
                {sections.family_history && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        FAMILY HISTORY
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {sections.family_history}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Additional Notes - Always visible */}
                <Accordion defaultExpanded sx={{ mt: 1 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      ADDITIONAL NOTES
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {sections.additional_notes || 'Any unmapped or supplementary information will appear here...'}
                    </Typography>
                  </AccordionDetails>
                </Accordion>

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
