import React, { useState, useEffect } from 'react';
import { Box, Grid, Alert, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import PatientHeader from '../components/ClinicalNotes/PatientHeader';
import PatientSummaryVitals from '../components/ClinicalNotes/PatientSummaryVitals';
import PhysicalExamination from '../components/ClinicalNotes/PhysicalExamination';
import ClinicalDocumentation from '../components/ClinicalNotes/ClinicalDocumentation';
import ActionBar from '../components/ClinicalNotes/ActionBar';
import webSocketService from '../services/websocket';
import { usePatient } from '../contexts/PatientContext';

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
    email: selectedPatient.email
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
    chief_complaint: selectedEncounter.chief_complaint,
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

  useEffect(() => {
    // Listen for real-time vital updates
    const handleVitalUpdate = (data: any) => {
      if (data.type === 'vitals:update') {
        setVitals((prevVitals: any) => ({ ...prevVitals, ...data.vitals }));
      }
    };

    webSocketService.on('vitals:update', handleVitalUpdate);

    // Auto-save draft every 5 minutes
    const autoSaveInterval = setInterval(() => {
      handleSaveDraft();
    }, 300000);

    return () => {
      webSocketService.off('vitals:update', handleVitalUpdate);
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

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh',
      bgcolor: '#f8f9fa' 
    }}>
      {/* Show notification if patient data is loaded from context */}
      {selectedPatient && (
        <Alert 
          severity="info" 
          sx={{ m: 2, mb: 0 }}
          action={
            <Button 
              color="inherit" 
              size="small"
              onClick={() => navigate('/patient-records')}
            >
              Back to Patients
            </Button>
          }
        >
          Clinical note for patient: {patient.first_name} {patient.last_name} (MRN: {patient.mrn})
        </Alert>
      )}
      
      {/* Patient Header */}
      <PatientHeader 
        patient={patient} 
        encounter={encounter}
      />
      
      {/* Main Content Grid */}
      <Box sx={{ 
        flex: 1, 
        overflow: 'hidden',
        p: 2
      }}>
        <Grid container spacing={2} sx={{ height: '100%' }}>
          {/* Left Column: Patient Summary & Physical Examination */}
          <Grid item xs={12} md={6} sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 2,
            height: '100%',
            overflow: 'auto'
          }}>
            <PatientSummaryVitals 
              patient={patient}
              encounter={encounter}
              vitals={vitals}
            />
            <PhysicalExamination 
              encounterId={encounter.id}
            />
          </Grid>

          {/* Right Column: Clinical Documentation */}
          <Grid item xs={12} md={6} sx={{ 
            height: '100%',
            overflow: 'hidden'
          }}>
            <ClinicalDocumentation 
              encounterId={encounter.id}
              patientId={patient.ehr_id || patient.id || '123'}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Action Bar */}
      <ActionBar 
        onSaveDraft={handleSaveDraft}
        onSignEncounter={handleSignEncounter}
        isDraftSaved={isDraftSaved}
        lastSaveTime={lastSaveTime}
      />
    </Box>
  );
}

export default ClinicalNotesPage;