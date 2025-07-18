import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Alert,
  Chip
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

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
};

const FindingItem: React.FC<Finding> = ({ label, value, status }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        py: 1.5,
        borderBottom: 1,
        borderColor: '#f8f9fa',
        '&:last-child': {
          borderBottom: 0
        }
      }}
    >
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography 
        variant="body2" 
        sx={{ 
          fontWeight: 500,
          color: status === 'abnormal' ? '#dc3545' : '#28a745'
        }}
      >
        {value}
      </Typography>
    </Box>
  );
};

const PhysicalExamination: React.FC<PhysicalExaminationProps> = ({ encounterId }) => {
  const [selectedTab, setSelectedTab] = useState(0);
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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const tabs = [
    { label: 'General', key: 'general' },
    { label: 'Pulmonary', key: 'pulmonary' },
    { label: 'Cardiac', key: 'cardiac' },
    { label: 'Imaging', key: 'imaging' }
  ];

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

      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', flex: 1 }}>
        <Tabs
          value={selectedTab}
          onChange={handleTabChange}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              minWidth: 'auto',
              px: 2,
              py: 1,
              fontSize: '0.875rem',
              textTransform: 'none',
              color: 'text.secondary',
              '&.Mui-selected': {
                color: 'primary.main',
                fontWeight: 500
              }
            },
            '& .MuiTabs-indicator': {
              height: 2
            }
          }}
        >
          {tabs.map((tab) => (
            <Tab key={tab.key} label={tab.label} />
          ))}
        </Tabs>

        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <TabPanel value={selectedTab} index={0}>
            {examFindings.general.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </TabPanel>

          <TabPanel value={selectedTab} index={1}>
            {examFindings.pulmonary.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </TabPanel>

          <TabPanel value={selectedTab} index={2}>
            {examFindings.cardiac.map((finding) => (
              <FindingItem key={finding.label} {...finding} />
            ))}
          </TabPanel>

          <TabPanel value={selectedTab} index={3}>
            <Box>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2
              }}>
                <Typography 
                  variant="subtitle2" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.secondary'
                  }}
                >
                  Imaging Findings
                </Typography>
                {examFindings.imaging.hasCritical && (
                  <Chip
                    icon={<WarningIcon />}
                    label="Critical"
                    size="small"
                    color="error"
                  />
                )}
              </Box>
              
              {examFindings.imaging.hasCritical ? (
                <Alert 
                  severity="error" 
                  sx={{ 
                    bgcolor: '#f8d7da',
                    color: '#721c24',
                    '& .MuiAlert-icon': {
                      color: '#721c24'
                    }
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    CXR: Suspicious lesion noted in right upper lobe with associated pleural effusion
                  </Typography>
                </Alert>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No imaging findings available
                </Typography>
              )}
            </Box>
          </TabPanel>
        </Box>
      </Box>
    </Paper>
  );
};

export default PhysicalExamination;