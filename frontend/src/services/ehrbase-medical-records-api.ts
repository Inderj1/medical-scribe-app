import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
// Use ngrok URL for EHRBASE medical records API
const LOCAL_EHRBASE_URL = 'https://859574eed9a9.ngrok.app/api';

interface Patient {
  ehr_id: string;
  patient: {
    name: string;
    date_of_birth: string;
    gender: string;
    external_ref: {
      id: string;
      namespace: string;
      type: string;
    };
  };
}

interface PatientRecord {
  record_id: string;
  patient_id: string;
  record_type: string;
  created_date: string;
  created_by: string;
  reason_for_visit: string;
  vitals: any;
  history_present_illness: any;
  past_medical_history: string[];
  past_surgical_history: string[];
  family_history: string[];
  social_history: any;
  review_of_systems: any;
  physical_examination: any;
  lab_results: any[];
  imaging_results: any[];
  assessment_and_plan: any;
}

class MedicalRecordsAPI {
  private axiosInstance: AxiosInstance;

  constructor() {
    // Direct connection to EHRBASE Medical Records API via ngrok
    this.axiosInstance = axios.create({
      baseURL: LOCAL_EHRBASE_URL,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
  }

  // Get all patients
  async getAllPatients(): Promise<Patient[]> {
    try {
      const response = await this.axiosInstance.get('/patients');
      return response.data.patients || [];
    } catch (error) {
      console.error('Failed to get patients from EHRBASE:', error);
      return [];
    }
  }

  // Get patient record by record ID
  async getPatientRecord(recordId: string): Promise<PatientRecord | null> {
    try {
      const response = await this.axiosInstance.get(`/records/${recordId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get patient record ${recordId}:`, error);
      return null;
    }
  }

  // Search patients with filters
  async searchPatients(filters?: {
    firstName?: string;
    lastName?: string;
    dateOfBirth?: string;
    mrn?: string;
  }): Promise<any[]> {
    try {
      console.log('Searching for patients in local EHRBASE API...');
      
      const allPatients = await this.getAllPatients();
      console.log(`Found ${allPatients.length} patients from local EHRBASE`);
      
      // Convert to our standard patient format
      const patients = allPatients.map(p => {
        const nameParts = p.patient.name.split(' ');
        const firstName = nameParts[0] || '';
        const lastName = nameParts.slice(1).join(' ') || '';
        
        return {
          ehr_id: p.ehr_id,
          mrn: p.patient.external_ref.id,
          first_name: firstName,
          last_name: lastName,
          date_of_birth: p.patient.date_of_birth,
          gender: p.patient.gender.toLowerCase(),
          phone: '',
          email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}@example.com`
        };
      });
      
      // Apply filters if provided
      if (filters) {
        return patients.filter(patient => {
          if (filters.firstName && !patient.first_name.toLowerCase().includes(filters.firstName.toLowerCase())) {
            return false;
          }
          if (filters.lastName && !patient.last_name.toLowerCase().includes(filters.lastName.toLowerCase())) {
            return false;
          }
          if (filters.mrn && !patient.mrn.toLowerCase().includes(filters.mrn.toLowerCase())) {
            return false;
          }
          if (filters.dateOfBirth && patient.date_of_birth !== filters.dateOfBirth) {
            return false;
          }
          return true;
        });
      }
      
      return patients;
    } catch (error) {
      console.error('Failed to search patients:', error);
      return [];
    }
  }
}

export const medicalRecordsAPI = new MedicalRecordsAPI();