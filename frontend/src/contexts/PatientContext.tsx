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

interface PatientContextType {
  selectedPatient: Patient | null;
  selectedEncounter: Encounter | null;
  recentVitals: any | null;
  setSelectedPatient: (patient: Patient | null) => void;
  setSelectedEncounter: (encounter: Encounter | null) => void;
  setRecentVitals: (vitals: any) => void;
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

  // Load cached patient data on mount
  useEffect(() => {
    const cachedPatient = localStorage.getItem('selectedPatient');
    const cachedEncounter = localStorage.getItem('selectedEncounter');
    const cachedVitals = localStorage.getItem('recentVitals');

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

  const clearPatientData = () => {
    setSelectedPatient(null);
    setSelectedEncounter(null);
    setRecentVitals(null);
    localStorage.removeItem('selectedPatient');
    localStorage.removeItem('selectedEncounter');
    localStorage.removeItem('recentVitals');
  };

  const value = {
    selectedPatient,
    selectedEncounter,
    recentVitals,
    setSelectedPatient,
    setSelectedEncounter,
    setRecentVitals,
    clearPatientData
  };

  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>;
};

export default PatientContext;