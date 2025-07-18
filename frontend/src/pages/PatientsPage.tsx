import React, { useState } from 'react';
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
  InputAdornment
} from '@mui/material';
import { 
  Search as SearchIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';

interface Patient {
  id: string;
  name: string;
  dateOfBirth: string;
  mrn: string;
  lastVisit: string;
  provider: string;
}

function PatientsPage() {
  const [searchTerm, setSearchTerm] = useState('');

  // Mock data - in real app, this would come from API
  const patients: Patient[] = [
    {
      id: '1',
      name: 'John Doe',
      dateOfBirth: '1980-05-15',
      mrn: 'MRN001234',
      lastVisit: '2024-01-10',
      provider: 'Dr. Smith'
    },
    {
      id: '2',
      name: 'Jane Smith',
      dateOfBirth: '1992-08-22',
      mrn: 'MRN001235',
      lastVisit: '2024-01-08',
      provider: 'Dr. Johnson'
    },
    {
      id: '3',
      name: 'Robert Johnson',
      dateOfBirth: '1975-03-10',
      mrn: 'MRN001236',
      lastVisit: '2024-01-05',
      provider: 'Dr. Williams'
    },
    {
      id: '4',
      name: 'Maria Garcia',
      dateOfBirth: '1988-11-30',
      mrn: 'MRN001237',
      lastVisit: '2024-01-03',
      provider: 'Dr. Brown'
    },
    {
      id: '5',
      name: 'David Lee',
      dateOfBirth: '1965-07-18',
      mrn: 'MRN001238',
      lastVisit: '2023-12-28',
      provider: 'Dr. Davis'
    }
  ];

  const filteredPatients = patients.filter(patient =>
    patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.mrn.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Patients
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => console.log('Add new patient')}
        >
          Add New Patient
        </Button>
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

      {/* Patients Table */}
      <TableContainer component={Paper} elevation={2}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Date of Birth</TableCell>
              <TableCell>MRN</TableCell>
              <TableCell>Last Visit</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredPatients.map((patient) => (
              <TableRow key={patient.id} hover>
                <TableCell>{patient.name}</TableCell>
                <TableCell>{patient.dateOfBirth}</TableCell>
                <TableCell>{patient.mrn}</TableCell>
                <TableCell>{patient.lastVisit}</TableCell>
                <TableCell>{patient.provider}</TableCell>
                <TableCell align="right">
                  <IconButton 
                    size="small" 
                    color="primary"
                    onClick={() => console.log('View patient', patient.id)}
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
      </TableContainer>

      {filteredPatients.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="textSecondary">
            No patients found matching your search criteria.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default PatientsPage;