import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Typography,
  Box,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SettingsIcon from '@mui/icons-material/Settings';

export type NoteFormat = 'long' | 'short' | 'bullet';

interface NoteSettingsProps {
  open: boolean;
  onClose: () => void;
  noteFormat: NoteFormat;
  onFormatChange: (format: NoteFormat) => void;
}

const NoteSettings: React.FC<NoteSettingsProps> = ({
  open,
  onClose,
  noteFormat,
  onFormatChange
}) => {
  const [selectedFormat, setSelectedFormat] = useState<NoteFormat>(noteFormat);

  const handleSave = () => {
    onFormatChange(selectedFormat);
    onClose();
  };

  const formatDescriptions = {
    long: 'Detailed documentation with complete sentences and comprehensive information',
    short: 'Concise documentation with key points in brief sentences',
    bullet: 'Structured bullet points for quick reference and clarity'
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SettingsIcon />
          <Typography variant="h6">Note Format Settings</Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent>
        <FormControl component="fieldset" sx={{ width: '100%', mt: 2 }}>
          <FormLabel component="legend" sx={{ mb: 2 }}>
            Choose your preferred note format
          </FormLabel>
          <RadioGroup
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value as NoteFormat)}
          >
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ 
                p: 2, 
                border: 1, 
                borderColor: selectedFormat === 'long' ? 'primary.main' : 'divider',
                borderRadius: 1,
                bgcolor: selectedFormat === 'long' ? 'primary.50' : 'transparent'
              }}>
                <FormControlLabel
                  value="long"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="subtitle1" fontWeight="medium">
                        Long Format
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {formatDescriptions.long}
                      </Typography>
                    </Box>
                  }
                />
              </Box>

              <Box sx={{ 
                p: 2, 
                border: 1, 
                borderColor: selectedFormat === 'short' ? 'primary.main' : 'divider',
                borderRadius: 1,
                bgcolor: selectedFormat === 'short' ? 'primary.50' : 'transparent'
              }}>
                <FormControlLabel
                  value="short"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="subtitle1" fontWeight="medium">
                        Short Format
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {formatDescriptions.short}
                      </Typography>
                    </Box>
                  }
                />
              </Box>

              <Box sx={{ 
                p: 2, 
                border: 1, 
                borderColor: selectedFormat === 'bullet' ? 'primary.main' : 'divider',
                borderRadius: 1,
                bgcolor: selectedFormat === 'bullet' ? 'primary.50' : 'transparent'
              }}>
                <FormControlLabel
                  value="bullet"
                  control={<Radio />}
                  label={
                    <Box>
                      <Typography variant="subtitle1" fontWeight="medium">
                        Bullet Points
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {formatDescriptions.bullet}
                      </Typography>
                    </Box>
                  }
                />
              </Box>
            </Box>
          </RadioGroup>
        </FormControl>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default NoteSettings;