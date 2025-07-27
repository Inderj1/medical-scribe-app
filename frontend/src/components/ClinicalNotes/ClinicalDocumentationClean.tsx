import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Divider,
  Alert,
  LinearProgress,
  Fade,
  Collapse,
  IconButton,
  Tooltip,
  Tabs,
  Tab
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import AddIcon from '@mui/icons-material/Add';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SettingsIcon from '@mui/icons-material/Settings';
import AssignmentIcon from '@mui/icons-material/Assignment';
import SummarizeIcon from '@mui/icons-material/Summarize';
import NoteSettings, { NoteFormat } from './NoteSettings';
import AfterVisitSummaryTab from './AfterVisitSummaryTab';

interface ClinicalDocumentationCleanProps {
  encounterId: string;
  patientId: string;
  onAddToSection?: (section: string, content: string, transcriptionId?: string) => void;
  prefilledSections?: any;
}

interface Symptom {
  id: string;
  text: string;
  severity?: 'high' | 'medium' | 'low';
  duration?: string;
}

interface Diagnosis {
  id: string;
  primary: string;
  code: string;
  isPrimary: boolean;
}

interface PlanItem {
  id: string;
  text: string;
  completed: boolean;
  category: 'action' | 'medication' | 'followup' | 'education';
}

const ClinicalDocumentationClean: React.FC<ClinicalDocumentationCleanProps> = ({ 
  encounterId, 
  patientId,
  onAddToSection,
  prefilledSections 
}) => {
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [transcriptionConfidence, setTranscriptionConfidence] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [noteFormat, setNoteFormat] = useState<NoteFormat>(
    (localStorage.getItem('noteFormat') as NoteFormat) || 'long'
  );
  const [currentTab, setCurrentTab] = useState(0);
  
  // Initialize with empty data or data from EHR
  const [presentIllness, setPresentIllness] = useState<Symptom[]>([]);
  const [riskFactors, setRiskFactors] = useState<Symptom[]>([]);
  const [previousInterventions, setPreviousInterventions] = useState('');
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [planItems, setPlanItems] = useState<PlanItem[]>([]);
  
  // Clinical sections state
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [medications, setMedications] = useState('');
  const [allergies, setAllergies] = useState('');
  const [pastMedicalHistory, setPastMedicalHistory] = useState('');
  const [socialHistory, setSocialHistory] = useState('');
  const [familyHistory, setFamilyHistory] = useState('');
  const [vitalSigns, setVitalSigns] = useState('');
  const [physicalExam, setPhysicalExam] = useState('');
  
  // Collapsed sections state
  const [collapsedSections, setCollapsedSections] = useState<{[key: string]: boolean}>({
    presentIllness: false,
    assessment: false,
    riskFactors: false,
    previousInterventions: false,
    otherSections: false
  });

  // Initialize from prefilled sections if available
  useEffect(() => {
    if (prefilledSections) {
      if (prefilledSections.chief_complaint) {
        setChiefComplaint(prefilledSections.chief_complaint);
      }
      if (prefilledSections.medications) {
        setMedications(prefilledSections.medications);
      }
      if (prefilledSections.allergies) {
        setAllergies(prefilledSections.allergies);
      }
      if (prefilledSections.past_medical_history) {
        setPastMedicalHistory(prefilledSections.past_medical_history);
      }
      if (prefilledSections.social_history) {
        setSocialHistory(prefilledSections.social_history);
      }
      if (prefilledSections.family_history) {
        setFamilyHistory(prefilledSections.family_history);
      }
      if (prefilledSections.vital_signs) {
        setVitalSigns(prefilledSections.vital_signs);
      }
      if (prefilledSections.physical_exam) {
        setPhysicalExam(prefilledSections.physical_exam);
      }
      
      // Parse symptoms from present illness if available
      if (prefilledSections.present_illness) {
        const symptoms = parseSymptoms(prefilledSections.present_illness);
        setPresentIllness(symptoms);
      }
      
      // Parse diagnoses from assessment if available
      if (prefilledSections.assessment) {
        const parsedDiagnoses = parseDiagnoses(prefilledSections.assessment);
        setDiagnoses(parsedDiagnoses);
      }
      
      // Parse plan items if available
      if (prefilledSections.plan) {
        const parsedPlanItems = parsePlanItems(prefilledSections.plan);
        setPlanItems(parsedPlanItems);
      }
    }
  }, [prefilledSections]);

  // Helper functions to parse data
  const parseSymptoms = (text: string): Symptom[] => {
    // Simple parser - in production, this would be more sophisticated
    const lines = text.split('\n').filter(line => line.trim());
    return lines.map((line, index) => ({
      id: `symptom-${index}`,
      text: line.trim(),
      severity: 'medium' as const
    }));
  };

  const parseDiagnoses = (text: string): Diagnosis[] => {
    const lines = text.split('\n').filter(line => line.trim());
    return lines.map((line, index) => ({
      id: `diagnosis-${index}`,
      primary: line.trim(),
      code: '',
      isPrimary: index === 0
    }));
  };

  const parsePlanItems = (text: string): PlanItem[] => {
    const lines = text.split('\n').filter(line => line.trim());
    return lines.map((line, index) => ({
      id: `plan-${index}`,
      text: line.trim(),
      completed: false,
      category: 'action' as const
    }));
  };

  const toggleSection = (section: string) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleNoteFormatChange = (format: NoteFormat) => {
    setNoteFormat(format);
    localStorage.setItem('noteFormat', format);
  };

  const handleAddSymptom = () => {
    const newSymptom: Symptom = {
      id: `symptom-${Date.now()}`,
      text: '',
      severity: 'medium'
    };
    setPresentIllness([...presentIllness, newSymptom]);
  };

  const handleAddDiagnosis = () => {
    const newDiagnosis: Diagnosis = {
      id: `diagnosis-${Date.now()}`,
      primary: '',
      code: '',
      isPrimary: diagnoses.length === 0
    };
    setDiagnoses([...diagnoses, newDiagnosis]);
  };

  const handleAddPlanItem = () => {
    const newPlanItem: PlanItem = {
      id: `plan-${Date.now()}`,
      text: '',
      completed: false,
      category: 'action'
    };
    setPlanItems([...planItems, newPlanItem]);
  };

  // Handle incoming transcription content
  const handleIncomingContent = (content: string, section?: string) => {
    if (section) {
      switch (section) {
        case 'chief_complaint':
          setChiefComplaint(prev => prev + (prev ? '\n' : '') + content);
          break;
        case 'present_illness':
          const newSymptom: Symptom = {
            id: `symptom-${Date.now()}`,
            text: content,
            severity: 'medium'
          };
          setPresentIllness(prev => [...prev, newSymptom]);
          break;
        case 'medications':
          setMedications(prev => prev + (prev ? '\n' : '') + content);
          break;
        case 'assessment':
          const newDiagnosis: Diagnosis = {
            id: `diagnosis-${Date.now()}`,
            primary: content,
            code: '',
            isPrimary: diagnoses.length === 0
          };
          setDiagnoses(prev => [...prev, newDiagnosis]);
          break;
        case 'plan':
          const newPlan: PlanItem = {
            id: `plan-${Date.now()}`,
            text: content,
            completed: false,
            category: 'action'
          };
          setPlanItems(prev => [...prev, newPlan]);
          break;
      }
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Tabs value={currentTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Clinical Documentation" icon={<AssignmentIcon />} iconPosition="start" />
        <Tab label="After Visit Summary" icon={<SummarizeIcon />} iconPosition="start" />
      </Tabs>

      {currentTab === 0 ? (
        <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h5" fontWeight={600}>
              Clinical Documentation
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip 
                label={noteFormat.charAt(0).toUpperCase() + noteFormat.slice(1)} 
                size="small" 
                color="primary"
              />
              <IconButton onClick={() => setSettingsOpen(true)} size="small">
                <SettingsIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Chief Complaint */}
          <Paper elevation={1} sx={{ mb: 2, p: 2 }}>
            <Typography variant="h6" gutterBottom>Chief Complaint</Typography>
            <Typography variant="body2" color="text.secondary">
              {chiefComplaint || 'No chief complaint documented'}
            </Typography>
          </Paper>

          {/* History of Present Illness */}
          <Paper elevation={1} sx={{ mb: 2 }}>
            <Box sx={{ p: 2, cursor: 'pointer' }} onClick={() => toggleSection('presentIllness')}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">History of Present Illness</Typography>
                <IconButton size="small">
                  {collapsedSections.presentIllness ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                </IconButton>
              </Box>
            </Box>
            <Collapse in={!collapsedSections.presentIllness}>
              <Divider />
              <Box sx={{ p: 2 }}>
                {presentIllness.length > 0 ? (
                  presentIllness.map((symptom) => (
                    <Box key={symptom.id} sx={{ mb: 1 }}>
                      <Typography variant="body2">{symptom.text}</Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No symptoms documented
                  </Typography>
                )}
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={handleAddSymptom}
                  sx={{ mt: 1 }}
                >
                  Add Symptom
                </Button>
              </Box>
            </Collapse>
          </Paper>

          {/* Assessment & Plan */}
          <Paper elevation={1} sx={{ mb: 2 }}>
            <Box sx={{ p: 2, cursor: 'pointer' }} onClick={() => toggleSection('assessment')}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Assessment & Plan</Typography>
                <IconButton size="small">
                  {collapsedSections.assessment ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                </IconButton>
              </Box>
            </Box>
            <Collapse in={!collapsedSections.assessment}>
              <Divider />
              <Box sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Diagnoses</Typography>
                {diagnoses.length > 0 ? (
                  diagnoses.map((diagnosis) => (
                    <Box key={diagnosis.id} sx={{ mb: 1 }}>
                      <Typography variant="body2">
                        {diagnosis.isPrimary && <Chip label="Primary" size="small" sx={{ mr: 1 }} />}
                        {diagnosis.primary}
                      </Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No diagnoses documented
                  </Typography>
                )}
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={handleAddDiagnosis}
                  sx={{ mt: 1, mb: 2 }}
                >
                  Add Diagnosis
                </Button>

                <Typography variant="subtitle2" gutterBottom>Plan</Typography>
                {planItems.length > 0 ? (
                  planItems.map((item) => (
                    <Box key={item.id} sx={{ mb: 1 }}>
                      <Typography variant="body2">{item.text}</Typography>
                    </Box>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No plan items documented
                  </Typography>
                )}
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={handleAddPlanItem}
                  sx={{ mt: 1 }}
                >
                  Add Plan Item
                </Button>
              </Box>
            </Collapse>
          </Paper>

          {/* Other Clinical Sections */}
          <Paper elevation={1} sx={{ mb: 2 }}>
            <Box sx={{ p: 2, cursor: 'pointer' }} onClick={() => toggleSection('otherSections')}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Other Clinical Sections</Typography>
                <IconButton size="small">
                  {collapsedSections.otherSections ? <ExpandMoreIcon /> : <ExpandLessIcon />}
                </IconButton>
              </Box>
            </Box>
            <Collapse in={!collapsedSections.otherSections}>
              <Divider />
              <Box sx={{ p: 2 }}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Medications</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {medications || 'No medications documented'}
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Allergies</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {allergies || 'No known allergies'}
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Past Medical History</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {pastMedicalHistory || 'No past medical history documented'}
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Social History</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {socialHistory || 'No social history documented'}
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Family History</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {familyHistory || 'No family history documented'}
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Vital Signs</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {vitalSigns || 'No vital signs documented'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" gutterBottom>Physical Exam</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {physicalExam || 'No physical exam documented'}
                  </Typography>
                </Box>
              </Box>
            </Collapse>
          </Paper>
        </Box>
      ) : (
        <AfterVisitSummaryTab 
          encounterId={encounterId}
          patientId={patientId}
          clinicalData={{
            chiefComplaint,
            presentIllness: presentIllness.map(s => s.text).join('\n'),
            medications,
            diagnoses: diagnoses.map(d => d.primary),
            planItems: planItems.map(p => p.text)
          }}
        />
      )}

      <NoteSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        currentFormat={noteFormat}
        onFormatChange={handleNoteFormatChange}
      />
    </Box>
  );
};

export default ClinicalDocumentationClean;