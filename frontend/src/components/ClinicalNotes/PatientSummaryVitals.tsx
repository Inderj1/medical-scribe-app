import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Divider,
  Chip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PersonIcon from '@mui/icons-material/Person';

interface Vitals {
  blood_pressure: string;
  heart_rate: number;
  respiratory_rate: number;
  temperature: number;
  oxygen_saturation: number;
  pain_level: string;
}

interface PatientSummaryVitalsProps {
  patient: {
    id: string;
    first_name: string;
    last_name: string;
    gender: string;
    smoking_history?: string;
    allergies?: string;
  };
  encounter: {
    chief_complaint: string;
    referring_physician?: string;
  };
  vitals: Vitals;
}

const PatientSummaryVitals: React.FC<PatientSummaryVitalsProps> = ({ 
  patient, 
  encounter, 
  vitals 
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshVitals = async () => {
    setIsRefreshing(true);
    // Simulate vital refresh
    setTimeout(() => {
      setIsRefreshing(false);
    }, 1000);
  };

  // Check for abnormal vitals
  const isOxygenLow = vitals.oxygen_saturation < 95;
  const isRespRateHigh = vitals.respiratory_rate > 20;
  const isBPHigh = parseInt(vitals.blood_pressure.split('/')[0]) > 140;


  return (
    <Paper
      elevation={2}
      sx={{
        bgcolor: 'white',
        borderRadius: 2,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <Box
        sx={{
          bgcolor: '#f8f9fa',
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Patient Summary & Vitals
          </Typography>
        </Box>
        <Tooltip title="Refresh Vitals">
          <IconButton 
            size="small" 
            onClick={handleRefreshVitals}
            disabled={isRefreshing}
            sx={{ 
              animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' }
              }
            }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ p: 1.5 }}>
        {/* Patient Info - Single Row Compact */}
        <Box sx={{ mb: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip 
            label={`CC: ${encounter.chief_complaint}`} 
            size="small" 
            sx={{ fontSize: '0.7rem' }}
          />
          <Chip 
            label={`Allergies: ${patient.allergies || 'NKDA'}`} 
            size="small" 
            color={patient.allergies && patient.allergies !== 'NKDA' ? 'warning' : 'default'}
            sx={{ fontSize: '0.7rem' }}
          />
          {patient.smoking_history && (
            <Chip 
              label={`Smoking: ${patient.smoking_history}`} 
              size="small" 
              color="error"
              sx={{ fontSize: '0.7rem' }}
            />
          )}
        </Box>

        {/* Current Vitals - Horizontal Display */}
        <Box sx={{ 
          display: 'flex', 
          gap: 1, 
          flexWrap: 'wrap',
          p: 1,
          bgcolor: '#f8f9fa',
          borderRadius: 1
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">SpO2:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600, color: isOxygenLow ? '#dc3545' : 'inherit' }}>
              {vitals.oxygen_saturation}%
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">BP:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600, color: isBPHigh ? '#dc3545' : 'inherit' }}>
              {vitals.blood_pressure}
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">HR:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {vitals.heart_rate} bpm
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">Temp:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {vitals.temperature}°F
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">RR:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600, color: isRespRateHigh ? '#dc3545' : 'inherit' }}>
              {vitals.respiratory_rate}
            </Typography>
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary">Pain:</Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {vitals.pain_level}
            </Typography>
          </Box>
        </Box>

      </Box>
    </Paper>
  );
};

export default PatientSummaryVitals;