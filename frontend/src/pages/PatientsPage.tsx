import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow,
  TextField,
  Button,
  IconButton,
  InputAdornment,
  CircularProgress,
  Alert,
  Snackbar
} from '@mui/material';
import { 
  Search as SearchIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  Sync as SyncIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { usePatient } from '../contexts/PatientContext';
import { ehrbaseAPI } from '../services/ehrbase-api';

interface Patient {
  id: string;
  ehr_id?: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  date_of_birth: string;
  mrn: string;
  gender: string;
  phone?: string;
  email?: string;
  last_visit?: string;
  last_provider?: string;
}

function PatientsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setSelectedPatient, setSelectedEncounter } = usePatient();

  // Fetch patients directly from EHRBase API
  const fetchPatients = async (search?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Get patients from EHRBase API
      const ehrPatients = await ehrbaseAPI.searchPatients(search ? { 
        firstName: search,
        lastName: search 
      } : undefined);
      
      // Transform EHRBase patient data to our format
      const transformedPatients: Patient[] = ehrPatients.map((ehrPatient: any) => {
        const patientData = ehrPatient.patient || {};
        const nameParts = (patientData.name || '').split(' ');
        const firstName = nameParts[0] || '';
        const lastName = nameParts.slice(1).join(' ') || '';
        
        return {
          id: ehrPatient.ehr_id,
          ehr_id: ehrPatient.ehr_id,
          first_name: firstName,
          last_name: lastName,
          full_name: patientData.name,
          date_of_birth: patientData.date_of_birth || '',
          mrn: patientData.external_ref?.id || `MRN-${ehrPatient.ehr_id.substring(0, 8)}`,
          gender: patientData.gender || '',
          phone: '',
          email: ''
        };
      });
      
      setPatients(transformedPatients);
    } catch (err) {
      console.error('Error fetching patients:', err);
      setError('Failed to load patients. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Load patients from EHRBase
  const syncPatients = async () => {
    try {
      setSyncing(true);
      setError(null);
      
      // Just refresh the patient list from EHRBase
      await fetchPatients();
      setSuccessMessage('Successfully loaded patients from EHRBase');
      
    } catch (err) {
      console.error('Error loading patients:', err);
      setError('Failed to load patients from EHRBase. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchPatients();
  }, []);

  // Search with debounce
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (searchTerm) {
        fetchPatients(searchTerm);
      } else {
        fetchPatients();
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]);

  const handleViewPatient = (patient: Patient) => {
    // Set patient in context with both id and ehr_id
    setSelectedPatient({
      id: patient.ehr_id || patient.id,  // Use ehr_id as the id for EHRBase patients
      ehr_id: patient.ehr_id || '',  // Provide empty string as default if undefined
      mrn: patient.mrn,
      first_name: patient.first_name,
      last_name: patient.last_name,
      date_of_birth: patient.date_of_birth,
      gender: patient.gender,
      phone: patient.phone,
      email: patient.email
    });
    
    // Clear any existing encounter
    setSelectedEncounter(null);
    
    // Navigate to patient details or clinical notes
    navigate('/clinical-notes');
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Patients
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={syncing ? <CircularProgress size={20} /> : <SyncIcon />}
            onClick={syncPatients}
            disabled={syncing}
          >
            {syncing ? 'Loading...' : 'Refresh from EHRBase'}
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => console.log('Add new patient')}
          >
            Add New Patient
          </Button>
        </Box>
      </Box>

      {/* Search Bar */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search by patient name or MRN..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      {/* Error/Success Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Patients Table */}
      <TableContainer component={Paper} elevation={2}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Gender</TableCell>
                <TableCell>Date of Birth</TableCell>
                <TableCell>MRN</TableCell>
                <TableCell>EHR ID</TableCell>
                <TableCell>Last Visit</TableCell>
                <TableCell>Provider</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {patients.map((patient) => (
                <TableRow key={patient.id} hover>
                  <TableCell>{patient.full_name || `${patient.first_name} ${patient.last_name}`}</TableCell>
                  <TableCell>{patient.gender}</TableCell>
                  <TableCell>{patient.date_of_birth}</TableCell>
                  <TableCell>{patient.mrn}</TableCell>
                  <TableCell>{patient.ehr_id || '-'}</TableCell>
                  <TableCell>{patient.last_visit ? new Date(patient.last_visit).toLocaleDateString() : '-'}</TableCell>
                  <TableCell>{patient.last_provider || '-'}</TableCell>
                  <TableCell align="right">
                    <IconButton 
                      size="small" 
                      color="primary"
                      onClick={() => handleViewPatient(patient)}
                    >
                      <VisibilityIcon />
                    </IconButton>
                    <IconButton 
                      size="small" 
                      color="primary"
                      onClick={() => console.log('Edit patient', patient.id)}
                    >
                      <EditIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      {!loading && patients.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="textSecondary">
            {searchTerm 
              ? 'No patients found matching your search criteria.'
              : 'No patients found. Click "Refresh from EHRBase" to load patients.'}
          </Typography>
        </Box>
      )}

      {/* Success Snackbar */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSuccessMessage(null)} severity="success">
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default PatientsPage;