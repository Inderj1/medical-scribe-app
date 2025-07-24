import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  CircularProgress,
  Fade,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  LinearProgress
} from '@mui/material';
import AssignmentIcon from '@mui/icons-material/Assignment';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import MedicationIcon from '@mui/icons-material/Medication';
import NoteAddIcon from '@mui/icons-material/NoteAdd';
import HistoryIcon from '@mui/icons-material/History';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

interface ActiveAgent {
  section: string;
  status: 'idle' | 'processing' | 'completed';
  confidence?: number;
}

interface AgentStatusProps {
  activeAgents: ActiveAgent[];
  currentSection?: string;
  isProcessing: boolean;
}

const sectionConfig = {
  chief_complaint: {
    label: 'Chief Complaint',
    icon: <AssignmentIcon />,
    color: '#1976d2'
  },
  history_present_illness: {
    label: 'Present Illness',
    icon: <LocalHospitalIcon />,
    color: '#7b1fa2'
  },
  medications: {
    label: 'Medications',
    icon: <MedicationIcon />,
    color: '#388e3c'
  },
  physical_exam: {
    label: 'Physical Exam',
    icon: <AssignmentIcon />,
    color: '#f57c00'
  },
  assessment_plan: {
    label: 'Assessment & Plan',
    icon: <NoteAddIcon />,
    color: '#c62828'
  },
  review_of_systems: {
    label: 'Review of Systems',
    icon: <HistoryIcon />,
    color: '#00796b'
  }
};

const AgentStatus: React.FC<AgentStatusProps> = ({ 
  activeAgents, 
  currentSection,
  isProcessing 
}) => {
  const getAgentStatus = (section: string) => {
    const agent = activeAgents.find(a => a.section === section);
    return agent || { section, status: 'idle' as const };
  };

  const getSectionIcon = (section: string) => {
    return sectionConfig[section as keyof typeof sectionConfig]?.icon || <SmartToyIcon />;
  };

  const getSectionLabel = (section: string) => {
    return sectionConfig[section as keyof typeof sectionConfig]?.label || section;
  };

  const getSectionColor = (section: string) => {
    return sectionConfig[section as keyof typeof sectionConfig]?.color || '#666';
  };

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        borderRadius: 2,
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        border: '1px solid',
        borderColor: 'divider'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <SmartToyIcon sx={{ color: 'primary.main' }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'primary.main' }}>
          AI Agent Status
        </Typography>
        {isProcessing && (
          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={16} thickness={4} />
            <Typography variant="caption" color="text.secondary">
              Processing...
            </Typography>
          </Box>
        )}
      </Box>

      <List sx={{ py: 0 }}>
        {Object.keys(sectionConfig).map((section, index) => {
          const agentStatus = getAgentStatus(section);
          const isActive = agentStatus.status === 'processing';
          const isCompleted = agentStatus.status === 'completed';
          const isCurrent = currentSection === section;

          return (
            <React.Fragment key={section}>
              {index > 0 && <Divider sx={{ my: 0.5 }} />}
              <ListItem
                sx={{
                  py: 0.5,
                  px: 1,
                  borderRadius: 1,
                  transition: 'all 0.2s ease',
                  bgcolor: isCurrent ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
                  '&:hover': {
                    bgcolor: 'rgba(0, 0, 0, 0.04)'
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <Box
                    sx={{
                      color: isActive ? getSectionColor(section) : 
                             isCompleted ? 'success.main' : 'text.disabled',
                      display: 'flex',
                      alignItems: 'center',
                      position: 'relative'
                    }}
                  >
                    {isCompleted ? (
                      <CheckCircleIcon sx={{ fontSize: 20 }} />
                    ) : (
                      getSectionIcon(section)
                    )}
                    {isActive && (
                      <CircularProgress
                        size={24}
                        thickness={2}
                        sx={{
                          position: 'absolute',
                          left: -2,
                          top: -2,
                          color: getSectionColor(section)
                        }}
                      />
                    )}
                  </Box>
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontWeight: isActive || isCurrent ? 600 : 400,
                        color: isActive || isCompleted ? 'text.primary' : 'text.secondary',
                        fontSize: '0.875rem'
                      }}
                    >
                      {getSectionLabel(section)}
                    </Typography>
                  }
                  secondary={
                    isActive && agentStatus.confidence !== undefined && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                        <LinearProgress
                          variant="determinate"
                          value={agentStatus.confidence * 100}
                          sx={{
                            flex: 1,
                            height: 3,
                            borderRadius: 1.5,
                            bgcolor: 'rgba(0, 0, 0, 0.08)'
                          }}
                        />
                        <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                          {Math.round(agentStatus.confidence * 100)}%
                        </Typography>
                      </Box>
                    )
                  }
                />
                
                {isActive && (
                  <Fade in={true}>
                    <Chip
                      label="Active"
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        bgcolor: getSectionColor(section),
                        color: 'white',
                        fontWeight: 600
                      }}
                    />
                  </Fade>
                )}
              </ListItem>
            </React.Fragment>
          );
        })}
      </List>

      {activeAgents.length === 0 && !isProcessing && (
        <Box sx={{ textAlign: 'center', py: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Agents ready. Start speaking to begin processing.
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default AgentStatus;