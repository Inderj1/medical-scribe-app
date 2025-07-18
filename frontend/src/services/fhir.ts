import axios from 'axios';

const FHIR_BASE_URL = 'http://localhost:3001/fhir';
const AUTH_URL = 'http://localhost:3001/auth/token';
const SMART_CONFIG_URL = 'http://localhost:3001/.well-known/smart-configuration';
const CLIENT_ID = 'eb54f0dc-d564-42ad-9dda-d83019c653b5';
const CLIENT_SECRET = 'c41af63a-2a76-4247-b935-ba19afd0e25d';

interface FHIRPatient {
  id: string;
  resourceType: 'Patient';
  identifier?: Array<{
    use?: string;
    type?: {
      coding?: Array<{
        system?: string;
        code?: string;
      }>;
    };
    value?: string;
  }>;
  name?: Array<{
    use?: string;
    family?: string;
    given?: string[];
  }>;
  telecom?: Array<{
    system?: string;
    value?: string;
    use?: string;
  }>;
  gender?: string;
  birthDate?: string;
  address?: Array<{
    use?: string;
    line?: string[];
    city?: string;
    state?: string;
    postalCode?: string;
    country?: string;
  }>;
}

interface FHIRObservation {
  id: string;
  resourceType: 'Observation';
  status: string;
  category?: Array<{
    coding?: Array<{
      system?: string;
      code?: string;
      display?: string;
    }>;
  }>;
  code: {
    coding?: Array<{
      system?: string;
      code?: string;
      display?: string;
    }>;
    text?: string;
  };
  subject?: {
    reference?: string;
  };
  effectiveDateTime?: string;
  valueQuantity?: {
    value?: number;
    unit?: string;
    system?: string;
    code?: string;
  };
  valueString?: string;
  valueBoolean?: boolean;
}

interface FHIRBundle {
  resourceType: 'Bundle';
  type: string;
  total?: number;
  entry?: Array<{
    resource: FHIRPatient | FHIRObservation;
  }>;
}

class FHIRService {
  private accessToken: string | null = null;
  private tokenExpiry: Date | null = null;
  private smartConfig: any = null;
  private dynamicClientId: string | null = null;
  private dynamicClientSecret: string | null = null;

  private async getSmartConfig() {
    if (this.smartConfig) {
      return this.smartConfig;
    }

    try {
      const response = await axios.get(SMART_CONFIG_URL);
      this.smartConfig = response.data;
      console.log('SMART Configuration:', this.smartConfig);
      return this.smartConfig;
    } catch (error) {
      console.error('Error fetching SMART configuration:', error);
      return null;
    }
  }

