/**
 * Agent-based WebSocket service for real-time medical transcription
 */

import { RealtimeAudioStreamer } from './realtimeAudioStreamer';

export interface AgentWebSocketConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export interface TranscriptionEvent {
  type: 'partial' | 'complete';
  text: string;
  analysis?: any;
  timestamp: string;
}

export class AgentWebSocketService {
  private ws: WebSocket | null = null;
  private config: Required<AgentWebSocketConfig>;
  private reconnectAttempts: number = 0;
  private isConnecting: boolean = false;
  private audioStreamer: RealtimeAudioStreamer | null = null;
  
  // Event handlers
  private onConnected: (() => void) | null = null;
  private onDisconnected: (() => void) | null = null;
  private onTranscription: ((event: TranscriptionEvent) => void) | null = null;
  private onError: ((error: Error) => void) | null = null;
  
  constructor(config: AgentWebSocketConfig = {}) {
    this.config = {
      url: '/api/v2/ws/agent',
      reconnectInterval: 1000,
      maxReconnectAttempts: 5,
      ...config
    };
    
    // Initialize audio streamer
    this.audioStreamer = new RealtimeAudioStreamer({
      onAudioData: this.handleAudioData.bind(this),
      onError: this.handleAudioError.bind(this)
    });
  }
  
  async connect(token: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      console.warn('WebSocket already connected or connecting');
      return;
    }
    
    this.isConnecting = true;
    
    try {
      // Build WebSocket URL with authentication
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}${this.config.url}?token=${token}`;
      
      // Create WebSocket connection
      this.ws = new WebSocket(wsUrl);
      this.ws.binaryType = 'arraybuffer';
      
      // Set up event handlers
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      
    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }
  
  disconnect(): void {
    this.stopAudioStreaming();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.isConnecting = false;
    this.reconnectAttempts = 0;
  }
  
  async startEncounter(encounterId: string, patientId: string): Promise<void> {
    if (!this.isConnected()) {
      throw new Error('WebSocket not connected');
    }
    
    // Send encounter start message
    this.send({
      type: 'encounter:start',
      encounter_id: encounterId,
      patient_id: patientId
    });
    
    // Start audio streaming
    await this.startAudioStreaming();
  }
  
  async endEncounter(): Promise<void> {
    // Stop audio streaming first
    this.stopAudioStreaming();
    
    // Send encounter end message
    this.send({
      type: 'encounter:end'
    });
  }
  
  setFormatPreference(format: 'soap' | 'bullet' | 'narrative'): void {
    this.send({
      type: 'format:preference',
      format
    });
  }
  
  private async startAudioStreaming(): Promise<void> {
    if (!this.audioStreamer) return;
    
    try {
      await this.audioStreamer.startStreaming();
      
      // Send audio configuration to server
      const config = this.audioStreamer.getAudioConfig();
      this.send({
        type: 'audio:config',
        config
      });
      
    } catch (error) {
      console.error('Failed to start audio streaming:', error);
      throw error;
    }
  }
  
  private stopAudioStreaming(): void {
    if (this.audioStreamer?.isActive()) {
      this.audioStreamer.stopStreaming();
    }
  }
  
  private handleAudioData(audioData: ArrayBuffer): void {
    if (!this.isConnected()) return;
    
    // Send raw audio data directly through WebSocket
    this.ws!.send(audioData);
  }
  
  private handleAudioError(error: Error): void {
    console.error('Audio streaming error:', error);
    this.onError?.(error);
  }
  
  private handleOpen(): void {
    console.log('WebSocket connected');
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.onConnected?.();
  }
  
  private handleClose(event: CloseEvent): void {
    console.log('WebSocket disconnected', event);
    this.isConnecting = false;
    this.stopAudioStreaming();
    
    this.onDisconnected?.();
    
    // Attempt reconnection if not a normal closure
    if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.attemptReconnect();
    }
  }
  
  private handleError(event: Event): void {
    console.error('WebSocket error', event);
    this.onError?.(new Error('WebSocket connection error'));
  }
  
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'transcription:partial':
          this.onTranscription?.({
            type: 'partial',
            text: data.text,
            timestamp: data.timestamp
          });
          break;
          
        case 'transcription:complete':
          this.onTranscription?.({
            type: 'complete',
            text: data.text,
            analysis: data.analysis,
            timestamp: data.timestamp
          });
          break;
          
        case 'error':
          this.onError?.(new Error(data.message));
          break;
      }
      
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }
  
  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting reconnection in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (!this.isConnected() && !this.isConnecting) {
        // Need to get token again for reconnection
        // This would be handled by the component using this service
        this.onDisconnected?.();
      }
    }, delay);
  }
  
  private send(data: any): void {
    if (!this.isConnected()) {
      throw new Error('WebSocket not connected');
    }
    
    this.ws!.send(JSON.stringify(data));
  }
  
  private isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  
  // Event handler setters
  on(event: 'connected', handler: () => void): void;
  on(event: 'disconnected', handler: () => void): void;
  on(event: 'transcription', handler: (event: TranscriptionEvent) => void): void;
  on(event: 'error', handler: (error: Error) => void): void;
  on(event: string, handler: any): void {
    switch (event) {
      case 'connected':
        this.onConnected = handler;
        break;
      case 'disconnected':
        this.onDisconnected = handler;
        break;
      case 'transcription':
        this.onTranscription = handler;
        break;
      case 'error':
        this.onError = handler;
        break;
    }
  }
  
  getConnectionStatus(): 'connected' | 'connecting' | 'disconnected' {
    if (this.isConnected()) return 'connected';
    if (this.isConnecting) return 'connecting';
    return 'disconnected';
  }
}

// Export singleton instance
export const agentWebSocketService = new AgentWebSocketService();