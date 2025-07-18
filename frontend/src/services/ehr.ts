import axios from 'axios';
import { fhirService } from './fhir';
import { ehrbaseService } from './ehrbase';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface EHRConnection {
  id: string;
  organization_id: string;
  organization_name: string;
  ehr_system: string;
  base_url: string;
  is_active: boolean;
  is_sandbox: boolean;
  last_tested_at?: string;
  last_sync_at?: string;
}

interface PatientSearchParams {
  organizationId: string;
  firstName?: string;
  lastName?: string;
  dateOfBirth?: string;
  mrn?: string;
}

interface PatientSearchResult {
  ehr_id: string;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string;
  email?: string;
}

interface PatientSyncRequest {
  organizationId: string;
  ehrPatientId: string;
  localPatientId?: string;
  syncHistorical?: boolean;
}

interface PatientSyncResponse {
  success: boolean;
  patient_id: string;
  mrn: string;
  synced_data: {
    demographics: boolean;
    allergies: number;
    medications: number;
    conditions: number;
  };
}

class EHRApi {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  async getConnections(organizationId?: string): Promise<EHRConnection[]> {
    const params = organizationId ? { organization_id: organizationId } : {};
    const response = await axios.get(`${API_BASE_URL}/api/ehr/connections`, {
      headers: this.getAuthHeaders(),
      params,
    });
    return response.data;
  }

  async testConnection(connectionId: string): Promise<{ success: boolean; message?: string }> {
    const response = await axios.post(
      `${API_BASE_URL}/api/ehr/connections/${connectionId}/test`,
      {},
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  async searchPatients(params: PatientSearchParams): Promise<PatientSearchResult[]> {
    try {
      // Check if we should use EHRBASE (you can make this configurable)
      const activeIntegration = localStorage.getItem('activeEHRIntegration') || 'ehrbase';
      
      if (activeIntegration === 'ehrbase') {
        // Use EHRBASE service
        const ehrbasePatients = await ehrbaseService.searchPatients({
          firstName: params.firstName,
          lastName: params.lastName,
          dateOfBirth: params.dateOfBirth,
          mrn: params.mrn,
        });
        
        // Return EHRBASE patients in the expected format
        return ehrbasePatients;
      } else {
        // Use FHIR service for direct FHIR server integration
        const fhirPatients = await fhirService.searchPatients({
          given: params.firstName,
          family: params.lastName,
          birthdate: params.dateOfBirth,
          identifier: params.mrn,
        });
        
        // Convert FHIR patients to internal format
        return fhirPatients.map(fhirPatient => 
          fhirService.convertFHIRPatientToInternal(fhirPatient)
        );
      }
    } catch (error) {
      console.error('Error searching patients:', error);
      // Fallback to original API if both fail
      const response = await axios.post(
        `${API_BASE_URL}/api/ehr/search/patients`,
        {
          organization_id: params.organizationId,
          first_name: params.firstName,
          last_name: params.lastName,
          date_of_birth: params.dateOfBirth,
          mrn: params.mrn,
        },
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    }
  }

  async syncPatient(request: PatientSyncRequest): Promise<PatientSyncResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/ehr/sync/patient`,
      {
        organization_id: request.organizationId,
        ehr_patient_id: request.ehrPatientId,
        local_patient_id: request.localPatientId,
        sync_historical: request.syncHistorical || false,
      },
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  async refreshPatientData(patientId: string, organizationId: string): Promise<any> {
    const response = await axios.get(
      `${API_BASE_URL}/api/ehr/patient/${patientId}/refresh`,
      {
        headers: this.getAuthHeaders(),
        params: { organization_id: organizationId },
      }
    );
    return response.data;
  }

  async getPatientEncounters(
    patientId: string,
    organizationId: string,
    startDate?: Date,
    endDate?: Date
  ): Promise<any[]> {
    const params: any = { organization_id: organizationId };
    if (startDate) params.start_date = startDate.toISOString();
    if (endDate) params.end_date = endDate.toISOString();

    const response = await axios.get(
      `${API_BASE_URL}/api/ehr/patient/${patientId}/encounters`,
      {
        headers: this.getAuthHeaders(),
        params,
      }
    );
    return response.data;
  }

  async getLatestVitals(patientId: string, organizationId: string): Promise<any> {
    const response = await axios.get(
      `${API_BASE_URL}/api/ehr/patient/${patientId}/vitals/latest`,
      {
        headers: this.getAuthHeaders(),
        params: { organization_id: organizationId },
      }
    );
    return response.data;
  }
}

export const ehrApi = new EHRApi();