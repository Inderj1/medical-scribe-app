/**
 * Real-time Audio Streamer for continuous audio streaming
 * Replaces chunk-based recording with continuous PCM stream
 */

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
}

export interface StreamerOptions {
  sampleRate?: number;
  channels?: number;
  bufferSize?: number;
  onAudioData?: (data: ArrayBuffer) => void;
  onError?: (error: Error) => void;
}

export class RealtimeAudioStreamer {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private isStreaming: boolean = false;
  
  private options: Required<StreamerOptions>;
  
  constructor(options: StreamerOptions = {}) {
    this.options = {
      sampleRate: 24000, // 24kHz for OpenAI Realtime API
      channels: 1, // Mono
      bufferSize: 2048, // Small buffer for low latency
      onAudioData: () => {},
      onError: () => {},
      ...options
    };
  }
  
  async startStreaming(): Promise<void> {
    if (this.isStreaming) {
      console.warn('Audio streaming already active');
      return;
    }
    
    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.options.sampleRate,
          channelCount: this.options.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      // Create audio context with specific sample rate
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.options.sampleRate
      });
      
      // Create audio source from media stream
      this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
      
      // Create script processor for real-time processing
      this.processor = this.audioContext.createScriptProcessor(
        this.options.bufferSize,
        this.options.channels,
        this.options.channels
      );
      
      // Process audio data
      this.processor.onaudioprocess = (event) => {
        if (!this.isStreaming) return;
        
        // Get PCM data from input buffer
        const inputData = event.inputBuffer.getChannelData(0);
        
        // Convert Float32Array to Int16Array (PCM16)
        const pcm16Data = this.float32ToInt16(inputData);
        
        // Send data through callback
        this.options.onAudioData(pcm16Data.buffer);
      };
      
      // Connect nodes
      this.source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      
      this.isStreaming = true;
      console.log('Real-time audio streaming started');
      
    } catch (error) {
      console.error('Failed to start audio streaming:', error);
      this.options.onError(error as Error);
      throw error;
    }
  }
  
  stopStreaming(): void {
    if (!this.isStreaming) return;
    
    this.isStreaming = false;
    
    // Disconnect audio nodes
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    
    // Close audio context
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    // Stop media stream tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    
    console.log('Real-time audio streaming stopped');
  }
  
  private float32ToInt16(float32Array: Float32Array): Int16Array {
    const int16Array = new Int16Array(float32Array.length);
    
    for (let i = 0; i < float32Array.length; i++) {
      // Convert float32 (-1 to 1) to int16 (-32768 to 32767)
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    
    return int16Array;
  }
  
  getAudioConfig(): AudioConfig {
    return {
      sampleRate: this.options.sampleRate,
      channels: this.options.channels,
      bitDepth: 16 // PCM16
    };
  }
  
  isActive(): boolean {
    return this.isStreaming;
  }
}