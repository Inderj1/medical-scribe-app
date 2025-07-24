import React from 'react';
import { Box, Chip, LinearProgress, Typography } from '@mui/material';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import PersonIcon from '@mui/icons-material/Person';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';

interface SpeakerIndicatorProps {
  currentSpeaker: 'DOCTOR' | 'PATIENT' | null;
  confidence: number;
  isActive: boolean;
}

const SpeakerIndicator: React.FC<SpeakerIndicatorProps> = ({ 
  currentSpeaker, 
  confidence,
  isActive 
}) => {
  const getSpeakerIcon = () => {
    if (currentSpeaker === 'DOCTOR') {
      return <LocalHospitalIcon sx={{ fontSize: 16 }} />;
    } else if (currentSpeaker === 'PATIENT') {
      return <PersonIcon sx={{ fontSize: 16 }} />;
    }
    return <RecordVoiceOverIcon sx={{ fontSize: 16 }} />;
  };

  const getSpeakerColor = () => {
    if (!isActive) return 'default';
    if (currentSpeaker === 'DOCTOR') return 'primary';
    if (currentSpeaker === 'PATIENT') return 'secondary';
    return 'default';
  };

  const getSpeakerLabel = () => {
    if (!isActive) return 'Inactive';
    return currentSpeaker || 'Detecting...';
  };

  return (
    <Box 
      sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1.5,
        p: 1.5,
        borderRadius: 1,
        bgcolor: 'rgba(0, 0, 0, 0.02)',
        border: '1px solid',
        borderColor: 'divider'
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
            Speaker:
          </Typography>
          <Chip
            label={getSpeakerLabel()}
            color={getSpeakerColor()}
            size="small"
            icon={getSpeakerIcon()}
            sx={{
              height: 24,
              fontSize: '0.75rem',
              fontWeight: 600,
              '& .MuiChip-icon': {
                fontSize: 16
              }
            }}
          />
        </Box>
        
        {isActive && currentSpeaker && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Confidence:
            </Typography>
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <LinearProgress
                variant="determinate"
                value={confidence * 100}
                sx={{ 
                  flex: 1,
                  height: 4,
                  borderRadius: 2,
                  bgcolor: 'rgba(0, 0, 0, 0.08)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 2,
                    bgcolor: confidence > 0.8 ? 'success.main' : 
                            confidence > 0.6 ? 'warning.main' : 'error.main'
                  }
                }}
              />
              <Typography 
                variant="caption" 
                sx={{ 
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: confidence > 0.8 ? 'success.main' : 
                         confidence > 0.6 ? 'warning.main' : 'error.main',
                  minWidth: 35
                }}
              >
                {Math.round(confidence * 100)}%
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default SpeakerIndicator;