import axios, { AxiosError } from 'axios';
import { ehrbaseAPI } from './ehrbase-api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const EHRBASE_PROXY_URL = `${API_BASE_URL}/api/ehrbase/proxy`;

class EHRBaseService {
  private axiosInstance = axios.create({
    baseURL: EHRBASE_PROXY_URL,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  });

  // Test proxy health
  async testProxyHealth(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/ehrbase/proxy/health`);
      console.log('Proxy health check:', response.data);
      return response.data;
    } catch (error) {
      console.error('Proxy health check failed:', error);
      return null;
    }
  }

  // Test connection to EHRBase
  async testConnection(): Promise<boolean> {
    try {
      console.log('Testing EHRBASE connection...');
      console.log('Proxy URL:', EHRBASE_PROXY_URL);
      
      // Try multiple endpoints to test connectivity
      const endpoints = [
        { path: '/', name: 'Root' },
        { path: '/ehr', name: 'EHR endpoint' },
        { path: '/definition/template/adl1.4', name: 'Templates' }
      ];
      
      for (const endpoint of endpoints) {
        try {
          console.log(`Testing ${endpoint.name} at ${endpoint.path}...`);
          const response = await this.axiosInstance.get(endpoint.path);
          console.log(`✓ ${endpoint.name} responded:`, response.status);
          return true;
        } catch (err) {
          console.log(`✗ ${endpoint.name} failed`);
        }
      }
      
      return false;
    } catch (error) {
      console.error('EHRBase connection test failed:', error);
      if (axios.isAxiosError(error)) {
        console.error('Connection error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          url: error.config?.url
        });
      }
      return false;
    }
  }

  // Get EHR by subject ID
  async getEHRBySubjectId(subjectId: string): Promise<any> {
    try {
      const response = await this.axiosInstance.get(`/ehr`, {
        params: {
          subject_id: subjectId,
          subject_namespace: 'ehrbase'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get EHR:', error);
      throw error;
    }
  }

  // Create new EHR
  async createEHR(subjectId: string, subjectNamespace: string = 'ehrbase'): Promise<any> {
    try {
      const response = await this.axiosInstance.post('/ehr', {
        _type: 'EHR_STATUS',
        subject: {
          external_ref: {
            id: {
              _type: 'GENERIC_ID',
              value: subjectId,
              scheme: 'id_scheme'
            },
            namespace: subjectNamespace,
            type: 'PERSON'
          }
        },
        is_modifiable: true,
        is_queryable: true
      });
      return response.data;
    } catch (error) {
      console.error('Failed to create EHR:', error);
      throw error;
    }
  }

  // Get composition by ID
  async getComposition(ehrId: string, compositionId: string): Promise<any> {
    try {
      const response = await this.axiosInstance.get(
        `/ehr/${ehrId}/composition/${compositionId}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get composition:', error);
      throw error;
    }
  }

  // Create composition
  async createComposition(ehrId: string, composition: any): Promise<any> {
    try {
      const response = await this.axiosInstance.post(
        `/ehr/${ehrId}/composition`,
        composition,
        {
          headers: {
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to create composition:', error);
      throw error;
    }
  }

  // Execute AQL query
  async executeQuery(aql: string): Promise<any> {
    try {
      console.log('Executing AQL query using ehrbaseAPI...');
      const result = await ehrbaseAPI.executeAQL(aql);
      console.log('AQL query response:', result);
      return result;
    } catch (error) {
      console.error('Failed to execute AQL query:', error);
      if (axios.isAxiosError(error)) {
        console.error('AQL query error details:', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          headers: error.response?.headers
        });
      }
      throw error;
    }
  }

  // Get all EHRs
  async getAllEHRs(): Promise<any> {
    try {
      // Use the new ehrbaseAPI instead of direct AQL
      console.log('Getting all EHRs using ehrbaseAPI...');
      const result = await ehrbaseAPI.getAllEHRs();
      console.log('All EHRs result:', result);
      return result;
    } catch (error) {
      console.error('Failed to get all EHRs - Full error:', error);
      if (axios.isAxiosError(error)) {
        console.error('Request failed:', {
          url: error.config?.url,
          method: error.config?.method,
          status: error.response?.status,
          data: error.response?.data
        });
      }
      return { rows: [] };
    }
  }

  // Search for demographic compositions
  async searchDemographics(ehrId: string): Promise<any> {
    try {
      const aqlQuery = `
        SELECT 
          c/uid/value as compositionId,
          c/name/value as name,
          c/archetype_details/archetype_id/value as archetypeId,
          c/context/start_time/value as time
        FROM EHR e
        CONTAINS COMPOSITION c
        WHERE e/ehr_id/value = '${ehrId}'
      `;
      
      const result = await this.executeQuery(aqlQuery);
      console.log(`Demographics for EHR ${ehrId}:`, result);
      return result;
    } catch (error) {
      console.error('Failed to search demographics:', error);
      return null;
    }
  }

  // Get all compositions for an EHR to see what data exists
  async getEHRCompositions(ehrId: string): Promise<any> {
    try {
      console.log(`Checking compositions for EHR ${ehrId}...`);
      
      // Query to get all compositions and their data
      const aqlQuery = `
        SELECT 
          c/uid/value as compositionId,
          c/name/value as compositionName,
          c/archetype_details/archetype_id/value as archetypeId,
          c/content as content
        FROM EHR e
        CONTAINS COMPOSITION c
        WHERE e/ehr_id/value = '${ehrId}'
      `;
      
      const result = await this.executeQuery(aqlQuery);
      console.log(`Compositions found for ${ehrId}:`, result);
      
      // Try to get specific patient data if it exists
      if (result.rows && result.rows.length > 0) {
        // Look for demographic or patient data
        for (const row of result.rows) {
          console.log('Composition:', {
            id: row[0],
            name: row[1],
            archetype: row[2]
          });
        }
      }
      
      return result;
    } catch (error) {
      console.error('Failed to get compositions:', error);
      return null;
    }
  }


  // Search patients using AQL
  async searchPatients(params: {
    firstName?: string;
    lastName?: string;
    dateOfBirth?: string;
    mrn?: string;
  }): Promise<any[]> {
    console.log('EHRBASE searchPatients called with params:', params);
    
    try {
      // Use the new ehrbaseAPI to search for real patient data
      console.log('Searching for patients using ehrbaseAPI...');
      const patients = await ehrbaseAPI.searchPatients(params);
      
      console.log(`Found ${patients.length} patients from EHRBASE:`, patients);
      
      return patients;
    } catch (error) {
      console.error('Failed to search patients - Full error:', error);
      if (axios.isAxiosError(error)) {
        console.error('Axios error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          url: error.config?.url
        });
      }
      return [];
    }
  }


  // Get all templates
  async getTemplates(): Promise<any> {
    try {
      const response = await this.axiosInstance.get('/definition/template/adl1.4');
      return response.data;
    } catch (error) {
      console.error('Failed to get templates:', error);
      throw error;
    }
  }

  // Upload a template
  async uploadTemplate(templateId: string, template: string): Promise<any> {
    try {
      const response = await this.axiosInstance.post(
        `/definition/template/adl1.4/${templateId}`,
        template,
        {
          headers: {
            'Content-Type': 'application/xml'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to upload template:', error);
      throw error;
    }
  }
}

export const ehrbaseService = new EHRBaseService();