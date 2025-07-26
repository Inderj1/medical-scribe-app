import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Divider,
  Alert,
  Checkbox,
  FormControlLabel,
  TextField,
  CircularProgress,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import PrintIcon from '@mui/icons-material/Print';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AssignmentIcon from '@mui/icons-material/Assignment';
import PersonIcon from '@mui/icons-material/Person';
import EventIcon from '@mui/icons-material/Event';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import ListAltIcon from '@mui/icons-material/ListAlt';
import { usePatient } from '../../contexts/PatientContext';

interface TodoItem {
  id: string;
  text: string;
  completed: boolean;
  category: 'medication' | 'followup' | 'lifestyle' | 'monitoring';
  priority: 'high' | 'medium' | 'low';
}

interface VisitSummary {
  id: string;
  visitDate: string;
  provider: string;
  reasonForVisit: string;
  keyFindings: string[];
  todoItems: TodoItem[];
  followUpInstructions: string;
  nextAppointment?: string;
  oneLinerSummary: string;
  patientFriendlyDiagnosis: string[];
  emergencyInstructions: string[];
}

interface AfterVisitSummaryTabProps {
  encounterId: string;
  patientId: string;
  clinicalData: any;
}

const AfterVisitSummaryTab: React.FC<AfterVisitSummaryTabProps> = ({
  encounterId,
  patientId,
  clinicalData
}) => {
  const { selectedPatient, selectedEncounter } = usePatient();
  const [summary, setSummary] = useState<VisitSummary | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState<VisitSummary | null>(null);

  // Auto-generate summary when component mounts if clinical data is available
  useEffect(() => {
    if (clinicalData && !summary) {
      generateSummary();
    }
  }, [clinicalData]);

  const generateSummary = async () => {
    setIsGenerating(true);
    
    try {
      // Simulate AI-powered summary generation
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const generatedSummary: VisitSummary = {
        id: `summary-${encounterId}`,
        visitDate: selectedEncounter?.encounter_date || new Date().toISOString(),
        provider: selectedEncounter?.provider_name || 'Dr. Smith',
        reasonForVisit: translateToLayman(clinicalData?.chief_complaint || 'General consultation'),
        keyFindings: extractKeyFindings(clinicalData),
        todoItems: generateTodoItems(clinicalData),
        followUpInstructions: generateFollowUpInstructions(clinicalData),
        nextAppointment: generateNextAppointment(clinicalData),
        oneLinerSummary: generateOneLinerSummary(clinicalData),
        patientFriendlyDiagnosis: translateDiagnoses(clinicalData?.diagnoses || []),
        emergencyInstructions: generateEmergencyInstructions(clinicalData)
      };
      
      setSummary(generatedSummary);
      setEditedSummary(generatedSummary);
    } catch (error) {
      console.error('Error generating summary:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const translateToLayman = (medicalText: string): string => {
    // Simple translation logic - in production, this would use AI
    const translations: { [key: string]: string } = {
      'dyspnea': 'difficulty breathing',
      'hemoptysis': 'coughing up blood',
      'thoracentesis': 'fluid removal from lung area',
      'bronchogenic carcinoma': 'lung cancer',
      'pleural effusion': 'fluid around the lungs'
    };
    
    let translated = medicalText;
    Object.entries(translations).forEach(([medical, layman]) => {
      translated = translated.replace(new RegExp(medical, 'gi'), layman);
    });
    
    return translated;
  };

  const extractKeyFindings = (data: any): string[] => {
    const findings = [];
    
    if (data?.presentIllness?.length > 0) {
      findings.push(`You came in because of ${translateToLayman(data.presentIllness[0]?.text || 'health concerns')}`);
    }
    
    if (data?.vitals) {
      findings.push(`Your vital signs were checked and ${data.vitals.blood_pressure ? 'blood pressure was ' + data.vitals.blood_pressure : 'were normal'}`);
    }
    
    findings.push('We discussed your symptoms and medical history');
    findings.push('Tests and examinations were performed to understand your condition better');
    
    return findings;
  };

  const generateTodoItems = (data: any): TodoItem[] => {
    const todos: TodoItem[] = [];
    
    // Extract from plan items
    if (data?.planItems) {
      data.planItems.forEach((item: any, index: number) => {
        if (item.category === 'medication') {
          todos.push({
            id: `todo-${index}`,
            text: translateToLayman(item.text),
            completed: false,
            category: 'medication',
            priority: 'high'
          });
        } else if (item.category === 'followup') {
          todos.push({
            id: `todo-${index}`,
            text: 'Schedule follow-up appointment as discussed',
            completed: false,
            category: 'followup',
            priority: 'high'
          });
        } else if (item.category === 'education') {
          todos.push({
            id: `todo-${index}`,
            text: translateToLayman(item.text),
            completed: false,
            category: 'lifestyle',
            priority: 'medium'
          });
        }
      });
    }
    
    // Add default todos
    todos.push(
      {
        id: 'default-1',
        text: 'Take all medications as prescribed',
        completed: false,
        category: 'medication',
        priority: 'high'
      },
      {
        id: 'default-2',
        text: 'Follow up with your doctor as scheduled',
        completed: false,
        category: 'followup',
        priority: 'high'
      },
      {
        id: 'default-3',
        text: 'Contact us if your symptoms get worse',
        completed: false,
        category: 'monitoring',
        priority: 'high'
      }
    );
    
    return todos;
  };

  const generateFollowUpInstructions = (data: any): string => {
    return `Please schedule a follow-up appointment in 1-2 weeks to review your progress and any test results. If you experience worsening symptoms or new concerns before then, please contact our office immediately.`;
  };

  const generateNextAppointment = (data: any): string => {
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 14);
    return futureDate.toLocaleDateString();
  };

  const generateOneLinerSummary = (data: any): string => {
    const reason = data?.chief_complaint || 'health concerns';
    const date = new Date().toLocaleDateString();
    return `${date}: Visit for ${translateToLayman(reason)} - tests ordered, treatment plan discussed`;
  };

  const translateDiagnoses = (diagnoses: any[]): string[] => {
    return diagnoses.map(diagnosis => translateToLayman(diagnosis.primary || diagnosis));
  };

  const generateEmergencyInstructions = (data: any): string[] => {
    return [
      'Call 911 or go to the emergency room if you have severe difficulty breathing',
      'Contact our office immediately if you cough up blood',
      'Seek immediate care if you have severe chest pain',
      'Call us if you develop fever over 101°F (38.3°C)'
    ];
  };

  const handleSave = () => {
    setSummary(editedSummary);
    setIsEditing(false);
    // TODO: Save to backend
  };

  const handlePrint = () => {
    window.print();
  };

  const handleTodoToggle = (todoId: string) => {
    if (!editedSummary) return;
    
    setEditedSummary({
      ...editedSummary,
      todoItems: editedSummary.todoItems.map(item =>
        item.id === todoId ? { ...item, completed: !item.completed } : item
      )
    });
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#d32f2f';
      case 'medium': return '#ed6c02';
      case 'low': return '#2e7d32';
      default: return '#1976d2';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'medication': return <LocalHospitalIcon />;
      case 'followup': return <EventIcon />;
      case 'lifestyle': return <PersonIcon />;
      case 'monitoring': return <AssignmentIcon />;
      default: return <ListAltIcon />;
    }
  };

  if (isGenerating) {
    return (
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '400px',
        gap: 2
      }}>
        <CircularProgress size={60} />
        <Typography variant="h6" color="primary">
          Generating After-Visit Summary...
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Creating patient-friendly summary from clinical notes
        </Typography>
      </Box>
    );
  }

  if (!summary) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          After-Visit Summary
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Generate a patient-friendly summary of this visit
        </Typography>
        <Button
          variant="contained"
          onClick={generateSummary}
          startIcon={<AssignmentIcon />}
          size="large"
        >
          Generate Summary
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', overflow: 'auto' }}>
      {/* Header with Actions */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        p: 2, 
        borderBottom: 1, 
        borderColor: 'divider',
        bgcolor: '#f8f9fa'
      }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          After-Visit Summary
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Print Summary">
            <IconButton onClick={handlePrint} color="primary">
              <PrintIcon />
            </IconButton>
          </Tooltip>
          {isEditing ? (
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              size="small"
            >
              Save
            </Button>
          ) : (
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setIsEditing(true)}
              size="small"
            >
              Edit
            </Button>
          )}
        </Box>
      </Box>

      <Box sx={{ p: 3 }}>
        {/* Visit Information */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Your Visit Information
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Date of Visit
                </Typography>
                <Typography variant="body1">
                  {new Date(summary.visitDate).toLocaleDateString()}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Your Doctor
                </Typography>
                <Typography variant="body1">
                  {summary.provider}
                </Typography>
              </Box>
              <Box sx={{ gridColumn: '1 / -1' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Reason for Visit
                </Typography>
                <Typography variant="body1">
                  {summary.reasonForVisit}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* What We Found */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              What We Found
            </Typography>
            {summary.patientFriendlyDiagnosis.length > 0 && (
              <Box sx={{ mb: 2 }}>
                {summary.patientFriendlyDiagnosis.map((diagnosis, index) => (
                  <Chip
                    key={index}
                    label={diagnosis}
                    color="info"
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>
            )}
            <List dense>
              {summary.keyFindings.map((finding, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <CheckCircleIcon color="success" />
                  </ListItemIcon>
                  <ListItemText primary={finding} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>

        {/* Your To-Do List */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Your To-Do List
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Please complete these important tasks for your health:
            </Typography>
            
            {editedSummary?.todoItems.map((todo) => (
              <Box key={todo.id} sx={{ mb: 1 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={todo.completed}
                      onChange={() => handleTodoToggle(todo.id)}
                      disabled={!isEditing}
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getCategoryIcon(todo.category)}
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {todo.text}
                      </Typography>
                      <Chip
                        size="small"
                        label={todo.priority}
                        sx={{ 
                          bgcolor: getPriorityColor(todo.priority),
                          color: 'white',
                          fontSize: '0.7rem'
                        }}
                      />
                    </Box>
                  }
                  sx={{ 
                    width: '100%',
                    m: 0,
                    textDecoration: todo.completed ? 'line-through' : 'none'
                  }}
                />
              </Box>
            ))}
          </CardContent>
        </Card>

        {/* Follow-up Instructions */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Follow-up Instructions
            </Typography>
            {isEditing ? (
              <TextField
                multiline
                rows={3}
                fullWidth
                value={editedSummary?.followUpInstructions || ''}
                onChange={(e) => setEditedSummary(prev => prev ? 
                  { ...prev, followUpInstructions: e.target.value } : null
                )}
              />
            ) : (
              <Typography variant="body1">
                {summary.followUpInstructions}
              </Typography>
            )}
            
            {summary.nextAppointment && (
              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="subtitle2">
                  Next Appointment: {summary.nextAppointment}
                </Typography>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Emergency Instructions */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom color="error">
              When to Seek Emergency Care
            </Typography>
            <List dense>
              {summary.emergencyInstructions.map((instruction, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <LocalHospitalIcon color="error" />
                  </ListItemIcon>
                  <ListItemText primary={instruction} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>

        {/* One-liner for Records */}
        <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Visit Summary for Records:
          </Typography>
          <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
            {summary.oneLinerSummary}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default AfterVisitSummaryTab;