import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  InputAdornment,
  IconButton,
  Avatar,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  CircularProgress,
  Alert
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import PersonIcon from '@mui/icons-material/Person';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import DescriptionIcon from '@mui/icons-material/Description';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CloseIcon from '@mui/icons-material/Close';
import NoteAddIcon from '@mui/icons-material/NoteAdd';
import { ehrApi } from '../services/ehr';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { usePatient } from '../contexts/PatientContext';

interface Patient {
  ehr_id: string;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string;
  email?: string;
}

interface Encounter {
  id: string;
  patient_id: string;
  encounter_date: string;
  chief_complaint: string;
  provider_name: string;
  encounter_type: string;
  status: string;
  vitals?: any;
  diagnosis?: string[];
  notes?: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`patient-tabpanel-${index}`}
      aria-labelledby={`patient-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function PatientRecordsPage() {
  const navigate = useNavigate();
  const { setSelectedPatient: setContextPatient, setSelectedEncounter: setContextEncounter, setRecentVitals } = usePatient();
  
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [selectedEncounter, setSelectedEncounter] = useState<Encounter | null>(null);
  const initialLoadRef = useRef(false);

  useEffect(() => {
    // Prevent duplicate calls in React StrictMode or on hot reload
    console.log('PatientRecordsPage useEffect triggered, initialLoadRef.current:', initialLoadRef.current);
    if (!initialLoadRef.current) {
      initialLoadRef.current = true;
      console.log('Starting initial patient search...');
      searchPatients();
    } else {
      console.log('Skipping duplicate patient search call');
    }
  }, []);

  const searchPatients = async (searchQuery?: string) => {
    console.log(`searchPatients called with searchQuery: "${searchQuery}", loading: ${loading}`);
    
    // Prevent multiple simultaneous calls
    if (loading) {
      console.log('Search already in progress, skipping...');
      return;
    }

    console.log('Starting patient search...');
    setLoading(true);
    setError(null);
    try {
      const searchParams = searchQuery ? { firstName: searchQuery } : {};
      console.log('Calling ehrApi.searchPatients with params:', searchParams);
      const results = await ehrApi.searchPatients({
        organizationId: 'ehrbase',
        ...searchParams
      });
      console.log(`Patient search completed, found ${results.length} patients`);
      setPatients(results);
    } catch (error) {
      console.error('Failed to search patients:', error);
      setError('Failed to load patients. Please try again.');
    } finally {
      setLoading(false);
      console.log('Patient search finished');
    }
  };

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    searchPatients(searchTerm);
  };

  const handlePatientSelect = async (patient: Patient) => {
    setSelectedPatient(patient);
    setDialogOpen(true);
    setTabValue(0);
    
    // Fetch patient encounters
    try {
      // Mock encounters data - replace with actual API call
      const mockEncounters: Encounter[] = [
        {
          id: '1',
          patient_id: patient.ehr_id,
          encounter_date: '2024-03-15T10:30:00',
          chief_complaint: 'Chest pain and shortness of breath',
          provider_name: 'Dr. Smith',
          encounter_type: 'Emergency',
          status: 'Completed',
          vitals: {
            blood_pressure: '150/95',
            heart_rate: '95',
            temperature: '98.6°F',
            oxygen_saturation: '98%'
          },
          diagnosis: ['STEMI', 'Hypertension'],
          notes: 'Patient presented with acute chest pain. EKG showed ST elevation. Admitted for cardiac catheterization.'
        },
        {
          id: '2',
          patient_id: patient.ehr_id,
          encounter_date: '2024-02-20T14:00:00',
          chief_complaint: 'Follow-up visit',
          provider_name: 'Dr. Johnson',
          encounter_type: 'Outpatient',
          status: 'Completed',
          vitals: {
            blood_pressure: '130/80',
            heart_rate: '72',
            temperature: '98.4°F'
          },
          diagnosis: ['Hypertension - controlled'],
          notes: 'Blood pressure well controlled on current medications.'
        }
      ];
      setEncounters(mockEncounters);
    } catch (error) {
      console.error('Failed to fetch encounters:', error);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy');
    } catch {
      return dateString;
    }
  };

  const formatDateTime = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy h:mm a');
    } catch {
      return dateString;
    }
  };

  const getGenderIcon = (gender: string) => {
    const genderLower = gender.toLowerCase();
    return genderLower === 'male' || genderLower === 'female' ? genderLower : 'other';
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'in-progress':
        return 'warning';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleStartClinicalNote = (patient: Patient) => {
    // Calculate age from date of birth
    const birthDate = new Date(patient.date_of_birth);
    const today = new Date();
    const age = today.getFullYear() - birthDate.getFullYear();
    
    // Set patient data in context
    setContextPatient({
      ...patient,
      age,
      allergies: 'NKDA', // Default value, should be fetched from patient record
      smoking_history: 'Unknown' // Default value, should be fetched from patient record
    });

    // Set most recent encounter and vitals if available
    if (encounters.length > 0) {
      const latestEncounter = encounters[0];
      setContextEncounter(latestEncounter);
      
      if (latestEncounter.vitals) {
        setRecentVitals(latestEncounter.vitals);
      }
    }

    // Navigate to clinical notes page
    navigate('/clinical-notes');
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Patient Records
      </Typography>

      {/* Search Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <form onSubmit={handleSearch}>
            <TextField
              fullWidth
              placeholder="Search patients by name, MRN, or date of birth..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <Button type="submit" variant="contained" disabled={loading}>
                      Search
                    </Button>
                  </InputAdornment>
                ),
              }}
            />
          </form>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      )}

      {/* Patients Grid */}
      {!loading && patients.length > 0 && (
        <Grid container spacing={3}>
          {patients.map((patient) => (
            <Grid item xs={12} sm={6} md={4} key={patient.ehr_id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  '&:hover': { 
                    boxShadow: 6,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.3s'
                  }
                }}
                onClick={() => handlePatientSelect(patient)}
              >
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                      <PersonIcon />
                    </Avatar>
                    <Box flex={1}>
                      <Typography variant="h6">
                        {patient.first_name} {patient.last_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        MRN: {patient.mrn}
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Divider sx={{ my: 1.5 }} />
                  
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <CalendarTodayIcon fontSize="small" color="action" />
                    <Typography variant="body2">
                      DOB: {formatDate(patient.date_of_birth)}
                    </Typography>
                  </Box>
                  
                  <Box display="flex" alignItems="center" gap={1}>
                    <Chip 
                      label={patient.gender} 
                      size="small" 
                      color={patient.gender.toLowerCase() === 'male' ? 'info' : 'secondary'}
                    />
                    {patient.phone && (
                      <Typography variant="body2" color="text.secondary">
                        {patient.phone}
                      </Typography>
                    )}
                  </Box>
                  
                  <Box display="flex" gap={1} mt={2}>
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<NoteAddIcon />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartClinicalNote(patient);
                      }}
                      sx={{ 
                        flex: 1,
                        textTransform: 'none',
                        bgcolor: '#28a745',
                        '&:hover': {
                          bgcolor: '#218838'
                        }
                      }}
                    >
                      Start Clinical Note
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePatientSelect(patient);
                      }}
                      sx={{ textTransform: 'none' }}
                    >
                      View Details
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* No Results */}
      {!loading && patients.length === 0 && searchTerm && (
        <Box textAlign="center" py={4}>
          <Typography variant="h6" color="text.secondary">
            No patients found matching "{searchTerm}"
          </Typography>
        </Box>
      )}

      {/* Patient Details Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedPatient && (
          <>
            <DialogTitle>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box display="flex" alignItems="center" gap={2}>
                  <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                    <PersonIcon />
                  </Avatar>
                  <Box>
                    <Typography variant="h5">
                      {selectedPatient.first_name} {selectedPatient.last_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      MRN: {selectedPatient.mrn} | DOB: {formatDate(selectedPatient.date_of_birth)}
                    </Typography>
                  </Box>
                </Box>
                <Box display="flex" alignItems="center" gap={2}>
                  <Button
                    variant="contained"
                    startIcon={<NoteAddIcon />}
                    onClick={() => {
                      handleStartClinicalNote(selectedPatient);
                      setDialogOpen(false);
                    }}
                    sx={{ 
                      textTransform: 'none',
                      bgcolor: '#28a745',
                      '&:hover': {
                        bgcolor: '#218838'
                      }
                    }}
                  >
                    Start Clinical Note
                  </Button>
                  <IconButton onClick={() => setDialogOpen(false)}>
                    <CloseIcon />
                  </IconButton>
                </Box>
              </Box>
            </DialogTitle>
            
            <DialogContent>
              <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
                <Tab label="Overview" />
                <Tab label="Encounters" />
                <Tab label="Medical History" />
              </Tabs>

              <TabPanel value={tabValue} index={0}>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Patient Information
                    </Typography>
                    <List>
                      <ListItem>
                        <ListItemText 
                          primary="Full Name"
                          secondary={`${selectedPatient.first_name} ${selectedPatient.last_name}`}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="Date of Birth"
                          secondary={formatDate(selectedPatient.date_of_birth)}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="Gender"
                          secondary={selectedPatient.gender}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="MRN"
                          secondary={selectedPatient.mrn}
                        />
                      </ListItem>
                    </List>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Contact Information
                    </Typography>
                    <List>
                      <ListItem>
                        <ListItemText 
                          primary="Phone"
                          secondary={selectedPatient.phone || 'Not provided'}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="Email"
                          secondary={selectedPatient.email || 'Not provided'}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText 
                          primary="EHR ID"
                          secondary={selectedPatient.ehr_id}
                        />
                      </ListItem>
                    </List>
                  </Grid>
                </Grid>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell>Chief Complaint</TableCell>
                        <TableCell>Provider</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {encounters.map((encounter) => (
                        <TableRow key={encounter.id}>
                          <TableCell>{formatDateTime(encounter.encounter_date)}</TableCell>
                          <TableCell>
                            <Chip 
                              label={encounter.encounter_type} 
                              size="small"
                              color={encounter.encounter_type === 'Emergency' ? 'error' : 'primary'}
                            />
                          </TableCell>
                          <TableCell>{encounter.chief_complaint}</TableCell>
                          <TableCell>{encounter.provider_name}</TableCell>
                          <TableCell>
                            <Chip 
                              label={encounter.status} 
                              size="small"
                              color={getStatusColor(encounter.status) as any}
                            />
                          </TableCell>
                          <TableCell>
                            <Button 
                              size="small"
                              onClick={() => setSelectedEncounter(encounter)}
                            >
                              View Details
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                
                {/* Encounter Details */}
                {selectedEncounter && (
                  <Card sx={{ mt: 3 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Encounter Details - {formatDateTime(selectedEncounter.encounter_date)}
                      </Typography>
                      
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle2" color="text.secondary">
                            Vital Signs
                          </Typography>
                          {selectedEncounter.vitals && (
                            <List dense>
                              <ListItem>
                                <ListItemText 
                                  primary="Blood Pressure"
                                  secondary={selectedEncounter.vitals.blood_pressure}
                                />
                              </ListItem>
                              <ListItem>
                                <ListItemText 
                                  primary="Heart Rate"
                                  secondary={`${selectedEncounter.vitals.heart_rate} bpm`}
                                />
                              </ListItem>
                              <ListItem>
                                <ListItemText 
                                  primary="Temperature"
                                  secondary={selectedEncounter.vitals.temperature}
                                />
                              </ListItem>
                              {selectedEncounter.vitals.oxygen_saturation && (
                                <ListItem>
                                  <ListItemText 
                                    primary="O2 Saturation"
                                    secondary={selectedEncounter.vitals.oxygen_saturation}
                                  />
                                </ListItem>
                              )}
                            </List>
                          )}
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle2" color="text.secondary">
                            Diagnosis
                          </Typography>
                          {selectedEncounter.diagnosis && (
                            <Box mt={1}>
                              {selectedEncounter.diagnosis.map((diag, index) => (
                                <Chip 
                                  key={index}
                                  label={diag}
                                  sx={{ mr: 1, mb: 1 }}
                                />
                              ))}
                            </Box>
                          )}
                          
                          {selectedEncounter.notes && (
                            <Box mt={2}>
                              <Typography variant="subtitle2" color="text.secondary">
                                Clinical Notes
                              </Typography>
                              <Typography variant="body2" sx={{ mt: 1 }}>
                                {selectedEncounter.notes}
                              </Typography>
                            </Box>
                          )}
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                )}
              </TabPanel>

              <TabPanel value={tabValue} index={2}>
                <Typography variant="body1" color="text.secondary">
                  Medical history information will be displayed here when available.
                </Typography>
              </TabPanel>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
}

export default PatientRecordsPage;