export interface AudioChunk {
  audio_chunk: string;
  timestamp: number;
}

export interface TranscriptionUpdate {
  type: 'transcription:partial' | 'transcription:final';
  text: string;
  confidence: number;
  timestamp: string;
  suggestedSection?: string;
}

export interface ClinicalNotesUpdate {
  type: 'notes:update';
  section: string;
  content: any;
  entities: any[];
}

export interface VitalsUpdate {
  type: 'vitals:update';
  vitals: {
    blood_pressure?: string;
    heart_rate?: number;
    respiratory_rate?: number;
    temperature?: number;
    oxygen_saturation?: number;
    pain_level?: string;
  };
  timestamp: string;
}

export interface ConnectionStatus {
  type: 'connection:status';
  status: 'connected' | 'disconnected' | 'error';
  user_id?: string;
  timestamp: string;
}

export interface EncounterStatus {
  type: 'encounter:started' | 'encounter:ended';
  encounter_id: string;
  status?: string;
}

type WebSocketMessage = TranscriptionUpdate | ClinicalNotesUpdate | VitalsUpdate | ConnectionStatus | EncounterStatus;

// Generic message type for runtime handling
interface GenericMessage {
  type: string;
  [key: string]: any;
}

class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<Function>> = new Map();
  private messageQueue: any[] = [];
  private isConnecting = false;
  private token: string | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  
  constructor() {
    this.connect = this.connect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.sendAudioChunk = this.sendAudioChunk.bind(this);
  }
  
  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected');
        resolve();
        return;
      }

      if (this.isConnecting) {
        console.log('WebSocket connection already in progress, waiting...');
        // Wait for the existing connection attempt to complete
        const checkInterval = setInterval(() => {
          if (!this.isConnecting) {
            clearInterval(checkInterval);
            if (this.socket?.readyState === WebSocket.OPEN) {
              resolve();
            } else {
              reject(new Error('Connection failed'));
            }
          }
        }, 100);
        
        // Timeout after 10 seconds
        setTimeout(() => {
          clearInterval(checkInterval);
          if (this.socket?.readyState === WebSocket.OPEN) {
            resolve();
          } else {
            reject(new Error('Connection timeout'));
          }
        }, 10000);
        return;
      }

      this.isConnecting = true;
      this.token = token;
      
      const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
      // Use enhanced agentic AI endpoint
      const url = `${wsUrl}/api/v1/ws/enhanced-audio-stream?token=${encodeURIComponent(token)}`;
      
      try {
        this.socket = new WebSocket(url);
        
        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          
          // Send any queued messages
          while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.sendMessage(message);
          }
          
          // Start heartbeat
          this.startHeartbeat();
          
          this.emitLocal('connection:status', {
            type: 'connection:status',
            status: 'connected',
            timestamp: new Date().toISOString()
          });
          
          resolve();
        };
        
        this.socket.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.isConnecting = false;
          this.stopHeartbeat();
          
          this.emitLocal('connection:status', {
            type: 'connection:status',
            status: 'disconnected',
            timestamp: new Date().toISOString()
          });
          
          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
        
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnecting = false;
          
          this.emitLocal('connection:status', {
            type: 'connection:status',
            status: 'error',
            timestamp: new Date().toISOString()
          });
          
          reject(error);
        };
        
        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }
  
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (this.token) {
        this.connect(this.token).catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }
  
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }
  
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
  
  disconnect(): void {
    this.stopHeartbeat();
    this.isConnecting = false;
    
    if (this.socket) {
      this.socket.close(1000, 'Normal closure');
      this.socket = null;
    }
    
    this.messageQueue = [];
    this.listeners.clear();
    this.token = null;
    this.reconnectAttempts = 0;
  }
  
  resetConnection(): void {
    console.log('Resetting WebSocket connection');
    this.isConnecting = false;
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      this.socket.close();
    }
    this.socket = null;
    this.stopHeartbeat();
  }
  
  private sendMessage(message: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      // Queue message if not connected
      this.messageQueue.push(message);
    }
  }
  
  startEncounter(encounterId: string, patientId: string): void {
    this.sendMessage({
      type: 'encounter:start',
      encounter_id: encounterId,
      patient_id: patientId
    });
  }
  
  endEncounter(patientId?: string): void {
    this.sendMessage({
      type: 'encounter:end',
      patient_id: patientId
    });
  }
  
  sendAudioChunk(audioData: ArrayBuffer): void {
    // Convert ArrayBuffer to base64 - handle large chunks
    const uint8Array = new Uint8Array(audioData);
    let binary = '';
    const chunkSize = 0x8000; // 32KB chunks to avoid call stack issues
    
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
      const chunk = uint8Array.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, Array.from(chunk));
    }
    
    const base64 = btoa(binary);
    
    this.sendMessage({
      type: 'audio:stream',
      audio_chunk: base64
    });
  }
  
  updateVitals(vitals: VitalsUpdate['vitals']): void {
    this.sendMessage({
      type: 'vitals:update',
      vitals
    });
  }
  
  // Generic emit method for sending any message type
  emit(type: string, data: any): void {
    this.sendMessage({
      type,
      ...data
    });
  }
  
  private handleMessage(data: WebSocketMessage): void {
    // Handle specific message types
    switch (data.type) {
      case 'connection:status':
        this.emitLocal('connection:status', data);
        break;
        
      case 'transcription:partial':
        this.emitLocal('transcription:partial', data);
        break;
        
      case 'transcription:final':
        this.emitLocal('transcription:final', data);
        break;
        
      case 'notes:update':
        this.emitLocal('notes:update', data);
        break;
        
      case 'vitals:update':
        this.emitLocal('vitals:update', data);
        break;
        
      case 'encounter:started':
      case 'encounter:ended':
        this.emitLocal(data.type, data);
        break;
        
      default:
        // Handle any other message types
        if ('type' in data) {
          this.emitLocal((data as GenericMessage).type, data);
        }
    }
  }
  
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }
  
  off(event: string, callback: Function): void {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.delete(callback);
    }
  }
  
  private emitLocal(event: string, data: any): void {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }
  
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
  
  getConnectionState(): string {
    if (!this.socket) return 'CLOSED';
    
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }
}

// Singleton instance
const webSocketService = new WebSocketService();
export default webSocketService;