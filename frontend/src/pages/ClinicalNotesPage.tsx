import React, { useState, useEffect } from 'react';
import { Box, Grid } from '@mui/material';
import PatientHeader from '../components/ClinicalNotes/PatientHeader';
import PatientSummaryVitals from '../components/ClinicalNotes/PatientSummaryVitals';
import PhysicalExamination from '../components/ClinicalNotes/PhysicalExamination';
import ClinicalDocumentation from '../components/ClinicalNotes/ClinicalDocumentation';
import ActionBar from '../components/ClinicalNotes/ActionBar';
import webSocketService from '../services/websocket';

function ClinicalNotesPage() {
  // Mock data - in real app, this would come from route params or global state
  const mockPatient = {
    id: '123',
    first_name: 'John',
    last_name: 'Doe',
    mrn: 'MRN001234',
    date_of_birth: '1978-05-15',
    gender: 'Male',
    age: 45,
    smoking_history: '20+ pack-years',
    allergies: 'NKDA'
  };

  const mockEncounter = {
    id: 'enc-001',
    chief_complaint: 'Chest pain',
    referring_physician: 'Dr. Smith',
    encounter_date: new Date(),
    risk_factors: ['smoker', 'hypertension']
  };

  const [vitals, setVitals] = useState({
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
        setVitals(prevVitals => ({ ...prevVitals, ...data.vitals }));
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
      {/* Patient Header */}
      <PatientHeader 
        patient={mockPatient} 
        encounter={mockEncounter}
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
              patient={mockPatient}
              encounter={mockEncounter}
              vitals={vitals}
            />
            <PhysicalExamination 
              encounterId={mockEncounter.id}
            />
          </Grid>

          {/* Right Column: Clinical Documentation */}
          <Grid item xs={12} md={6} sx={{ 
            height: '100%',
            overflow: 'hidden'
          }}>
            <ClinicalDocumentation 
              encounterId={mockEncounter.id}
              patientId={mockPatient.id}
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