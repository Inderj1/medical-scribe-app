import React from 'react';
import { Box, Typography } from '@mui/material';

const ClinicalNotesPageDebug: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4">Clinical Notes Page - Debug Version</Typography>
      <Typography variant="body1">If you can see this, the React app is working.</Typography>
    </Box>
  );
};

export default ClinicalNotesPageDebug;