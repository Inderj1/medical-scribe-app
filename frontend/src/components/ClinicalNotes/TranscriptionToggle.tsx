import React from 'react';
import { Box, Switch, FormControlLabel, Tooltip, Chip } from '@mui/material';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';

interface TranscriptionToggleProps {
  useEnhanced: boolean;
  onChange: (useEnhanced: boolean) => void;
}

const TranscriptionToggle: React.FC<TranscriptionToggleProps> = ({ useEnhanced, onChange }) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Tooltip title={
        useEnhanced 
          ? "Using AI-powered agentic transcription with advanced analysis" 
          : "Using standard transcription"
      }>
        <FormControlLabel
          control={
            <Switch
              checked={useEnhanced}
              onChange={(e) => onChange(e.target.checked)}
              size="small"
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {useEnhanced && <RocketLaunchIcon fontSize="small" color="primary" />}
              <span>Enhanced AI</span>
              {useEnhanced && (
                <Chip 
                  label="BETA" 
                  size="small" 
                  color="primary" 
                  sx={{ height: 16, fontSize: '0.65rem' }}
                />
              )}
            </Box>
          }
        />
      </Tooltip>
    </Box>
  );
};

export default TranscriptionToggle;