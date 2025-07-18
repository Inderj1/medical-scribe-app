import React from 'react';
import { Box, Typography, Grid, Paper, Button, Alert } from '@mui/material';
import EpicLaunch from '../components/Auth/EpicLaunch';
import PatientSearch from '../components/EHR/PatientSearch';
import { fhirService } from '../services/fhir';
import { ehrbaseService } from '../services/ehrbase';
import { ehrApi } from '../services/ehr';

function EHRIntegrationPage() {
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [testResult, setTestResult] = React.useState<string | null>(null);
  const [testing, setTesting] = React.useState(false);

  // Set EHRBASE as the active integration
  React.useEffect(() => {
    localStorage.setItem('activeEHRIntegration', 'ehrbase');
  }, []);

  const testFHIRConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // First test server connection and registration
      const connectionResult = await fhirService.testServerConnection();
      console.log('Server connection test result:', connectionResult);
      
      // Check SMART configuration
      const smartConfig = await fhirService.getSmartConfiguration();
      if (smartConfig) {
        console.log('SMART Configuration loaded:', smartConfig);
        console.log('Supported grant types:', smartConfig.grant_types_supported);
        console.log('Supported capabilities:', smartConfig.capabilities);
        console.log('Authorization endpoint:', smartConfig.authorization_endpoint);
        console.log('Token endpoint:', smartConfig.token_endpoint);
      }
      
      // Try to get server metadata first
      try {
        const metadata = await fhirService.getServerMetadata();
        console.log('Server metadata retrieved:', metadata);
      } catch (error) {
        console.log('Server metadata not accessible');
      }
      
      // Then test patient retrieval
      const patients = await fhirService.getPatients();
      setTestResult(`Success! Found ${patients.length} patients in FHIR server`);
    } catch (error) {
      setTestResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setTesting(false);
    }
  };

  const startOAuth2Flow = async () => {
    try {
      // First register the app if needed
      await fhirService.testServerConnection();
      
      // Then initiate OAuth2 authorization flow
      await fhirService.initiateAuthorizationFlow();
    } catch (error) {
      console.error('Error starting OAuth2 flow:', error);
      setTestResult(`Error starting OAuth2 flow: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const testMedicalRecordsAPI = async () => {
    console.log('=== MEDICAL RECORDS API TEST ===');
    setTesting(true);
    setTestResult(null);
    
    try {
      const baseUrl = 'https://859574eed9a9.ngrok.app/api';
      console.log('Testing Medical Records API:', baseUrl);
      
      // Test 1: Get all patients
      console.log('\n1. Testing patients endpoint...');
      try {
        const patientsResponse = await fetch(baseUrl + '/patients');
        console.log('Patients response status:', patientsResponse.status);
        const patientsData = await patientsResponse.json();
        console.log('Total patients:', patientsData.patients?.length || 0);
        
        if (patientsData.patients && patientsData.patients.length > 0) {
          setTestResult(`Found ${patientsData.patients.length} patients in Medical Records API!`);
          console.log('First 3 patients:', patientsData.patients.slice(0, 3));
          
          // Test 2: Get John Smith's records
          console.log('\n2. Testing patient records...');
          const johnSmith = patientsData.patients.find((p: any) => p.patient.name === 'John Smith');
          if (johnSmith) {
            const recordsResponse = await fetch(`${baseUrl}/patients/${johnSmith.ehr_id}/records`);
            const recordsData = await recordsResponse.json();
            console.log(`John Smith has ${recordsData.records?.length || 0} records`);
          }
        } else {
          setTestResult('Medical Records API is accessible but no patients found.');
        }
      } catch (e) {
        console.error('Patients endpoint error:', e);
      }
      
      // Test 3: Test specific record
      console.log('\n3. Testing specific record endpoint...');
      try {
        const recordResponse = await fetch(baseUrl + '/records/e7f6c37f-8cd6-456c-a84d-11655e498a01');
        console.log('Record response status:', recordResponse.status);
        if (recordResponse.ok) {
          const recordData = await recordResponse.json();
          console.log('Record patient ID:', recordData.patient_id);
          console.log('Reason for visit:', recordData.reason_for_visit);
        }
      } catch (e) {
        console.error('Record endpoint error:', e);
      }
      
    } catch (error) {
      console.error('Medical Records API test failed:', error);
      setTestResult(`Test error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setTesting(false);
      console.log('=== END MEDICAL RECORDS API TEST ===');
    }
  };

  const testPatientSearch = async () => {
    console.log('=== TESTING PATIENT SEARCH ===');
    setTesting(true);
    setTestResult(null);
    
    try {
      // Test 1: Search with no parameters (get all patients)
      console.log('Test 1: Searching for all patients (no filters)...');
      const allPatients = await ehrbaseService.searchPatients({});
      console.log(`Found ${allPatients.length} total patients:`, allPatients);
      
      // Test 2: Search by first name
      console.log('\nTest 2: Searching for patients with first name "Patient"...');
      const patientsByFirstName = await ehrbaseService.searchPatients({ firstName: 'Patient' });
      console.log(`Found ${patientsByFirstName.length} patients with first name "Patient":`, patientsByFirstName);
      
      // Test 3: Search for "John"
      console.log('\nTest 3: Searching for patients with first name "John"...');
      const patientsByJohn = await ehrbaseService.searchPatients({ firstName: 'John' });
      console.log(`Found ${patientsByJohn.length} patients with first name "John":`, patientsByJohn);
      
      // Show John patients in result
      if (patientsByJohn.length > 0) {
        const johnNames = patientsByJohn.map(p => `${p.first_name} ${p.last_name}`).join(', ');
        console.log('John patients found:', johnNames);
      }
      
      // Test 4: Direct EHR API call
      console.log('\nTest 4: Testing direct EHR API search...');
      const ehrApiResults = await ehrApi.searchPatients({
        organizationId: 'default',
        firstName: 'Patient'
      });
      console.log('EHR API search results:', ehrApiResults);
      
      const totalFound = allPatients.length;
      if (totalFound > 0) {
        setTestResult(`Patient search successful! Found ${totalFound} patients in EHRBASE.`);
      } else {
        setTestResult('Patient search completed but no patients found. Check if there are EHRs in EHRBASE.');
      }
    } catch (error) {
      console.error('Patient search test failed:', error);
      setTestResult(`Patient search error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setTesting(false);
      console.log('=== END PATIENT SEARCH TEST ===');
    }
  };

  const testEHRBaseConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      console.log('Testing connection to Medical Records API...');
      
      // Import the medical records API
      const { medicalRecordsAPI } = await import('../services/ehrbase-medical-records-api');
      
      // Test getting all patients
      const patients = await medicalRecordsAPI.getAllPatients();
      console.log('Medical Records API test - Patients:', patients);
      
      if (patients && patients.length > 0) {
        setTestResult(`Success! Connected to Medical Records API. Found ${patients.length} patients.`);
        
        // Show first few patient names
        const patientNames = patients.slice(0, 3).map(p => p.patient.name).join(', ');
        console.log('First few patients:', patientNames);
      } else {
        setTestResult('Connected to Medical Records API but no patients found.');
      }
    } catch (error) {
      setTestResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        EHR Integration
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Epic FHIR Connection
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Connect to Epic EHR systems using SMART on FHIR to access patient data.
            </Typography>
            <EpicLaunch />
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Patient Search
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Search for patients in connected EHR systems and import their data.
            </Typography>
            <button
              onClick={() => setSearchOpen(true)}
              style={{
                padding: '10px 20px',
                backgroundColor: '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Open Patient Search
            </button>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Active Integration: EHRBASE
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Status:</strong> Connected via Backend Proxy
              </Typography>
              <Typography variant="body2">
                <strong>EHRBASE:</strong> https://294c4163c972.ngrok.app/ehrbase
              </Typography>
              <Typography variant="body2">
                <strong>Medical Records API:</strong> https://859574eed9a9.ngrok.app/api
              </Typography>
              <Typography variant="body2">
                <strong>Proxy:</strong> {process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/ehrbase/proxy
              </Typography>
              <Typography variant="body2">
                <strong>System Type:</strong> EHRBASE openEHR CDR
              </Typography>
              <Typography variant="body2">
                <strong>Authentication:</strong> None (Open Access)
              </Typography>
              <Typography variant="body2">
                <strong>API Standard:</strong> openEHR REST API v1
              </Typography>
            </Box>
            
            <Typography variant="body2" sx={{ mt: 3, mb: 1 }}>
              <strong>Other Available Integrations:</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Epic FHIR (SMART on FHIR OAuth2)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Generic FHIR Server
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Cerner PowerChart
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Button 
                variant="contained" 
                color="secondary"
                onClick={testMedicalRecordsAPI}
                disabled={testing}
                sx={{ mr: 2 }}
              >
                {testing ? 'Testing...' : 'Test Medical Records API'}
              </Button>
              <Button 
                variant="outlined" 
                onClick={testEHRBaseConnection}
                disabled={testing}
                sx={{ mr: 2 }}
              >
                {testing ? 'Testing...' : 'Test API Connection'}
              </Button>
              <Button 
                variant="contained" 
                color="primary"
                onClick={testPatientSearch}
                disabled={testing}
                sx={{ mr: 2 }}
              >
                {testing ? 'Testing...' : 'Test Patient Search'}
              </Button>
              <Button 
                variant="outlined" 
                onClick={testFHIRConnection}
                disabled={testing}
                sx={{ mr: 2 }}
              >
                Test FHIR Connection
              </Button>
              <Button 
                variant="contained" 
                onClick={startOAuth2Flow}
                sx={{ mr: 2 }}
              >
                Start OAuth2 (Epic)
              </Button>
              {testResult && (
                <Alert 
                  severity={testResult.startsWith('Success') ? 'success' : 'error'}
                  sx={{ mt: 2 }}
                >
                  {testResult}
                </Alert>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <PatientSearch 
        open={searchOpen} 
        onClose={() => setSearchOpen(false)}
        onPatientSelect={(patient) => {
          console.log('Selected patient:', patient);
          setSearchOpen(false);
        }}
      />
    </Box>
  );
}

export default EHRIntegrationPage;