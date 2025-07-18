import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Alert,
  Chip,
  Divider
} from '@mui/material';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import WarningIcon from '@mui/icons-material/Warning';
import webSocketService from '../../services/websocket';

interface PhysicalExaminationProps {
  encounterId: string;
}

interface Finding {
  label: string;
  value: string;
  status: 'normal' | 'abnormal';
}

const FindingItem: React.FC<Finding> = ({ label, value, status }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        py: 0.75,
        px: 1,
        '&:hover': {
          bgcolor: '#f8f9fa'
        }
      }}
    >
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography 
        variant="caption" 
        sx={{ 
          fontWeight: 600,
          color: status === 'abnormal' ? '#dc3545' : 'text.primary'
        }}
      >
        {value}
      </Typography>
    </Box>
  );
};

const PhysicalExamination: React.FC<PhysicalExaminationProps> = ({ encounterId }) => {
  const [examFindings, setExamFindings] = useState({
    general: [
      { label: 'General Appearance', value: 'Alert and oriented', status: 'normal' as const },
      { label: 'Respiratory Effort', value: 'Normal', status: 'normal' as const },
      { label: 'Distress Level', value: 'No acute distress', status: 'normal' as const }
    ],
    pulmonary: [
      { label: 'Breath Sounds', value: 'Clear bilaterally', status: 'normal' as const },
      { label: 'Percussion', value: 'Resonant', status: 'normal' as const },
      { label: 'Chest Wall', value: 'No tenderness', status: 'normal' as const }
    ],
    cardiac: [
      { label: 'Heart Sounds', value: 'Regular, no murmurs', status: 'normal' as const },
      { label: 'Rhythm', value: 'Regular', status: 'normal' as const },
      { label: 'Extremities', value: 'No edema', status: 'normal' as const }
    ],
    imaging: {
      hasCritical: false,
      findings: ''
    }
  });

  useEffect(() => {
    // Listen for examination updates from voice transcription
    const handleExamUpdate = (data: any) => {
      if (data.type === 'exam:update' && data.section) {
        setExamFindings(prev => ({
          ...prev,
          [data.section]: data.findings
        }));
      }
    };

    webSocketService.on('exam:update', handleExamUpdate);

    return () => {
      webSocketService.off('exam:update', handleExamUpdate);
    };
  }, [encounterId]);

  return (
    <Paper
      elevation={2}
      sx={{
        bgcolor: 'white',
        borderRadius: 2,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        flex: 1
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
          alignItems: 'center',
          gap: 1
        }}
      >
        <LocalHospitalIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Physical Examination
        </Typography>
      </Box>

      <Box sx={{ p: 1.5, overflow: 'auto', flex: 1 }}>
        {/* General Examination */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 0.5 }}>
            GENERAL
          </Typography>
          <Box sx={{ bgcolor: '#f8f9fa', borderRadius: 1 }}>
            {examFindings.general.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </Box>
        </Box>

        {/* Pulmonary Examination */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 0.5 }}>
            PULMONARY
          </Typography>
          <Box sx={{ bgcolor: '#f8f9fa', borderRadius: 1 }}>
            {examFindings.pulmonary.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </Box>
        </Box>

        {/* Cardiac Examination */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 0.5 }}>
            CARDIAC
          </Typography>
          <Box sx={{ bgcolor: '#f8f9fa', borderRadius: 1 }}>
            {examFindings.cardiac.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </Box>
        </Box>

        {/* Imaging */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
              IMAGING
            </Typography>
            {examFindings.imaging.hasCritical && (
              <Chip
                icon={<WarningIcon />}
                label="Critical"
                size="small"
                color="error"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
          </Box>
          
          {examFindings.imaging.hasCritical ? (
            <Alert 
              severity="error" 
              sx={{ 
                py: 0.5,
                px: 1,
                '& .MuiAlert-message': { py: 0 },
                '& .MuiAlert-icon': { py: 0.5 }
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                CXR: Suspicious lesion noted in right upper lobe with associated pleural effusion
              </Typography>
            </Alert>
          ) : (
            <Box sx={{ bgcolor: '#f8f9fa', borderRadius: 1, p: 1 }}>
              <Typography variant="caption" color="text.secondary">
                No imaging findings available
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

export default PhysicalExamination;