import webSocketService from './websocket';

export interface AudioRecorderOptions {
  onDataAvailable?: (data: Blob) => void;
  onError?: (error: Error) => void;
  onStop?: () => void;
  sampleRate?: number;
  channelCount?: number;
}

class AudioRecorderService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private isRecording: boolean = false;
  private options: AudioRecorderOptions = {};
  private chunks: Blob[] = [];
  private recordingStartTime: number = 0;
  private chunkInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.start = this.start.bind(this);
    this.stop = this.stop.bind(this);
    this.pause = this.pause.bind(this);
    this.resume = this.resume.bind(this);
  }

  async start(options: AudioRecorderOptions = {}): Promise<void> {
    this.options = options;
    
    try {
      // Request microphone access
      const constraints: MediaStreamConstraints = {
        audio: {
          channelCount: options.channelCount || 1,
          sampleRate: options.sampleRate || 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      };

      this.audioStream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // Create audio context for analysis
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      source.connect(this.analyser);

      // Setup MediaRecorder
      const mimeType = this.getSupportedMimeType();
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType,
        audioBitsPerSecond: 128000
      });

      this.mediaRecorder.ondataavailable = this.handleDataAvailable.bind(this);
      this.mediaRecorder.onerror = (event: Event) => {
        this.handleError(new Error('MediaRecorder error'));
      };
      this.mediaRecorder.onstop = this.handleStop.bind(this);

      // Start recording with timeslice for streaming
      this.isRecording = true;
      this.recordingStartTime = Date.now();
      this.chunks = [];
      
      // Start recording with 1-second chunks for streaming
      this.mediaRecorder.start(1000);

      // Send audio chunks every second
      this.chunkInterval = setInterval(() => {
        if (this.chunks.length > 0) {
          this.sendAudioChunks();
        }
      }, 1000);

      console.log('Audio recording started');
    } catch (error) {
      console.error('Error starting audio recording:', error);
      this.handleError(error as Error);
      throw error;
    }
  }

  private getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/wav',
      'audio/mp4'
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        console.log(`Using mime type: ${type}`);
        return type;
      }
    }

    return 'audio/webm'; // Fallback
  }

  private async handleDataAvailable(event: BlobEvent): Promise<void> {
    if (event.data && event.data.size > 0) {
      this.chunks.push(event.data);
      
      // Optional: Call the onDataAvailable callback
      if (this.options.onDataAvailable) {
        this.options.onDataAvailable(event.data);
      }
    }
  }

  private async sendAudioChunks(): Promise<void> {
    if (this.chunks.length === 0 || !webSocketService.isConnected()) {
      return;
    }

    try {
      // Combine all chunks into a single blob
      const audioBlob = new Blob(this.chunks, { type: this.mediaRecorder?.mimeType || 'audio/webm' });
      this.chunks = []; // Clear chunks after combining

      // Convert blob to ArrayBuffer
      const arrayBuffer = await audioBlob.arrayBuffer();
      
      // Send to WebSocket
      webSocketService.sendAudioChunk(arrayBuffer);
      
      console.log(`Sent audio chunk: ${arrayBuffer.byteLength} bytes`);
    } catch (error) {
      console.error('Error sending audio chunk:', error);
    }
  }

  private handleError(error: Error): void {
    console.error('MediaRecorder error:', error);
    this.isRecording = false;
    
    if (this.options.onError) {
      this.options.onError(error);
    }
  }

  private handleStop(): void {
    console.log('MediaRecorder stopped');
    this.isRecording = false;
    
    // Send any remaining chunks
    if (this.chunks.length > 0) {
      this.sendAudioChunks();
    }
    
    if (this.options.onStop) {
      this.options.onStop();
    }
  }

  stop(): void {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      
      // Stop all audio tracks
      if (this.audioStream) {
        this.audioStream.getTracks().forEach(track => track.stop());
        this.audioStream = null;
      }

      // Clean up audio context
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
        this.analyser = null;
      }

      // Clear chunk interval
      if (this.chunkInterval) {
        clearInterval(this.chunkInterval);
        this.chunkInterval = null;
      }

      this.isRecording = false;
      console.log('Audio recording stopped');
    }
  }

  pause(): void {
    if (this.mediaRecorder && this.isRecording && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause();
      console.log('Audio recording paused');
    }
  }

  resume(): void {
    if (this.mediaRecorder && this.isRecording && this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume();
      console.log('Audio recording resumed');
    }
  }

  getRecordingState(): string {
    if (!this.mediaRecorder) return 'inactive';
    return this.mediaRecorder.state;
  }

  isCurrentlyRecording(): boolean {
    return this.isRecording && this.mediaRecorder?.state === 'recording';
  }

  getRecordingDuration(): number {
    if (!this.isRecording) return 0;
    return Date.now() - this.recordingStartTime;
  }

  // Get audio level for visualization
  getAudioLevel(): number {
    if (!this.analyser || !this.isRecording) return 0;

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
    return average / 255; // Normalize to 0-1
  }
}

// Singleton instance
const audioRecorderService = new AudioRecorderService();
export default audioRecorderService;