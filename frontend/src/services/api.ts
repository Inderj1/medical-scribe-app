import { useAuth } from '@clerk/clerk-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function to get auth headers
export async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await (window as any).Clerk?.session?.getToken();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// Helper function for authenticated fetch
export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(url, {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers,
    },
  });

  if (!response.ok && response.status === 401) {
    // Handle unauthorized - could redirect to login
    console.error('Unauthorized request');
  }

  return response;
}

// Transcription API
export const transcriptionAPI = {
  // Upload audio file for transcription
  async uploadAudio(
    encounterId: string,
    audioFile: File | Blob,
    formatPreference: string = 'soap',
    language: string = 'en'
  ) {
    const formData = new FormData();
    formData.append('encounter_id', encounterId);
    formData.append('audio_file', audioFile);
    formData.append('format_preference', formatPreference);
    formData.append('language', language);

    const token = await (window as any).Clerk?.session?.getToken();
    const response = await fetch(`${API_BASE}/api/v1/transcription/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload audio');
    }

    return response.json();
  },

  // Get transcription status and results
  async getTranscription(transcriptionId: string) {
    const response = await authFetch(`${API_BASE}/api/v1/transcription/${transcriptionId}`);
    return response.json();
  },

  // Get clinical note for transcription
  async getClinicalNote(transcriptionId: string) {
    const response = await authFetch(`${API_BASE}/api/v1/transcription/${transcriptionId}/clinical-note`);
    return response.json();
  },

  // List transcriptions
  async listTranscriptions(params?: {
    encounterId?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.encounterId) queryParams.append('encounter_id', params.encounterId);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const response = await authFetch(`${API_BASE}/api/v1/transcription?${queryParams.toString()}`);
    return response.json();
  },
};

// Encounter API
export const encounterAPI = {
  // Create encounter
  async createEncounter(encounterData: {
    patient_id: string;
    chief_complaint?: string;
    encounter_type?: string;
    provider_name?: string;
    location?: string;
    metadata?: any;
  }) {
    const response = await authFetch(`${API_BASE}/api/v1/encounters`, {
      method: 'POST',
      body: JSON.stringify(encounterData),
    });
    return response.json();
  },

  // Get encounter
  async getEncounter(encounterId: string) {
    const response = await authFetch(`${API_BASE}/api/v1/encounters/${encounterId}`);
    return response.json();
  },

  // Update encounter
  async updateEncounter(encounterId: string, updateData: any) {
    const response = await authFetch(`${API_BASE}/api/v1/encounters/${encounterId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
    return response.json();
  },

  // List encounters
  async listEncounters(params?: {
    patientId?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.patientId) queryParams.append('patient_id', params.patientId);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const response = await authFetch(`${API_BASE}/api/v1/encounters?${queryParams.toString()}`);
    return response.json();
  },
};

// Patient API
export const patientAPI = {
  // Search patients
  async searchPatients(query: string) {
    const response = await authFetch(`${API_BASE}/api/v1/patients/search?q=${encodeURIComponent(query)}`);
    return response.json();
  },

  // Get patient
  async getPatient(patientId: string) {
    const response = await authFetch(`${API_BASE}/api/v1/patients/${patientId}`);
    return response.json();
  },

  // Create patient
  async createPatient(patientData: any) {
    const response = await authFetch(`${API_BASE}/api/v1/patients`, {
      method: 'POST',
      body: JSON.stringify(patientData),
    });
    return response.json();
  },

  // Update patient
  async updatePatient(patientId: string, updateData: any) {
    const response = await authFetch(`${API_BASE}/api/v1/patients/${patientId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
    return response.json();
  },
};

// Test endpoints
export const testAPI = {
  // Test agent system
  async testAgents() {
    const response = await authFetch(`${API_BASE}/api/test/agents`);
    return response.json();
  },

  // Test OpenAI connection
  async testOpenAI() {
    const response = await authFetch(`${API_BASE}/api/test/openai`);
    return response.json();
  },

  // Health check
  async healthCheck() {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },
};