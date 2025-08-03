/**
 * API client for streaming endpoints
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const streamingAPI = {
  /**
   * Start a new streaming session
   */
  async startSession(sessionData: any, token: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/streaming/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(sessionData)
    });
    
    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }
    
    return response.json();
  },

  /**
   * Send text chunk to session
   */
  async sendTextChunk(sessionId: string, textData: any, token: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/streaming/${sessionId}/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(textData)
    });
    
    if (!response.ok) {
      throw new Error(`Failed to send text chunk: ${response.statusText}`);
    }
    
    return response.json();
  },

  /**
   * Send audio chunk to session
   */
  async sendAudioChunk(sessionId: string, audioFile: Blob, chunkNumber: number, token: string) {
    const formData = new FormData();
    formData.append('audio_file', audioFile, 'audio.webm');
    formData.append('chunk_number', chunkNumber.toString());
    
    const response = await fetch(`${API_BASE_URL}/api/v1/streaming/${sessionId}/audio`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Failed to send audio chunk: ${response.statusText}`);
    }
    
    return response.json();
  },

  /**
   * End streaming session
   */
  async endSession(sessionId: string, token: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/streaming/${sessionId}/end`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to end session: ${response.statusText}`);
    }
    
    return response.json();
  },

  /**
   * Get session status
   */
  async getSessionStatus(sessionId: string, token: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/streaming/${sessionId}/status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get session status: ${response.statusText}`);
    }
    
    return response.json();
  }
};