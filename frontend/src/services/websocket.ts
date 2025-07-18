import { io, Socket } from 'socket.io-client';

export interface AudioChunk {
  audio_chunk: string;
  timestamp: number;
}

export interface TranscriptionUpdate {
  type: 'transcription:partial' | 'transcription:final';
  text: string;
  confidence: number;
  timestamp: string;
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
    blood_pressure_systolic?: number;
    blood_pressure_diastolic?: number;
    heart_rate?: number;
    respiratory_rate?: number;
    temperature?: number;
    oxygen_saturation?: number;
    pain_level?: number;
  };
  timestamp: string;
}

export interface ConnectionStatus {
  type: 'connection:status';
  status: 'connected' | 'disconnected' | 'error';
  user_id?: string;
  timestamp: string;
}

type WebSocketMessage = TranscriptionUpdate | ClinicalNotesUpdate | VitalsUpdate | ConnectionStatus;

class WebSocketService {
  private socket: Socket | null = null;
  private audioBuffer: AudioChunk[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners: Map<string, Set<Function>> = new Map();
  
  constructor() {
    this.connect = this.connect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.sendAudioChunk = this.sendAudioChunk.bind(this);
  }
  
  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
      
      this.socket = io(wsUrl, {
        path: '/ws/audio-stream',
        transports: ['websocket'],
        auth: {
          token
        },
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
      });
      
      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.emitLocal('connection:status', {
          type: 'connection:status',
          status: 'connected',
          timestamp: new Date().toISOString()
        });
        resolve();
      });
      
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        this.emitLocal('connection:status', {
          type: 'connection:status',
          status: 'disconnected',
          timestamp: new Date().toISOString()
        });
      });
      
      this.socket.on('error', (error) => {
        console.error('WebSocket error:', error);
        this.emitLocal('connection:status', {
          type: 'connection:status',
          status: 'error',
          timestamp: new Date().toISOString()
        });
        reject(error);
      });
      
      // Handle incoming messages
      this.socket.on('message', (data: WebSocketMessage) => {
        this.handleMessage(data);
      });
      
      // Specific event handlers
      this.socket.on('transcription:partial', (data: TranscriptionUpdate) => {
        this.emitLocal('transcription:partial', data);
      });
      
      this.socket.on('transcription:final', (data: TranscriptionUpdate) => {
        this.emitLocal('transcription:final', data);
      });
      
      this.socket.on('notes:update', (data: ClinicalNotesUpdate) => {
        this.emitLocal('notes:update', data);
      });
      
      this.socket.on('vitals:update', (data: VitalsUpdate) => {
        this.emitLocal('vitals:update', data);
      });
    });
  }
  
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.audioBuffer = [];
    this.listeners.clear();
  }
  
  startEncounter(encounterId: string, patientId: string): void {
    if (!this.socket) {
      throw new Error('WebSocket not connected');
    }
    
    this.socket.emit('message', {
      type: 'encounter:start',
      encounter_id: encounterId,
      patient_id: patientId
    });
  }
  
  endEncounter(): void {
    if (!this.socket) {
      throw new Error('WebSocket not connected');
    }
    
    // Send any remaining audio
    this.flushAudioBuffer();
    
    this.socket.emit('message', {
      type: 'encounter:end'
    });
  }
  
  sendAudioChunk(audioData: ArrayBuffer): void {
    if (!this.socket) {
      throw new Error('WebSocket not connected');
    }
    
    // Convert ArrayBuffer to base64
    const uint8Array = new Uint8Array(audioData);
    const base64 = btoa(String.fromCharCode.apply(null, Array.from(uint8Array)));
    
    const chunk: AudioChunk = {
      audio_chunk: base64,
      timestamp: Date.now()
    };
    
    this.audioBuffer.push(chunk);
    
    // Send chunks in batches
    if (this.audioBuffer.length >= 10 || Date.now() - this.audioBuffer[0].timestamp > 1000) {
      this.flushAudioBuffer();
    }
  }
  
  private flushAudioBuffer(): void {
    if (this.audioBuffer.length === 0 || !this.socket) return;
    
    this.audioBuffer.forEach(chunk => {
      this.socket!.emit('message', {
        type: 'audio:stream',
        audio_chunk: chunk.audio_chunk
      });
    });
    
    this.audioBuffer = [];
  }
  
  updateVitals(vitals: VitalsUpdate['vitals']): void {
    if (!this.socket) {
      throw new Error('WebSocket not connected');
    }
    
    this.socket.emit('message', {
      type: 'vitals:update',
      vitals
    });
  }
  
  sendPing(): void {
    if (!this.socket) return;
    
    this.socket.emit('message', {
      type: 'ping'
    });
  }
  
  private handleMessage(data: WebSocketMessage): void {
    this.emitLocal(data.type, data);
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
        callback(data);
      });
    }
  }
  
  isConnected(): boolean {
    return this.socket?.connected || false;
  }
  
  emit(event: string, data: any): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn(`Cannot emit ${event}: WebSocket not connected`);
    }
  }
}

// Singleton instance
const webSocketService = new WebSocketService();
export default webSocketService;