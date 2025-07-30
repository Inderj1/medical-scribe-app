import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const EHRBASE_PROXY_URL = `${API_BASE_URL}/api/ehrbase/proxy`;
const EHR_DIRECT_URL = 'http://3.223.44.85';

interface EHRData {
  ehr_id: {
    value: string;
  };
  system_id: {
    value: string;
  };
  ehr_status: {
    subject: {
      external_ref: {
        id: {
          value: string;
        };
        namespace: string;
      };
    };
  };
  time_created: {
    value: string;
  };
}

interface CompositionData {
  uid: {
    value: string;
  };
  name: {
    value: string;
  };
  archetype_details: {
    archetype_id: {
      value: string;
    };
    template_id?: {
      value: string;
    };
  };
  content?: any[];
}

class EHRBaseAPI {
  private axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: EHRBASE_PROXY_URL,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
  }

  // ==================== EHR ENDPOINTS ====================

  // Get EHR by ID
  async getEHR(ehrId: string): Promise<EHRData> {
    const response = await this.axiosInstance.get(`/ehr/${ehrId}`);
    return response.data;
  }

  // Get EHR by subject ID and namespace
  async getEHRBySubject(subjectId: string, subjectNamespace: string = 'default'): Promise<EHRData> {
    const response = await this.axiosInstance.get('/ehr', {
      params: {
        subject_id: subjectId,
        subject_namespace: subjectNamespace
      }
    });
    return response.data;
  }

  // Create new EHR
  async createEHR(subjectId: string, subjectNamespace: string = 'default'): Promise<EHRData> {
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
  }

  // Create EHR with specific ID
  async createEHRWithId(ehrId: string, subjectId: string, subjectNamespace: string = 'default'): Promise<EHRData> {
    const response = await this.axiosInstance.put(`/ehr/${ehrId}`, {
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
  }

  // ==================== COMPOSITION ENDPOINTS ====================

  // Get composition
  async getComposition(ehrId: string, compositionId: string): Promise<CompositionData> {
    const response = await this.axiosInstance.get(
      `/ehr/${ehrId}/composition/${compositionId}`
    );
    return response.data;
  }

  // Create composition
  async createComposition(ehrId: string, composition: any): Promise<CompositionData> {
    const response = await this.axiosInstance.post(
      `/ehr/${ehrId}/composition`,
      composition,
      {
        headers: {
          'Prefer': 'return=representation'
        }
      }
    );
    return response.data;
  }

  // Update composition
  async updateComposition(ehrId: string, compositionId: string, composition: any): Promise<CompositionData> {
    const response = await this.axiosInstance.put(
      `/ehr/${ehrId}/composition/${compositionId}`,
      composition,
      {
        headers: {
          'Prefer': 'return=representation'
        }
      }
    );
    return response.data;
  }

  // Delete composition
  async deleteComposition(ehrId: string, precedingVersionUid: string): Promise<void> {
    await this.axiosInstance.delete(
      `/ehr/${ehrId}/composition/${precedingVersionUid}`
    );
  }

  // ==================== QUERY ENDPOINTS ====================

  // Execute AQL query
  async executeAQL(aql: string, parameters?: Record<string, any>): Promise<any> {
    const response = await this.axiosInstance.post('/query/aql', {
      q: aql,
      ...parameters
    });
    return response.data;
  }

  // Execute stored query
  async executeStoredQuery(queryName: string, parameters?: Record<string, any>): Promise<any> {
    const response = await this.axiosInstance.post(
      `/query/${queryName}`,
      parameters || {}
    );
    return response.data;
  }

  // ==================== TEMPLATE ENDPOINTS ====================

  // List all templates
  async listTemplates(): Promise<any[]> {
    const response = await this.axiosInstance.get('/definition/template/adl1.4');
    return response.data;
  }

  // Get specific template
  async getTemplate(templateId: string): Promise<any> {
    const response = await this.axiosInstance.get(
      `/definition/template/adl1.4/${templateId}`
    );
    return response.data;
  }

  // Get example composition for template
  async getTemplateExample(templateId: string): Promise<any> {
    const response = await this.axiosInstance.get(
      `/definition/template/adl1.4/${templateId}/example`
    );
    return response.data;
  }

  // Upload template
  async uploadTemplate(templateContent: string): Promise<any> {
    const response = await this.axiosInstance.post(
      '/definition/template/adl1.4',
      templateContent,
      {
        headers: {
          'Content-Type': 'application/xml'
        }
      }
    );
    return response.data;
  }

  // ==================== NEW MEDICAL RECORD EXTRACTION ENDPOINTS ====================

  // Get patient records using the new API
  async getPatientRecords(patientId: string): Promise<any> {
    try {
      const response = await axios.get(`${EHR_DIRECT_URL}/api/patients/${patientId}/records`);
      return response.data;
    } catch (error) {
      console.error('Failed to get patient records:', error);
      throw error;
    }
  }

  // Get specific record by ID
  async getRecord(recordId: string): Promise<any> {
    try {
      const response = await axios.get(`${EHR_DIRECT_URL}/api/records/${recordId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get record:', error);
      throw error;
    }
  }

  // Get specific section of a record
  async getRecordSection(recordId: string, section: 'history' | 'examination' | 'assessment' | 'plan'): Promise<any> {
    try {
      const response = await axios.get(`${EHR_DIRECT_URL}/api/records/${recordId}/sections/${section}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get ${section} section:`, error);
      throw error;
    }
  }

  // Get patient summary
  async getPatientSummary(patientId: string): Promise<any> {
    try {
      const response = await axios.get(`${EHR_DIRECT_URL}/api/summary/${patientId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get patient summary:', error);
      throw error;
    }
  }

  // Direct OpenEHR API access for compositions
  async getCompositions(ehrId: string): Promise<any> {
    try {
      const response = await axios.get(`${EHR_DIRECT_URL}/ehrbase/rest/openehr/v1/ehr/${ehrId}/composition`);
      return response.data;
    } catch (error) {
      console.error('Failed to get compositions:', error);
      throw error;
    }
  }

  // Execute complex AQL queries directly on EHRBase
  async executeComplexAQL(query: string): Promise<any> {
    try {
      const response = await axios.post(`${EHR_DIRECT_URL}/ehrbase/rest/openehr/v1/query/aql`, {
        q: query
      }, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to execute AQL query:', error);
      throw error;
    }
  }

  // ==================== HELPER FUNCTIONS ====================

  // Get all EHRs using AQL
  async getAllEHRs(): Promise<any> {
    const aql = `
      SELECT 
        e/ehr_id/value as ehrId,
        e/ehr_status/subject/external_ref/id/value as subjectId,
        e/ehr_status/subject/external_ref/namespace as subjectNamespace,
        e/time_created/value as timeCreated
      FROM EHR e
    `;
    return this.executeAQL(aql);
  }

  // Search for patients with demographic data
  async searchPatients(filters?: {
    firstName?: string;
    lastName?: string;
    dateOfBirth?: string;
    mrn?: string;
  }): Promise<any[]> {
    try {
      console.log('Searching for patients in EHR system...');
      
      // Use direct EHR endpoint
      const response = await axios.get(`${EHR_DIRECT_URL}/api/patients`, {
        params: filters
      });
      
      console.log('Patients found:', response.data);
      // Check if response has a 'patients' property (API returns {patients: [...]})
      if (response.data && response.data.patients) {
        return response.data.patients;
      }
      return response.data || [];
      
    } catch (error) {
      console.error('Failed to search patients:', error);
      return [];
    }
  }

  // Get dotphrases from EHR system
  async getDotphrases(): Promise<any[]> {
    try {
      console.log('Fetching dotphrases from EHR system...');
      
      const response = await axios.get(`${EHR_DIRECT_URL}/api/dotphrases`);
      
      console.log('Dotphrases found:', response.data);
      // Check if response has a 'dotphrases' property
      if (response.data && response.data.dotphrases) {
        return response.data.dotphrases;
      }
      return response.data || [];
      
    } catch (error) {
      console.error('Failed to fetch dotphrases:', error);
      return [];
    }
  }

  // Create a patient demographic composition
  async createPatientDemographics(ehrId: string, demographics: {
    firstName: string;
    lastName: string;
    dateOfBirth: string;
    gender: string;
    mrn?: string;
  }): Promise<any> {
    const composition = {
      _type: 'COMPOSITION',
      name: {
        _type: 'DV_TEXT',
        value: 'Patient Demographics'
      },
      archetype_details: {
        _type: 'ARCHETYPED',
        archetype_id: {
          _type: 'ARCHETYPE_ID',
          value: 'openEHR-EHR-COMPOSITION.person.v1'
        },
        rm_version: '1.0.4'
      },
      language: {
        _type: 'CODE_PHRASE',
        terminology_id: {
          _type: 'TERMINOLOGY_ID',
          value: 'ISO_639-1'
        },
        code_string: 'en'
      },
      territory: {
        _type: 'CODE_PHRASE',
        terminology_id: {
          _type: 'TERMINOLOGY_ID',
          value: 'ISO_3166-1'
        },
        code_string: 'US'
      },
      category: {
        _type: 'DV_CODED_TEXT',
        value: 'event',
        defining_code: {
          _type: 'CODE_PHRASE',
          terminology_id: {
            _type: 'TERMINOLOGY_ID',
            value: 'openehr'
          },
          code_string: '433'
        }
      },
      composer: {
        _type: 'PARTY_IDENTIFIED',
        name: 'Medical Scribe System'
      },
      content: [{
        _type: 'ADMIN_ENTRY',
        name: {
          _type: 'DV_TEXT',
          value: 'Person data'
        },
        archetype_details: {
          _type: 'ARCHETYPED',
          archetype_id: {
            _type: 'ARCHETYPE_ID',
            value: 'openEHR-EHR-ADMIN_ENTRY.person_data.v1'
          },
          rm_version: '1.0.4'
        },
        language: {
          _type: 'CODE_PHRASE',
          terminology_id: {
            _type: 'TERMINOLOGY_ID',
            value: 'ISO_639-1'
          },
          code_string: 'en'
        },
        encoding: {
          _type: 'CODE_PHRASE',
          terminology_id: {
            _type: 'TERMINOLOGY_ID',
            value: 'IANA_character-sets'
          },
          code_string: 'UTF-8'
        },
        data: {
          _type: 'ITEM_TREE',
          name: {
            _type: 'DV_TEXT',
            value: 'Person data'
          },
          archetype_node_id: 'at0001',
          items: [
            {
              _type: 'ELEMENT',
              name: {
                _type: 'DV_TEXT',
                value: 'First name'
              },
              archetype_node_id: 'at0002',
              value: {
                _type: 'DV_TEXT',
                value: demographics.firstName
              }
            },
            {
              _type: 'ELEMENT',
              name: {
                _type: 'DV_TEXT',
                value: 'Last name'
              },
              archetype_node_id: 'at0003',
              value: {
                _type: 'DV_TEXT',
                value: demographics.lastName
              }
            },
            {
              _type: 'ELEMENT',
              name: {
                _type: 'DV_TEXT',
                value: 'Date of birth'
              },
              archetype_node_id: 'at0004',
              value: {
                _type: 'DV_DATE',
                value: demographics.dateOfBirth
              }
            },
            {
              _type: 'ELEMENT',
              name: {
                _type: 'DV_TEXT',
                value: 'Gender'
              },
              archetype_node_id: 'at0005',
              value: {
                _type: 'DV_CODED_TEXT',
                value: demographics.gender,
                defining_code: {
                  _type: 'CODE_PHRASE',
                  terminology_id: {
                    _type: 'TERMINOLOGY_ID',
                    value: 'local'
                  },
                  code_string: demographics.gender
                }
              }
            }
          ]
        }
      }]
    };

    return this.createComposition(ehrId, composition);
  }

  // Get patient encounters/compositions
  async getPatientEncounters(ehrId: string): Promise<any[]> {
    try {
      console.log(`Getting encounters for EHR ID: ${ehrId}`);
      
      // Use AQL to get patient encounters/compositions
      const aqlQuery = `
        SELECT 
          c/uid/value as composition_id,
          c/context/start_time/value as encounter_date,
          c/content[openEHR-EHR-EVALUATION.clinical_synopsis.v1]/data[at0001]/items[at0002]/value/value as chief_complaint,
          c/content[openEHR-EHR-OBSERVATION.vital_signs.v1]/data[at0001]/events[at0006]/data[at0003]/items as vitals,
          c/composer/name as provider_name
        FROM EHR e[ehr_id/value='${ehrId}']
        CONTAINS COMPOSITION c
        ORDER BY c/context/start_time/value DESC
        LIMIT 10
      `;

      const result = await this.executeAQL(aqlQuery);
      
      if (result && result.rows) {
        const encounters = result.rows.map((row: any[], index: number) => ({
          id: row[0] || `enc-${Date.now()}-${index}`,
          encounter_date: row[1] || new Date().toISOString(),
          chief_complaint: row[2] || 'General consultation',
          vitals: this.parseVitals(row[3]),
          provider_name: row[4] || 'Dr. Smith',
          encounter_type: 'Outpatient',
          status: 'Completed',
          diagnosis: [],
          notes: ''
        }));
        
        console.log(`Found ${encounters.length} encounters for EHR ${ehrId}`);
        return encounters;
      }
      
      return [];
    } catch (error) {
      console.error('Error getting patient encounters:', error);
      return [];
    }
  }

  // Helper method to parse vitals from AQL result
  private parseVitals(vitalsData: any): any {
    if (!vitalsData || !Array.isArray(vitalsData)) {
      return {};
    }

    const vitals: any = {};
    for (const vital of vitalsData) {
      if (vital && vital.name && vital.value) {
        const name = vital.name.value.toLowerCase();
        const value = vital.value.magnitude || vital.value.value || vital.value;
        
        if (name.includes('blood pressure')) {
          vitals.blood_pressure = `${value}`;
        } else if (name.includes('heart rate')) {
          vitals.heart_rate = `${value}`;
        } else if (name.includes('temperature')) {
          vitals.temperature = `${value}°F`;
        } else if (name.includes('oxygen')) {
          vitals.oxygen_saturation = `${value}%`;
        }
      }
    }
    
    return vitals;
  }
}

export const ehrbaseAPI = new EHRBaseAPI();