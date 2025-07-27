import React, { useState, useEffect } from 'react';
import { Box, Grid, Alert, Button, CircularProgress, Backdrop, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PatientHeader from '../components/ClinicalNotes/PatientHeader';
import ClinicalDocumentationClean from '../components/ClinicalNotes/ClinicalDocumentationClean';
import RealtimeTranscription from '../components/ClinicalNotes/RealtimeTranscription';
import ActionBar from '../components/ClinicalNotes/ActionBar';
import webSocketService from '../services/websocket';
import { usePatient } from '../contexts/PatientContext';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

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

  useEffect(() => {
    // Auto-start clinical notes if coming from patient selection
    if (selectedPatient && !clinicalNotesStarted) {
      handleStartClinicalNotes();
    }

    // Listen for real-time vital updates
    const handleVitalUpdate = (data: any) => {
      if (data.type === 'vitals:update') {
        setVitals((prevVitals: any) => ({ ...prevVitals, ...data.vitals }));
      }
    };

    // Listen for clinical notes prefill
    const handleClinicalNotesPrefill = (data: any) => {
      setIsLoadingEHR(false);
      setClinicalNotesStarted(true);
      
      // Pre-populate sections with EHR data
      if (data.data?.sections) {
        setSections(data.data.sections);
        setVitals(data.data.sections.vitals || {});
      }
    };


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
    
    // Since we already have patient data from Patient Records page,
    // create the prefill data structure directly instead of doing another EHR search
    const prefillData = {
      patient_info: {
        name: `${patient.first_name} ${patient.last_name}`,
        mrn: patient.mrn,
        date_of_birth: patient.date_of_birth,
        age: patient.age,
        gender: patient.gender,
        phone: patient.phone,
        email: patient.email,
        ehr_id: patient.ehr_id
      },
      sections: {
        chief_complaint: patient.recent_chief_complaint || selectedEncounter?.chief_complaint || "",
        history_present_illness: "",
        past_medical_history: patient.recent_diagnosis || selectedEncounter?.diagnosis || [],
        medications: [],
        allergies: patient.allergies ? [patient.allergies] : ["NKDA"],
        social_history: {
          smoking: patient.smoking_history || "Unknown",
          alcohol: "Unknown",
          occupation: "Unknown"
        },
        family_history: [],
        review_of_systems: {},
        vitals: recentVitals || selectedEncounter?.vitals || {},
        physical_exam: {},
        assessment_plan: {
          clinical_notes: patient.recent_clinical_notes || selectedEncounter?.notes || "",
          diagnosis: patient.recent_diagnosis || selectedEncounter?.diagnosis || []
        }
      },
      recent_labs: [],
      recent_encounters: selectedEncounter ? [{
        date: selectedEncounter.encounter_date,
        type: selectedEncounter.encounter_type,
        chief_complaint: selectedEncounter.chief_complaint,
        provider: selectedEncounter.provider_name,
        status: selectedEncounter.status
      }] : [],
      metadata: {
        prefill_timestamp: new Date().toISOString(),
        data_sources: ["patient_context"],
        source: "existing_patient_selection"
      }
    };

    // Set the prefilled data directly
    setSections(prefillData.sections);
    setVitals(prefillData.sections.vitals || {});
    
    // Mark as completed without WebSocket call
    setIsLoadingEHR(false);
    setClinicalNotesStarted(true);
    
    console.log('Clinical notes started with existing patient data:', prefillData);
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

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh',
      bgcolor: '#f8f9fa' 
    }}>
      {/* Patient Header - Full Width in light blue section */}
      <Box sx={{ px: 2, py: 2 }}>
        <PatientHeader 
          patient={patient} 
          encounter={encounter}
          vitals={vitals}
        />
      </Box>
      
      {/* Main Content Grid - Full Width */}
      <Box sx={{ 
        flex: 1, 
        overflow: 'hidden',
        px: 2,
        py: 1
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
          /* Clinical Notes Interface */
          <Box sx={{ display: 'flex', gap: 2, height: '100%' }}>
            {/* Left Side: Live Transcription */}
            {!isSidebarCollapsed && (
              <Box sx={{ 
                width: 380,
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                gap: 2
              }}>
                <RealtimeTranscription 
                  encounterId={encounter.id}
                  patientId={patient.id}
                  onTranscriptionUpdate={handleAddToSection}
                  onCollapsedChange={setIsSidebarCollapsed}
                  isCollapsed={isSidebarCollapsed}
                />
              </Box>
            )}

            {/* Collapsed Sidebar */}
            {isSidebarCollapsed && (
              <Box sx={{ 
                width: 60,
                height: '100%'
              }}>
                <RealtimeTranscription 
                  encounterId={encounter.id}
                  patientId={patient.id}
                  onTranscriptionUpdate={handleAddToSection}
                  onCollapsedChange={setIsSidebarCollapsed}
                  isCollapsed={isSidebarCollapsed}
                />
              </Box>
            )}

            {/* Right Side: Clinical Documentation */}
            <Box sx={{ 
              flex: 1,
              height: '100%',
              overflow: 'hidden'
            }}>
              <ClinicalDocumentationClean 
                encounterId={encounter.id}
                patientId={patient.ehr_id || patient.id || '123'}
                onAddToSection={handleAddToSection}
                prefilledSections={sections}
              />
            </Box>
          </Box>
        )}
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

      {/* Action Bar */}
      <ActionBar 
        onSaveDraft={handleSaveDraft}
        onSignEncounter={handleSignEncounter}
        isDraftSaved={isDraftSaved}
        lastSaveTime={lastSaveTime}
        encounterId={encounter.id}
        patientId={patient.ehr_id || patient.id || '123'}
        onShowSummaryReview={handleShowSummaryReview}
      />
    </Box>
  );
}

export default ClinicalNotesPage;