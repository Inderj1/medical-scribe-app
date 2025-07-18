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
  Chip,
  Button,
  IconButton,
  FormControl,
  Select,
  MenuItem,
  InputLabel
} from '@mui/material';
import { 
  Add as AddIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';

interface Encounter {
  id: string;
  patientName: string;
  chiefComplaint: string;
  provider: string;
  startTime: string;
  status: 'active' | 'completed' | 'draft';
  duration?: string;
}

function EncountersPage() {
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Mock data
  const encounters: Encounter[] = [
    {
      id: '1',
      patientName: 'John Doe',
      chiefComplaint: 'Annual checkup',
      provider: 'Dr. Smith',
      startTime: '2024-01-15 09:00',
      status: 'completed',
      duration: '25 min'
    },
    {
      id: '2',
      patientName: 'Jane Smith',
      chiefComplaint: 'Chest pain',
      provider: 'Dr. Johnson',
      startTime: '2024-01-15 10:30',
      status: 'active'
    },
    {
      id: '3',
      patientName: 'Robert Johnson',
      chiefComplaint: 'Follow-up - Hypertension',
      provider: 'Dr. Williams',
      startTime: '2024-01-15 11:00',
      status: 'draft'
    },
    {
      id: '4',
      patientName: 'Maria Garcia',
      chiefComplaint: 'Migraine',
      provider: 'Dr. Brown',
      startTime: '2024-01-15 14:00',
      status: 'completed',
      duration: '30 min'
    },
    {
      id: '5',
      patientName: 'David Lee',
      chiefComplaint: 'Diabetes management',
      provider: 'Dr. Davis',
      startTime: '2024-01-15 15:30',
      status: 'active'
    }
  ];

  const filteredEncounters = filterStatus === 'all' 
    ? encounters 
    : encounters.filter(e => e.status === filterStatus);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'default';
      case 'draft':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Encounters
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => console.log('Create new encounter')}
        >
          New Encounter
        </Button>
      </Box>

      {/* Filter */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Status</InputLabel>
          <Select
            value={filterStatus}
            label="Filter by Status"
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <MenuItem value="all">All Encounters</MenuItem>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="draft">Draft</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Encounters Table */}
      <TableContainer component={Paper} elevation={2}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Patient</TableCell>
              <TableCell>Chief Complaint</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Start Time</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredEncounters.map((encounter) => (
              <TableRow key={encounter.id} hover>
                <TableCell>{encounter.patientName}</TableCell>
                <TableCell>{encounter.chiefComplaint}</TableCell>
                <TableCell>{encounter.provider}</TableCell>
                <TableCell>{encounter.startTime}</TableCell>
                <TableCell>
                  <Chip 
                    label={encounter.status} 
                    color={getStatusColor(encounter.status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>{encounter.duration || '-'}</TableCell>
                <TableCell align="right">
                  {encounter.status === 'active' && (
                    <IconButton 
                      size="small" 
                      color="error"
                      onClick={() => console.log('Stop recording', encounter.id)}
                    >
                      <StopIcon />
                    </IconButton>
                  )}
                  {encounter.status === 'draft' && (
                    <IconButton 
                      size="small" 
                      color="success"
                      onClick={() => console.log('Start recording', encounter.id)}
                    >
                      <PlayArrowIcon />
                    </IconButton>
                  )}
                  <IconButton 
                    size="small" 
                    color="primary"
                    onClick={() => console.log('View notes', encounter.id)}
                  >
                    <DescriptionIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {filteredEncounters.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="textSecondary">
            No encounters found for the selected filter.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default EncountersPage;