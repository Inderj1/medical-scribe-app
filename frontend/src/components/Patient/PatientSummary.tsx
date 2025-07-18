import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  IconButton,
  Divider,
  Alert,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PersonIcon from '@mui/icons-material/Person';
import WarningIcon from '@mui/icons-material/Warning';
import webSocketService from '../../services/websocket';

interface Vitals {
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  heart_rate?: number;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
  pain_level?: number;
}

interface PatientSummaryProps {
  patient: {
    id: string;
    mrn: string;
    first_name: string;
    last_name: string;
    date_of_birth?: string;
    gender?: string;
  };
  encounter: {
    id: string;
    chief_complaint?: string;
    referring_physician?: string;
  };
}

const PatientSummary: React.FC<PatientSummaryProps> = ({ patient, encounter }) => {
  const [vitals, setVitals] = useState<Vitals>({});
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  useEffect(() => {
    // Listen for vitals updates
    const handleVitalsUpdate = (data: any) => {
      if (data.type === 'vitals:update') {
        setVitals(data.vitals);
        setLastUpdated(new Date());
      }
    };

    webSocketService.on('vitals:update', handleVitalsUpdate);

    return () => {
      webSocketService.off('vitals:update', handleVitalsUpdate);
    };
  }, []);

  const refreshVitals = () => {
    // Simulate vitals refresh
    setLastUpdated(new Date());
  };

  const isVitalAbnormal = (vital: string, value?: number): boolean => {
    if (!value) return false;
    
    const ranges: { [key: string]: [number, number] } = {
      oxygen_saturation: [95, 100],
      blood_pressure_systolic: [90, 140],
      blood_pressure_diastolic: [60, 90],
      heart_rate: [60, 100],
      respiratory_rate: [12, 20],
      temperature: [97.0, 99.5],
    };

    const range = ranges[vital];
    if (!range) return false;
    
    return value < range[0] || value > range[1];
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, bgcolor: '#f8f9fa', borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonIcon />
          <Typography variant="h6" fontWeight={600}>
            Patient Summary & Vitals
          </Typography>
        </Box>
        <IconButton size="small" onClick={refreshVitals}>
          <RefreshIcon />
        </IconButton>
      </Box>
      
      <Box sx={{ p: 2, flex: 1, overflow: 'auto' }}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Chief Complaint
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {encounter.chief_complaint || 'Not specified'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Referring Physician
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {encounter.referring_physician || 'Primary Care Doctor'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Patient Info
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {patient.first_name} {patient.last_name} | {patient.gender || 'Unknown'} | MRN: {patient.mrn}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Allergies
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                NKDA
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 2 }}>
          Current Vitals
        </Typography>
        
        <Grid container spacing={1.5}>
          {vitals.oxygen_saturation !== undefined && (
            <Grid item xs={4}>
              <Box sx={{ 
                bgcolor: '#f8f9fa', 
                p: 1.5, 
                borderRadius: 1, 
                textAlign: 'center',
                position: 'relative',
                border: isVitalAbnormal('oxygen_saturation', vitals.oxygen_saturation) ? '2px solid #dc3545' : 'none'
              }}>
                {isVitalAbnormal('oxygen_saturation', vitals.oxygen_saturation) && (
                  <Box sx={{ position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: '50%', bgcolor: '#dc3545' }} />
                )}
                <Typography variant="h6" fontWeight={600}>
                  {vitals.oxygen_saturation}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  SpO2
                </Typography>
              </Box>
            </Grid>
          )}
          
          {(vitals.blood_pressure_systolic !== undefined || vitals.blood_pressure_diastolic !== undefined) && (
            <Grid item xs={4}>
              <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1, textAlign: 'center' }}>
                <Typography variant="h6" fontWeight={600}>
                  {vitals.blood_pressure_systolic || '--'}/{vitals.blood_pressure_diastolic || '--'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  BP
                </Typography>
              </Box>
            </Grid>
          )}
          
          {vitals.temperature !== undefined && (
            <Grid item xs={4}>
              <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1, textAlign: 'center' }}>
                <Typography variant="h6" fontWeight={600}>
                  {vitals.temperature}°F
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Temp
                </Typography>
              </Box>
            </Grid>
          )}
          
          {vitals.heart_rate !== undefined && (
            <Grid item xs={4}>
              <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1, textAlign: 'center' }}>
                <Typography variant="h6" fontWeight={600}>
                  {vitals.heart_rate}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  HR
                </Typography>
              </Box>
            </Grid>
          )}
          
          {vitals.respiratory_rate !== undefined && (
            <Grid item xs={4}>
              <Box sx={{ 
                bgcolor: '#f8f9fa', 
                p: 1.5, 
                borderRadius: 1, 
                textAlign: 'center',
                position: 'relative',
                border: isVitalAbnormal('respiratory_rate', vitals.respiratory_rate) ? '2px solid #dc3545' : 'none'
              }}>
                {isVitalAbnormal('respiratory_rate', vitals.respiratory_rate) && (
                  <Box sx={{ position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: '50%', bgcolor: '#dc3545' }} />
                )}
                <Typography variant="h6" fontWeight={600}>
                  {vitals.respiratory_rate}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  RR
                </Typography>
              </Box>
            </Grid>
          )}
          
          {vitals.pain_level !== undefined && (
            <Grid item xs={4}>
              <Box sx={{ bgcolor: '#f8f9fa', p: 1.5, borderRadius: 1, textAlign: 'center' }}>
                <Typography variant="h6" fontWeight={600}>
                  {vitals.pain_level}/10
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Pain
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>

        <Divider sx={{ my: 2 }} />
        
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Recent Labs
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
            <Typography variant="body2" color="text.secondary">Sodium</Typography>
            <Typography variant="body2" fontWeight={500} color="error">128 mEq/L ↓</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
            <Typography variant="body2" color="text.secondary">WBC</Typography>
            <Typography variant="body2" fontWeight={500}>8.2 K/uL</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
            <Typography variant="body2" color="text.secondary">Hemoglobin</Typography>
            <Typography variant="body2" fontWeight={500}>13.1 g/dL</Typography>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default PatientSummary;