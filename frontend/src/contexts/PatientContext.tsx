import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface Patient {
  ehr_id: string;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string;
  email?: string;
  age?: number;
  allergies?: string;
  smoking_history?: string;
  // Additional clinical context from recent encounters
  recent_diagnosis?: string[];
  recent_chief_complaint?: string;
  recent_clinical_notes?: string;
}

interface Encounter {
  id: string;
  patient_id: string;
  encounter_date: string;
  chief_complaint: string;
  provider_name: string;
  encounter_type: string;
  status: string;
  vitals?: any;
  diagnosis?: string[];
  notes?: string;
}

interface TodoItem {
  id: string;
  text: string;
  completed: boolean;
  category: 'medication' | 'followup' | 'lifestyle' | 'monitoring';
  priority: 'high' | 'medium' | 'low';
}

interface VisitSummary {
  id: string;
  visit_date: string;
  provider: string;
  reason_for_visit: string;
  key_findings: string[];
  todo_items: TodoItem[];
  follow_up_instructions: string;
  next_appointment?: string;
  one_liner_summary: string;
  patient_friendly_diagnosis: string[];
  emergency_instructions: string[];
}

interface PatientContextType {
  selectedPatient: Patient | null;
  selectedEncounter: Encounter | null;
  recentVitals: any | null;
  visitSummary: VisitSummary | null;
  previousVisitSummaries: VisitSummary[];
  setSelectedPatient: (patient: Patient | null) => void;
  setSelectedEncounter: (encounter: Encounter | null) => void;
  setRecentVitals: (vitals: any) => void;
  setVisitSummary: (summary: VisitSummary | null) => void;
  setPreviousVisitSummaries: (summaries: VisitSummary[]) => void;
  clearPatientData: () => void;
}

const PatientContext = createContext<PatientContextType | undefined>(undefined);

export const usePatient = () => {
  const context = useContext(PatientContext);
  if (context === undefined) {
    throw new Error('usePatient must be used within a PatientProvider');
  }
  return context;
};

interface PatientProviderProps {
  children: ReactNode;
}

export const PatientProvider: React.FC<PatientProviderProps> = ({ children }) => {
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [selectedEncounter, setSelectedEncounter] = useState<Encounter | null>(null);
  const [recentVitals, setRecentVitals] = useState<any | null>(null);
  const [visitSummary, setVisitSummary] = useState<VisitSummary | null>(null);
  const [previousVisitSummaries, setPreviousVisitSummaries] = useState<VisitSummary[]>([]);

  // Load cached patient data on mount
  useEffect(() => {
    const cachedPatient = localStorage.getItem('selectedPatient');
    const cachedEncounter = localStorage.getItem('selectedEncounter');
    const cachedVitals = localStorage.getItem('recentVitals');
    const cachedSummary = localStorage.getItem('visitSummary');
    const cachedPreviousSummaries = localStorage.getItem('previousVisitSummaries');

    if (cachedPatient) {
      try {
        setSelectedPatient(JSON.parse(cachedPatient));
      } catch (e) {
        console.error('Error loading cached patient:', e);
      }
    }

    if (cachedEncounter) {
      try {
        setSelectedEncounter(JSON.parse(cachedEncounter));
      } catch (e) {
        console.error('Error loading cached encounter:', e);
      }
    }

    if (cachedVitals) {
      try {
        setRecentVitals(JSON.parse(cachedVitals));
      } catch (e) {
        console.error('Error loading cached vitals:', e);
      }
    }

    if (cachedSummary) {
      try {
        setVisitSummary(JSON.parse(cachedSummary));
      } catch (e) {
        console.error('Error loading cached summary:', e);
      }
    }

    if (cachedPreviousSummaries) {
      try {
        setPreviousVisitSummaries(JSON.parse(cachedPreviousSummaries));
      } catch (e) {
        console.error('Error loading cached previous summaries:', e);
      }
    }
  }, []);

  // Cache patient data when it changes
  useEffect(() => {
    if (selectedPatient) {
      localStorage.setItem('selectedPatient', JSON.stringify(selectedPatient));
    } else {
      localStorage.removeItem('selectedPatient');
    }
  }, [selectedPatient]);

  useEffect(() => {
    if (selectedEncounter) {
      localStorage.setItem('selectedEncounter', JSON.stringify(selectedEncounter));
    } else {
      localStorage.removeItem('selectedEncounter');
    }
  }, [selectedEncounter]);

  useEffect(() => {
    if (recentVitals) {
      localStorage.setItem('recentVitals', JSON.stringify(recentVitals));
    } else {
      localStorage.removeItem('recentVitals');
    }
  }, [recentVitals]);

  useEffect(() => {
    if (visitSummary) {
      localStorage.setItem('visitSummary', JSON.stringify(visitSummary));
    } else {
      localStorage.removeItem('visitSummary');
    }
  }, [visitSummary]);

  useEffect(() => {
    if (previousVisitSummaries.length > 0) {
      localStorage.setItem('previousVisitSummaries', JSON.stringify(previousVisitSummaries));
    } else {
      localStorage.removeItem('previousVisitSummaries');
    }
  }, [previousVisitSummaries]);

  const clearPatientData = () => {
    setSelectedPatient(null);
    setSelectedEncounter(null);
    setRecentVitals(null);
    setVisitSummary(null);
    setPreviousVisitSummaries([]);
    localStorage.removeItem('selectedPatient');
    localStorage.removeItem('selectedEncounter');
    localStorage.removeItem('recentVitals');
    localStorage.removeItem('visitSummary');
    localStorage.removeItem('previousVisitSummaries');
  };

  const value = {
    selectedPatient,
    selectedEncounter,
    recentVitals,
    visitSummary,
    previousVisitSummaries,
    setSelectedPatient,
    setSelectedEncounter,
    setRecentVitals,
    setVisitSummary,
    setPreviousVisitSummaries,
    clearPatientData
  };

  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>;
};

export default PatientContext;