import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface SignUpData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  role?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    full_name: string;
    role: string;
  };
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
}

class AuthService {
  private token: string | null = null;
  private user: User | null = null;

  constructor() {
    // Load token from localStorage on initialization
    const savedToken = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    
    if (savedToken) {
      this.token = savedToken;
      this.setAuthHeader(savedToken);
    }
    
    if (savedUser) {
      try {
        this.user = JSON.parse(savedUser);
      } catch (error) {
        console.error('Error parsing saved user:', error);
      }
    }
  }

  private setAuthHeader(token: string): void {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  private clearAuthHeader(): void {
    delete axios.defaults.headers.common['Authorization'];
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      // FastAPI expects form data for OAuth2
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/auth/login`,
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      const { access_token, user } = response.data;
      
      // Save token and user
      this.token = access_token;
      this.user = user;
      
      // Persist to localStorage
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // Set authorization header for future requests
      this.setAuthHeader(access_token);

      return response.data;
    } catch (error: any) {
      console.error('Login error:', error.response?.data || error.message);
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  }

  async signUp(data: SignUpData): Promise<AuthResponse> {
    try {
      const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/auth/signup`,
        data
      );

      const { access_token, user } = response.data;
      
      // Save token and user
      this.token = access_token;
      this.user = user;
      
      // Persist to localStorage
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // Set authorization header for future requests
      this.setAuthHeader(access_token);

      return response.data;
    } catch (error: any) {
      console.error('Sign up error:', error.response?.data || error.message);
      throw new Error(error.response?.data?.detail || 'Sign up failed');
    }
  }

  async logout(): Promise<void> {
    // Clear token and user
    this.token = null;
    this.user = null;
    
    // Clear from localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    
    // Clear authorization header
    this.clearAuthHeader();
  }

  async getCurrentUser(): Promise<User | null> {
    if (!this.token) {
      return null;
    }

    try {
      const response = await axios.get<User>(`${API_BASE_URL}/auth/me`);
      this.user = response.data;
      localStorage.setItem('user', JSON.stringify(this.user));
      return this.user;
    } catch (error) {
      console.error('Error fetching current user:', error);
      // If token is invalid, clear it
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        await this.logout();
      }
      return null;
    }
  }

  getToken(): string | null {
    return this.token;
  }

  getUser(): User | null {
    return this.user;
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  // Create a demo user for testing
  async loginDemo(): Promise<AuthResponse> {
    // Use demo credentials
    return this.login({
      username: 'demo',
      password: 'demo123'
    });
  }
}

// Singleton instance
const authService = new AuthService();
export default authService;