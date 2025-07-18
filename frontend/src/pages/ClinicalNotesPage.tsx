import React from 'react';
import { Box, Grid, Typography } from '@mui/material';
import ClinicalNotes from '../components/ClinicalNotes/ClinicalNotes';
import PatientSummary from '../components/Patient/PatientSummary';

function ClinicalNotesPage() {
  // Mock data - in real app, this would come from route params or global state
  const mockPatient = {
    id: '123',
    first_name: 'John',
    last_name: 'Doe',
    mrn: 'MRN001234',
    date_of_birth: '1978-05-15',
    gender: 'Male'
  };

  const mockEncounter = {
    id: 'enc-001',
    chief_complaint: 'Chest pain',
    referring_physician: 'Dr. Smith'
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Clinical Documentation
      </Typography>

      <Grid container spacing={3}>
        {/* Patient Summary Section */}
        <Grid item xs={12} md={4}>
          <PatientSummary 
            patient={mockPatient} 
            encounter={mockEncounter}
          />
        </Grid>

        {/* Clinical Notes Section */}
        <Grid item xs={12} md={8}>
          <ClinicalNotes encounterId={mockEncounter.id} />
        </Grid>
      </Grid>
    </Box>
  );
}

export default ClinicalNotesPage;