import React from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  CircularProgress
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PrintIcon from '@mui/icons-material/Print';
import AddIcon from '@mui/icons-material/Add';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { formatDistanceToNow } from 'date-fns';

interface ActionBarProps {
  onSaveDraft: () => void;
  onSignEncounter: () => void;
  isDraftSaved: boolean;
  lastSaveTime: Date;
}

const ActionBar: React.FC<ActionBarProps> = ({
  onSaveDraft,
  onSignEncounter,
  isDraftSaved,
  lastSaveTime
}) => {
  const [isSaving, setIsSaving] = React.useState(false);
  const [isSigningOff, setIsSigningOff] = React.useState(false);

  const handleSaveDraft = async () => {
    setIsSaving(true);
    await onSaveDraft();
    setTimeout(() => setIsSaving(false), 500);
  };

  const handleSignEncounter = async () => {
    const confirmed = window.confirm(
      'Are you ready to sign and close this encounter? All documentation will be finalized.'
    );
    
    if (confirmed) {
      setIsSigningOff(true);
      await onSignEncounter();
      setTimeout(() => {
        setIsSigningOff(false);
        alert('Encounter signed and submitted to EMR');
      }, 1000);
    }
  };

  const handlePrintSummary = () => {
    window.print();
  };

  const handleAddAddendum = () => {
    console.log('Opening addendum editor...');
  };

  const getTimeSinceLastSave = () => {
    return formatDistanceToNow(lastSaveTime, { addSuffix: true });
  };

  return (
    <Paper
      elevation={3}
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        bgcolor: 'white',
        borderTop: 1,
        borderColor: 'divider',
        px: 3,
        py: 1.5,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 1200,
        boxShadow: '0 -2px 4px rgba(0,0,0,0.05)'
      }}
    >
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSignEncounter}
          disabled={isSigningOff}
          startIcon={isSigningOff ? <CircularProgress size={16} /> : <CheckCircleIcon />}
          sx={{ textTransform: 'none' }}
        >
          {isSigningOff ? 'Signing...' : 'Sign & Close Encounter'}
        </Button>
        
        <Button
          variant="contained"
          color="secondary"
          onClick={handleSaveDraft}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
          sx={{ 
            textTransform: 'none',
            bgcolor: '#6c757d',
            '&:hover': {
              bgcolor: '#5a6268'
            }
          }}
        >
          {isSaving ? 'Saving...' : 'Save Draft'}
        </Button>
        
        <Button
          variant="outlined"
          onClick={handlePrintSummary}
          startIcon={<PrintIcon />}
          sx={{ 
            textTransform: 'none',
            borderColor: '#6c757d',
            color: '#6c757d',
            '&:hover': {
              borderColor: '#5a6268',
              bgcolor: 'rgba(108, 117, 125, 0.04)'
            }
          }}
        >
          Print Summary
        </Button>
        
        <Button
          variant="outlined"
          onClick={handleAddAddendum}
          startIcon={<AddIcon />}
          sx={{ 
            textTransform: 'none',
            borderColor: '#6c757d',
            color: '#6c757d',
            '&:hover': {
              borderColor: '#5a6268',
              bgcolor: 'rgba(108, 117, 125, 0.04)'
            }
          }}
        >
          Add Addendum
        </Button>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Last saved:
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {isDraftSaved ? getTimeSinceLastSave() : 'Not saved'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            Voice recording:
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <FiberManualRecordIcon 
              sx={{ 
                fontSize: 12, 
                color: '#28a745',
                animation: 'pulse 2s ease-in-out infinite'
              }} 
            />
            <Typography 
              variant="body2" 
              sx={{ 
                color: '#28a745', 
                fontWeight: 500
              }}
            >
              Active
            </Typography>
          </Box>
        </Box>
      </Box>

      <style>
        {`
          @keyframes pulse {
            0% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
            100% {
              opacity: 1;
            }
          }
        `}
      </style>
    </Paper>
  );
};

export default ActionBar;