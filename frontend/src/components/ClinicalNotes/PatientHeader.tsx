import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Paper,
  Divider
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
    smoking_history?: string;
    allergies?: string;
  };
  encounter: {
    encounter_date: Date | string;
    risk_factors?: string[];
    chief_complaint: string;
  };
  vitals: {
    blood_pressure: string;
    heart_rate: number;
    respiratory_rate: number;
    temperature: number;
    oxygen_saturation: number;
    pain_level: string;
  };
}

const PatientHeader: React.FC<PatientHeaderProps> = ({ patient, encounter, vitals }) => {
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

  // Check for abnormal vitals
  const isOxygenLow = vitals.oxygen_saturation < 95;
  const isRespRateHigh = vitals.respiratory_rate > 20;
  const isBPHigh = parseInt(vitals.blood_pressure.split('/')[0]) > 140;

  return (
    <Paper 
      elevation={1}
      sx={{
        bgcolor: 'white',
        borderBottom: 1,
        borderColor: 'divider',
        px: 3,
        py: 1,
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        zIndex: 100
      }}
    >
      {/* Single Line: All Patient Info */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
        {/* Left Side: Patient Info + Vitals + Summary */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, overflow: 'hidden' }}>
          {/* Patient Basic Info */}
          <Typography 
            variant="body2" 
            sx={{ 
              fontWeight: 600,
              color: 'text.secondary',
              fontSize: '0.75rem'
            }}
          >
            MRN: #{patient.mrn}
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.9rem' }}>
            {patient.first_name} {patient.last_name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            {patient.gender}, {patient.age || 'Pending'}
          </Typography>
          
          {/* Risk Badges - Slightly Larger */}
          {getRiskBadges().map((badge, index) => (
            React.cloneElement(badge, {
              key: index,
              sx: { 
                ...badge.props.sx, 
                fontSize: '0.65rem', 
                height: '20px',
                '& .MuiChip-label': { px: 0.5 }
              }
            })
          ))}
          
          {/* Patient Summary */}
          <Typography variant="body2" sx={{ fontSize: '0.72rem', mx: 0.5 }}>
            CC: {encounter.chief_complaint}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', mx: 0.5 }}>
            Allergies: {patient.allergies || 'NKDA'}
          </Typography>
          {patient.smoking_history && (
            <Typography variant="body2" sx={{ fontSize: '0.72rem', color: '#dc3545', mx: 0.5 }}>
              Smoking: {patient.smoking_history}
            </Typography>
          )}
          
          {/* Vitals */}
          <Typography variant="body2" sx={{ fontSize: '0.72rem', color: isOxygenLow ? '#dc3545' : 'inherit', mx: 0.3 }}>
            SpO2: {vitals.oxygen_saturation}%
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', color: isBPHigh ? '#dc3545' : 'inherit', mx: 0.3 }}>
            BP: {vitals.blood_pressure}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', mx: 0.3 }}>
            HR: {vitals.heart_rate}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', mx: 0.3 }}>
            Temp: {vitals.temperature}°F
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', color: isRespRateHigh ? '#dc3545' : 'inherit', mx: 0.3 }}>
            RR: {vitals.respiratory_rate}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.72rem', mx: 0.3 }}>
            Pain: {vitals.pain_level}
          </Typography>
        </Box>
        
        {/* Right Side: Encounter Info + Recording Status */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            {format(new Date(encounter.encounter_date), 'MMM dd, h:mm a')}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
            <FiberManualRecordIcon 
              sx={{ 
                fontSize: 12, 
                color: '#28a745' 
              }} 
            />
            <Typography variant="body2" sx={{ color: '#28a745', fontWeight: 500, fontSize: '0.72rem' }}>
              Recording
            </Typography>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default PatientHeader;