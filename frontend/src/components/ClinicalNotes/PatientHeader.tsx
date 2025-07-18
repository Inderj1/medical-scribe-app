import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Paper
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import SmokingRoomsIcon from '@mui/icons-material/SmokingRooms';
import ErrorIcon from '@mui/icons-material/Error';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { format } from 'date-fns';

interface PatientHeaderProps {
  patient: {
    id: string;
    first_name: string;
    last_name: string;
    mrn: string;
    gender: string;
    age?: number;
  };
  encounter: {
    encounter_date: Date;
    risk_factors?: string[];
  };
}

const PatientHeader: React.FC<PatientHeaderProps> = ({ patient, encounter }) => {
  const getRiskBadges = () => {
    const badges = [];
    
    if (encounter.risk_factors?.includes('critical')) {
      badges.push(
        <Chip
          key="critical"
          icon={<ErrorIcon />}
          label="High Risk - Possible Malignancy"
          size="small"
          sx={{
            bgcolor: '#dc3545',
            color: 'white',
            '& .MuiChip-icon': { color: 'white' }
          }}
        />
      );
    }
    
    if (encounter.risk_factors?.includes('smoker')) {
      badges.push(
        <Chip
          key="smoker"
          icon={<SmokingRoomsIcon />}
          label="Active Smoker"
          size="small"
          sx={{
            bgcolor: '#ffc107',
            color: '#212529',
            '& .MuiChip-icon': { color: '#212529' }
          }}
        />
      );
    }
    
    if (encounter.risk_factors?.includes('hypertension')) {
      badges.push(
        <Chip
          key="htn"
          icon={<WarningIcon />}
          label="Hypertension"
          size="small"
          color="warning"
        />
      );
    }
    
    return badges;
  };

  return (
    <Paper 
      elevation={1}
      sx={{
        bgcolor: 'white',
        borderBottom: 1,
        borderColor: 'divider',
        px: 3,
        py: 1.5,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        zIndex: 100
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography 
            variant="body2" 
            sx={{ 
              fontWeight: 600,
              color: 'text.secondary'
            }}
          >
            MRN: #{patient.mrn}
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {patient.first_name} {patient.last_name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {patient.gender}, {patient.age ? `Age: ${patient.age}` : 'Age: Pending'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          {getRiskBadges()}
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Encounter:
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {format(encounter.encounter_date, 'MMM dd, yyyy h:mm a')}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 2 }}>
          <FiberManualRecordIcon 
            sx={{ 
              fontSize: 12, 
              color: '#28a745' 
            }} 
          />
          <Typography variant="caption" sx={{ color: '#28a745', fontWeight: 500 }}>
            Recording Active
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default PatientHeader;