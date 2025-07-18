import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import SyncIcon from '@mui/icons-material/Sync';
import CloseIcon from '@mui/icons-material/Close';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from 'date-fns';
import { ehrApi } from '../../services/ehr';

interface PatientSearchProps {
  open: boolean;
  onClose: () => void;
  onPatientSelect: (patient: any) => void;
  organizationId?: string;
}

interface SearchParams {
  firstName?: string;
  lastName?: string;
  dateOfBirth?: string;
  mrn?: string;
}

const PatientSearch: React.FC<PatientSearchProps> = ({
  open,
  onClose,
  onPatientSelect,
  organizationId,
}) => {
  const [searchParams, setSearchParams] = useState<SearchParams>({});
  const [searchTriggered, setSearchTriggered] = useState(false);

  // Search patients query
  const { data: patients, isLoading: isSearching, error: searchError, refetch } = useQuery({
    queryKey: ['fhir-patient-search', searchParams],
    queryFn: () => ehrApi.searchPatients({
      organizationId: organizationId || 'default',
      ...searchParams,
    }),
    enabled: searchTriggered,
  });

  // Sync patient mutation - simplified for FHIR direct integration
  const syncPatientMutation = useMutation({
    mutationFn: (ehrPatientId: string) => {
      // For FHIR integration, we can directly select the patient
      const patient = patients?.find(p => p.ehr_id === ehrPatientId);
      if (patient) {
        return Promise.resolve({
          success: true,
          patient_id: patient.ehr_id,
          mrn: patient.mrn,
          synced_data: {
            demographics: true,
            allergies: 0,
            medications: 0,
            conditions: 0,
          }
        });
      }
      return Promise.reject(new Error('Patient not found'));
    },
    onSuccess: (data, ehrPatientId) => {
      const patient = patients?.find(p => p.ehr_id === ehrPatientId);
      if (patient) {
        onPatientSelect({
          ...patient,
          localId: data.patient_id,
        });
      }
      onClose();
    },
  });

  const handleSearch = () => {
    if (searchParams.firstName || searchParams.lastName || searchParams.dateOfBirth || searchParams.mrn) {
      setSearchTriggered(true);
      refetch();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSyncPatient = (patient: any) => {
    syncPatientMutation.mutate(patient.ehr_id);
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MM/dd/yyyy');
    } catch {
      return dateString;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Search EHR for Patient</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Search for patients in your connected EHR system. At least one search field is required.
          </Typography>
          
          <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2} sx={{ mt: 2 }}>
            <TextField
              label="First Name"
              value={searchParams.firstName || ''}
              onChange={(e) => setSearchParams({ ...searchParams, firstName: e.target.value })}
              onKeyPress={handleKeyPress}
              size="small"
            />
            <TextField
              label="Last Name"
              value={searchParams.lastName || ''}
              onChange={(e) => setSearchParams({ ...searchParams, lastName: e.target.value })}
              onKeyPress={handleKeyPress}
              size="small"
            />
            <TextField
              label="Date of Birth"
              type="date"
              value={searchParams.dateOfBirth || ''}
              onChange={(e) => setSearchParams({ ...searchParams, dateOfBirth: e.target.value })}
              onKeyPress={handleKeyPress}
              InputLabelProps={{ shrink: true }}
              size="small"
            />
            <TextField
              label="MRN"
              value={searchParams.mrn || ''}
              onChange={(e) => setSearchParams({ ...searchParams, mrn: e.target.value })}
              onKeyPress={handleKeyPress}
              size="small"
            />
          </Box>
          
          <Box display="flex" justifyContent="center" sx={{ mt: 2 }}>
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              disabled={isSearching || (!searchParams.firstName && !searchParams.lastName && !searchParams.dateOfBirth && !searchParams.mrn)}
            >
              Search EHR
            </Button>
          </Box>
        </Box>

        {searchError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error searching EHR: {(searchError as Error).message}
          </Alert>
        )}

        {isSearching && (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}

        {patients && patients.length > 0 && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>MRN</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Date of Birth</TableCell>
                  <TableCell>Gender</TableCell>
                  <TableCell>Phone</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {patients.map((patient) => (
                  <TableRow key={patient.ehr_id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {patient.mrn}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {patient.first_name} {patient.last_name}
                    </TableCell>
                    <TableCell>{formatDate(patient.date_of_birth)}</TableCell>
                    <TableCell>
                      <Chip 
                        label={patient.gender} 
                        size="small" 
                        color={patient.gender === 'male' ? 'info' : 'secondary'}
                      />
                    </TableCell>
                    <TableCell>{patient.phone || '-'}</TableCell>
                    <TableCell align="center">
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<SyncIcon />}
                        onClick={() => handleSyncPatient(patient)}
                        disabled={syncPatientMutation.isPending}
                      >
                        Import
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {patients && patients.length === 0 && (
          <Alert severity="info">
            No patients found matching your search criteria.
          </Alert>
        )}

        {syncPatientMutation.isPending && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              bgcolor: 'rgba(255, 255, 255, 0.9)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1,
            }}
          >
            <CircularProgress />
            <Typography sx={{ mt: 2 }}>Importing patient data...</Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};

export default PatientSearch;