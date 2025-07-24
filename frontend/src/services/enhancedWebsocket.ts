import { EventEmitter } from 'events';

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
  confidence: number;
}

export interface TranscriptionResult {
  job_id: string;
  text: string;
  confidence: number;
  segments: TranscriptionSegment[];
  processing_time: number;
  timestamp: string;
}

export interface ClinicalEntity {
  text: string;
  formatted_text?: string;
  severity?: string;
  duration?: string;
  dosage?: string;
  frequency?: string;
  type?: string;
  value?: string;
  unit?: string;
  name?: string;
  status?: string;
  segment_start?: number;
  segment_end?: number;
  segment_confidence?: number;
}

export interface ClinicalAnalysis {
  job_id: string;
  entities: {
    symptoms: ClinicalEntity[];
    medications: ClinicalEntity[];
    vitals: ClinicalEntity[];
    procedures: ClinicalEntity[];
    conditions: ClinicalEntity[];
    measurements: ClinicalEntity[];
  };
  suggested_section: {
    primary_section: string;
    confidence: number;
    reasoning: string;
    alternative_sections: string[];
  };
  confidence: number;
  contextual_info: {
    clinical_significance: 'low' | 'medium' | 'high';
    urgency: 'routine' | 'urgent' | 'critical';
    relationships: string[];
    key_insights: string[];
    missing_information: string[];
    follow_up_questions: string[];
  };
  timestamp: string;
}

export interface QueueStatus {
  queue_size: number;
  processing_jobs: number;
  failed_jobs: number;
  processing_job_ids: string[];
  failed_job_ids: string[];
}

export interface ServerMetrics {
  total_transcriptions: number;
  successful_transcriptions: number;
  failed_transcriptions: number;
  average_processing_time: number;
  active_connections: number;
  uptime: number;
  queue_status: QueueStatus;
  client_stats: {
    total_users: number;
    total_connections: number;
    active_encounters: number;
    total_context_items: number;
    total_jobs_tracked: number;
  };
}

export interface ClientInfo {
  user_id: string;
  connected: boolean;
  connection_count: number;
  encounter_id: string | null;
  note_format: string;
  context_size: number;
  job_count: number;
  metadata: Record<string, any>;
}

class EnhancedWebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private messageQueue: any[] = [];
  private currentEncounterId: string | null = null;
  private clientInfo: ClientInfo | null = null;

  constructor() {
    super();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_API_URL || window.location.host;
    this.url = `${protocol}//${host}/api/v1/ws/enhanced-audio-stream`;
  }

  async connect(token: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(`${this.url}?token=${encodeURIComponent(token)}`);

        this.ws.onopen = () => {
          console.log('Enhanced WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPingInterval();
          this.flushMessageQueue();
          this.emit('connected');
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.emit('error', error);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.isConnecting = false;
          this.stopPingInterval();
          this.emit('disconnected', { code: event.code, reason: event.reason });

          // Auto-reconnect logic
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
              this.reconnectAttempts++;
              this.connect(token);
            }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
          }
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  private handleMessage(data: any): void {
    const messageType = data.type;

    switch (messageType) {
      case 'connection_established':
        this.clientInfo = data.metadata;
        this.emit('connection:established', data);
        break;

      case 'encounter:started':
        this.currentEncounterId = data.encounter_id;
        this.emit('encounter:started', data);
        break;

      case 'encounter:ended':
        this.currentEncounterId = null;
        this.emit('encounter:ended', data);
        break;

      case 'transcription:queued':
        this.emit('transcription:queued', data);
        break;

      case 'transcription:result':
        this.emit('transcription:result', data as TranscriptionResult);
        break;

      case 'transcription:error':
        this.emit('transcription:error', data);
        break;

      case 'clinical:analysis':
        this.emit('clinical:analysis', data as ClinicalAnalysis);
        break;

      case 'clinical:summary':
        this.emit('clinical:summary', data);
        break;

      case 'notes:update':
        this.emit('notes:update', data);
        break;

      case 'notes:auto_update':
        this.emit('notes:auto_update', data);
        break;

      case 'vitals:update':
        this.emit('vitals:update', data);
        break;

      case 'metrics:update':
        this.emit('metrics:update', data.metrics as ServerMetrics);
        break;

      case 'status:response':
        this.emit('status:response', data);
        break;

      case 'settings:updated':
        this.emit('settings:updated', data);
        break;

      case 'error':
        this.emit('error', data);
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.warn('Unknown message type:', messageType);
        this.emit(messageType, data);
    }
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      // Queue message for later
      this.messageQueue.push(data);
      console.warn('WebSocket not connected, message queued');
    }
  }

  // Enhanced API methods

  startEncounter(encounterId: string, patientId: string, encounterType: string = 'general', noteFormat: string = 'long'): void {
    this.send({
      type: 'encounter:start',
      encounter_id: encounterId,
      patient_id: patientId,
      encounter_type: encounterType,
      note_format: noteFormat
    });
  }

  endEncounter(patientId: string, vitals?: any): void {
    this.send({
      type: 'encounter:end',
      patient_id: patientId,
      vitals
    });
  }

  streamAudio(audioChunk: string): void {
    this.send({
      type: 'audio:stream',
      audio_chunk: audioChunk
    });
  }

  sendTranscription(audio: string, id?: string, priority: number = 1): void {
    this.send({
      type: 'transcription',
      audio,
      id: id || crypto.randomUUID(),
      priority,
      timestamp: new Date().toISOString()
    });
  }

  updateNotes(section: string, content: any, action: string = 'update'): void {
    this.send({
      type: 'notes:update',
      section,
      content: {
        text: typeof content === 'string' ? content : content.text,
        action
      }
    });
  }

  updateSettings(settings: { noteFormat?: string }): void {
    this.send({
      type: 'settings:update',
      ...settings
    });
  }

  updateVitals(vitals: any): void {
    this.send({
      type: 'vitals:update',
      vitals
    });
  }

  getStatus(): void {
    this.send({
      type: 'get:status'
    });
  }

  disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.emit('disconnected', { code: 1000, reason: 'Client disconnect' });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getCurrentEncounterId(): string | null {
    return this.currentEncounterId;
  }

  getClientInfo(): ClientInfo | null {
    return this.clientInfo;
  }

  // Helper method to format transcription with segments
  formatTranscriptionWithTimestamps(result: TranscriptionResult): string {
    if (!result.segments || result.segments.length === 0) {
      return result.text;
    }

    return result.segments
      .map(segment => `[${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}] ${segment.text}`)
      .join('\n');
  }

  private formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
}

// Create singleton instance
const enhancedWebSocketService = new EnhancedWebSocketService();

export default enhancedWebSocketService;