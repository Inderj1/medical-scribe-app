import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  IconButton,
  Tooltip,
  Divider,
  Chip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PersonIcon from '@mui/icons-material/Person';
import ErrorIcon from '@mui/icons-material/Error';

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

interface VitalItemProps {
  label: string;
  value: string | number;
  unit?: string;
  isAbnormal?: boolean;
}

const VitalItem: React.FC<VitalItemProps> = ({ label, value, unit = '', isAbnormal = false }) => {
  return (
    <Box 
      sx={{ 
        textAlign: 'center',
        p: 1.5,
        bgcolor: '#f8f9fa',
        borderRadius: 1,
        position: 'relative',
        minHeight: 70,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center'
      }}
    >
      {isAbnormal && (
        <Box
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: '#dc3545'
          }}
        />
      )}
      <Typography 
        variant="h5" 
        sx={{ 
          fontWeight: 600,
          color: '#212529',
          lineHeight: 1.2
        }}
      >
        {value}{unit}
      </Typography>
      <Typography 
        variant="caption" 
        sx={{ 
          color: 'text.secondary',
          fontSize: '0.7rem',
          mt: 0.5
        }}
      >
        {label}
      </Typography>
    </Box>
  );
};

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

  // Recent labs data (mock)
  const recentLabs = [
    { name: 'Sodium', value: '128 mEq/L', range: '136-145', isLow: true, isHigh: false },
    { name: 'WBC', value: '8.2 K/uL', range: '4.5-11.0', isLow: false, isHigh: false },
    { name: 'Hemoglobin', value: '13.1 g/dL', range: '13.5-17.5', isLow: true, isHigh: false }
  ];

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

      <Box sx={{ p: 2 }}>
        {/* Patient Info Grid */}
        <Grid container spacing={1.5} sx={{ mb: 2 }}>
          <Grid item xs={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                CHIEF COMPLAINT
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                {encounter.chief_complaint}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                REFERRING PHYSICIAN
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                {encounter.referring_physician || 'Not specified'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                SMOKING HISTORY
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                {patient.smoking_history || 'Unknown'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                ALLERGIES
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5 }}>
                {patient.allergies || 'NKDA'}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* Current Vitals */}
        <Typography 
          variant="subtitle2" 
          sx={{ 
            fontWeight: 600,
            color: 'text.secondary',
            mb: 1.5
          }}
        >
          Current Vitals
        </Typography>
        
        <Grid container spacing={1.5}>
          <Grid item xs={4}>
            <VitalItem 
              label="SpO2" 
              value={vitals.oxygen_saturation} 
              unit="%" 
              isAbnormal={isOxygenLow}
            />
          </Grid>
          <Grid item xs={4}>
            <VitalItem 
              label="BP" 
              value={vitals.blood_pressure} 
              isAbnormal={isBPHigh}
            />
          </Grid>
          <Grid item xs={4}>
            <VitalItem 
              label="Temp" 
              value={vitals.temperature} 
              unit="°F" 
            />
          </Grid>
          <Grid item xs={4}>
            <VitalItem 
              label="HR" 
              value={vitals.heart_rate} 
              unit=" bpm"
            />
          </Grid>
          <Grid item xs={4}>
            <VitalItem 
              label="RR" 
              value={vitals.respiratory_rate} 
              isAbnormal={isRespRateHigh}
            />
          </Grid>
          <Grid item xs={4}>
            <VitalItem 
              label="Pain" 
              value={vitals.pain_level} 
            />
          </Grid>
        </Grid>

        {/* Recent Labs */}
        <Typography 
          variant="subtitle2" 
          sx={{ 
            fontWeight: 600,
            color: 'text.secondary',
            mt: 3,
            mb: 1.5
          }}
        >
          Recent Labs
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {recentLabs.map((lab, index) => (
            <Box
              key={lab.name}
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 1,
                borderBottom: index < recentLabs.length - 1 ? 1 : 0,
                borderColor: '#f8f9fa'
              }}
            >
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                {lab.name}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 500,
                    color: lab.isLow || lab.isHigh ? '#dc3545' : 'text.primary'
                  }}
                >
                  {lab.value} {lab.isLow && '↓'} {lab.isHigh && '↑'}
                </Typography>
                {(lab.isLow || lab.isHigh) && (
                  <Tooltip title={`Normal range: ${lab.range}`}>
                    <ErrorIcon sx={{ fontSize: 16, color: '#dc3545' }} />
                  </Tooltip>
                )}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Paper>
  );
};

export default PatientSummaryVitals;