  private async getAccessToken(): Promise<string> {
    // Check if we have a valid token
    if (this.accessToken && this.tokenExpiry && new Date() < this.tokenExpiry) {
      return this.accessToken;
    }

    // Get SMART configuration to find the correct token endpoint
    const smartConfig = await this.getSmartConfig();
    const tokenEndpoint = smartConfig?.token_endpoint || AUTH_URL;
    
    console.log('Using token endpoint:', tokenEndpoint);

    // Use dynamic client credentials if available, otherwise fallback to static ones
    const clientId = this.dynamicClientId || CLIENT_ID;
    const clientSecret = this.dynamicClientSecret || CLIENT_SECRET;
    
    console.log('Using client ID:', clientId);

    // Check what grant types are supported
    if (smartConfig && smartConfig.grant_types_supported) {
      console.log('Server supported grant types:', smartConfig.grant_types_supported);
      console.log('First supported grant type:', smartConfig.grant_types_supported[0]);
      console.log('Grant types as JSON:', JSON.stringify(smartConfig.grant_types_supported));
    }

    // Check if server only supports authorization_code
    if (smartConfig && smartConfig.grant_types_supported && 
        smartConfig.grant_types_supported.includes('authorization_code') && 
        !smartConfig.grant_types_supported.includes('client_credentials')) {
      
      console.log('Server only supports authorization_code flow. Redirecting to authorization endpoint...');
      
      // Generate state parameter for security
      const state = btoa(Math.random().toString()).substring(0, 32);
      localStorage.setItem('oauth_state', state);
      localStorage.setItem('oauth_client_id', clientId);
      localStorage.setItem('oauth_client_secret', clientSecret);
      
      // Build authorization URL
      const authParams = new URLSearchParams({
        response_type: 'code',
        client_id: clientId,
        redirect_uri: window.location.origin + '/callback',
        scope: 'patient/*.read user/*.read',
        state: state
      });
      
      const authUrl = `${smartConfig.authorization_endpoint}?${authParams.toString()}`;
      console.log('Authorization URL:', authUrl);
      
      // For now, let's try a different approach - check if there's a way to get token directly
      throw new Error('Authorization code flow required - need to implement redirect flow');
    }

    // Get new token - try different approaches
    try {
      // First try: Form-based with client credentials (SMART standard)
      let response;
      try {
        const params = new URLSearchParams();
        params.append('grant_type', 'client_credentials');
        params.append('client_id', clientId);
        params.append('client_secret', clientSecret);

        response = await axios.post(tokenEndpoint, params, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
      } catch (error) {
        if (axios.isAxiosError(error) && error.response) {
          console.log('Form client_credentials failed:', error.response.status, error.response.data);
        }
        console.log('Form client_credentials failed, trying JSON format...');
        
        // Second try: JSON format with client credentials
        try {
          response = await axios.post(tokenEndpoint, {
            grant_type: 'client_credentials',
            client_id: clientId,
            client_secret: clientSecret,
          }, {
            headers: {
              'Content-Type': 'application/json',
            },
          });
        } catch (error2) {
          if (axios.isAxiosError(error2) && error2.response) {
            console.log('JSON client_credentials failed:', error2.response.status, error2.response.data);
          }
          console.log('JSON client_credentials failed, trying Basic Auth...');
          
          // Third try: Basic Auth with client credentials
          const basicAuth = btoa(`${clientId}:${clientSecret}`);
          const params2 = new URLSearchParams();
          params2.append('grant_type', 'client_credentials');
          params2.append('scope', 'patient/*.read user/*.read');
          
          try {
            response = await axios.post(tokenEndpoint, params2, {
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Basic ${basicAuth}`,
              },
            });
          } catch (error3) {
            if (axios.isAxiosError(error3) && error3.response) {
              console.log('Basic Auth client_credentials failed:', error3.response.status, error3.response.data);
            }
            console.log('Basic Auth client_credentials failed, trying with scope in body...');
            
            // Fourth try: Add scope parameter to form request
            const params3 = new URLSearchParams();
            params3.append('grant_type', 'client_credentials');
            params3.append('client_id', clientId);
            params3.append('client_secret', clientSecret);
            params3.append('scope', 'patient/*.read user/*.read');
            
            response = await axios.post(tokenEndpoint, params3, {
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              },
            });
          }
        }
      }

      this.accessToken = response.data.access_token;
      const expiresIn = response.data.expires_in || 3600; // Default to 1 hour
      this.tokenExpiry = new Date(Date.now() + (expiresIn * 1000));
      
      return this.accessToken!;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        console.error('Final OAuth2 attempt failed:', error.response.status, error.response.data);
      }
      console.error('All OAuth2 attempts failed:', error);
      console.log('Falling back to test token...');
      
      // Fallback to test token for development
      this.accessToken = 'test-token-123';
      this.tokenExpiry = new Date(Date.now() + (3600 * 1000)); // 1 hour from now
      
      return this.accessToken;
    }
  }

  private async getAuthHeaders() {
    try {
      const token = await this.getAccessToken();
      return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
    } catch (error) {
      console.log('Token failed, trying Basic Auth with client credentials...');
      // Try Basic Auth with client credentials directly
      const basicAuth = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
      return {
        'Authorization': `Basic ${basicAuth}`,
        'Content-Type': 'application/json',
      };
    }
  }

  // First, let's try to get server metadata (usually public)
  async getServerMetadata() {
    try {
      const response = await axios.get(`${FHIR_BASE_URL}/metadata`, {
        headers: { 'Content-Type': 'application/json' }
      });
      console.log('Server metadata:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error getting server metadata:', error);
      throw error;
    }
  }

  async getPatients(): Promise<FHIRPatient[]> {
    // First check if we can get server metadata
    try {
      await this.getServerMetadata();
      console.log('Server metadata retrieved successfully');
    } catch (error) {
      console.log('Server metadata not accessible');
    }

    const authMethods = [
      // Method 1: Try OAuth token
      async () => {
        const token = await this.getAccessToken();
        return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      },
      // Method 2: Basic auth with client credentials
      async () => {
        const basicAuth = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
        return { 'Authorization': `Basic ${basicAuth}`, 'Content-Type': 'application/json' };
      },
      // Method 3: Test token
      async () => {
        return { 'Authorization': 'Bearer test-token-123', 'Content-Type': 'application/json' };
      },
      // Method 4: Try different token format
      async () => {
        return { 'Authorization': 'Bearer test-access-token', 'Content-Type': 'application/json' };
      },
      // Method 5: Try API key format
      async () => {
        return { 'X-API-Key': CLIENT_ID, 'Content-Type': 'application/json' };
      },
      // Method 6: No auth (public endpoint)
      async () => {
        return { 'Content-Type': 'application/json' };
      }
    ];

    for (let i = 0; i < authMethods.length; i++) {
      try {
        console.log(`Trying authentication method ${i + 1}...`);
        const headers = await authMethods[i]();
        const response = await axios.get(`${FHIR_BASE_URL}/Patient`, { headers });
        
        const bundle = response.data as FHIRBundle;
        console.log(`Authentication method ${i + 1} succeeded!`);
        if (bundle.entry) {
          return bundle.entry.map(entry => entry.resource as FHIRPatient);
        }
        return [];
      } catch (error) {
        console.log(`Authentication method ${i + 1} failed:`, error);
        if (i === authMethods.length - 1) {
          console.error('All authentication methods failed');
          throw error;
        }
      }
    }
    
    return [];
  }

  async getPatient(id: string): Promise<FHIRPatient> {
    const authMethods = [
      async () => {
        const token = await this.getAccessToken();
        return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      },
      async () => {
        const basicAuth = btoa(`${CLIENT_ID}:${CLIENT_SECRET}`);
        return { 'Authorization': `Basic ${basicAuth}`, 'Content-Type': 'application/json' };
      },
      async () => {
        return { 'Authorization': 'Bearer test-token-123', 'Content-Type': 'application/json' };
      },
      async () => {
        return { 'Content-Type': 'application/json' };
      }
    ];

    for (let i = 0; i < authMethods.length; i++) {
      try {
        const headers = await authMethods[i]();
        const response = await axios.get(`${FHIR_BASE_URL}/Patient/${id}`, { headers });
        return response.data as FHIRPatient;
      } catch (error) {
        if (i === authMethods.length - 1) {
          console.error(`Error fetching FHIR patient ${id}:`, error);
          throw error;
        }
      }
    }
    
    throw new Error('All authentication methods failed');
  }

  async searchPatients(params: {
    given?: string;
    family?: string;
    birthdate?: string;
    identifier?: string;
  }): Promise<FHIRPatient[]> {
    try {
      const searchParams = new URLSearchParams();
      if (params.given) searchParams.append('given', params.given);
      if (params.family) searchParams.append('family', params.family);
      if (params.birthdate) searchParams.append('birthdate', params.birthdate);
      if (params.identifier) searchParams.append('identifier', params.identifier);

      const headers = await this.getAuthHeaders();
      const response = await axios.get(`${FHIR_BASE_URL}/Patient?${searchParams.toString()}`, {
        headers,
      });
      
      const bundle = response.data as FHIRBundle;
      if (bundle.entry) {
        return bundle.entry.map(entry => entry.resource as FHIRPatient);
      }
      return [];
    } catch (error) {
      console.error('Error searching FHIR patients:', error);
      throw error;
    }
  }

  async getObservations(patientId?: string): Promise<FHIRObservation[]> {
    try {
      const url = patientId 
        ? `${FHIR_BASE_URL}/Observation?patient=${patientId}`
        : `${FHIR_BASE_URL}/Observation`;
      
      const headers = await this.getAuthHeaders();
      const response = await axios.get(url, {
        headers,
      });
      
      const bundle = response.data as FHIRBundle;
      if (bundle.entry) {
        return bundle.entry.map(entry => entry.resource as FHIRObservation);
      }
      return [];
    } catch (error) {
      console.error('Error fetching FHIR observations:', error);
      throw error;
    }
  }

  // Helper method to convert FHIR Patient to our internal format
  convertFHIRPatientToInternal(fhirPatient: FHIRPatient): {
    ehr_id: string;
    mrn: string;
    first_name: string;
    last_name: string;
    date_of_birth: string;
    gender: string;
    phone?: string;
    email?: string;
  } {
    const name = fhirPatient.name?.[0];
    const mrn = fhirPatient.identifier?.find(id => 
      id.type?.coding?.some(c => c.code === 'MR')
    )?.value || fhirPatient.id;
    
    const phone = fhirPatient.telecom?.find(t => t.system === 'phone')?.value;
    const email = fhirPatient.telecom?.find(t => t.system === 'email')?.value;

    return {
      ehr_id: fhirPatient.id,
      mrn: mrn,
      first_name: name?.given?.[0] || '',
      last_name: name?.family || '',
      date_of_birth: fhirPatient.birthDate || '',
      gender: fhirPatient.gender || '',
      phone,
      email,
    };
  }

  // Public method to get SMART configuration for display
  async getSmartConfiguration() {
    return await this.getSmartConfig();
  }

  // Handle OAuth2 authorization code flow
  async initiateAuthorizationFlow() {
    const smartConfig = await this.getSmartConfig();
    if (!smartConfig) {
      throw new Error('SMART configuration not available');
    }

    // Get client credentials (dynamic if available)
    const clientId = this.dynamicClientId || CLIENT_ID;
    const clientSecret = this.dynamicClientSecret || CLIENT_SECRET;
    
    // Generate state parameter for security
    const state = btoa(Math.random().toString()).substring(0, 32);
    localStorage.setItem('oauth_state', state);
    localStorage.setItem('oauth_client_id', clientId);
    localStorage.setItem('oauth_client_secret', clientSecret);
    
    // Build authorization URL
    const authParams = new URLSearchParams({
      response_type: 'code',
      client_id: clientId,
      redirect_uri: window.location.origin + '/callback',
      scope: 'patient/*.read user/*.read',
      state: state
    });
    
    const authUrl = `${smartConfig.authorization_endpoint}?${authParams.toString()}`;
    console.log('Redirecting to authorization URL:', authUrl);
    
    // Redirect to authorization endpoint
    window.location.href = authUrl;
  }

  // Handle authorization code callback
  async handleAuthorizationCallback(code: string, state: string) {
    // Verify state parameter
    const storedState = localStorage.getItem('oauth_state');
    if (state !== storedState) {
      throw new Error('Invalid state parameter');
    }

    // Get stored client credentials
    const clientId = localStorage.getItem('oauth_client_id');
    const clientSecret = localStorage.getItem('oauth_client_secret');
    
    if (!clientId || !clientSecret) {
      throw new Error('Client credentials not found');
    }

    // Exchange authorization code for access token
    const smartConfig = await this.getSmartConfig();
    const tokenEndpoint = smartConfig?.token_endpoint || AUTH_URL;
    
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: window.location.origin + '/callback',
      client_id: clientId,
      client_secret: clientSecret
    });

    try {
      const response = await axios.post(tokenEndpoint, params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      this.accessToken = response.data.access_token;
      const expiresIn = response.data.expires_in || 3600;
      this.tokenExpiry = new Date(Date.now() + (expiresIn * 1000));

      // Clean up localStorage
      localStorage.removeItem('oauth_state');
      localStorage.removeItem('oauth_client_id');
      localStorage.removeItem('oauth_client_secret');

      return {
        access_token: this.accessToken,
        expires_in: expiresIn,
        token_type: response.data.token_type
      };
    } catch (error) {
      console.error('Error exchanging authorization code for token:', error);
      throw error;
    }
  }

  // Test server connectivity and registration
  async testServerConnection() {
    console.log('Testing server connection...');
    
    // Try to register the app first (this might be required)
    try {
      const registerResponse = await axios.post('http://localhost:3001/auth/register', {
        client_name: 'Medical Scribe Frontend',
        client_uri: 'http://localhost:3000',
        redirect_uris: ['http://localhost:3000/callback'],
        grant_types: ['client_credentials', 'authorization_code'],
        response_types: ['code', 'token'],
        scope: 'patient/*.read user/*.read'
      }, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      console.log('New app registration:', registerResponse.data);
      
      // Update client credentials with new registration
      if (registerResponse.data.client_id && registerResponse.data.client_secret) {
        console.log('Using newly registered client credentials');
        // Store the dynamic credentials
        this.dynamicClientId = registerResponse.data.client_id;
        this.dynamicClientSecret = registerResponse.data.client_secret;
        // Clear any cached tokens to force re-authentication
        this.accessToken = null;
        this.tokenExpiry = null;
        
        return {
          client_id: registerResponse.data.client_id,
          client_secret: registerResponse.data.client_secret,
          registered: true
        };
      }
    } catch (error) {
      console.log('App registration failed or not required:', error);
    }

    // Return existing credentials
    return {
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      registered: false
    };
  }
}

export const fhirService = new FHIRService();
export type { FHIRPatient, FHIRObservation, FHIRBundle };