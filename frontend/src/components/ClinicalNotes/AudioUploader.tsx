import React, { useState, useRef } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  LinearProgress,
  Alert,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Chip
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AudioFileIcon from '@mui/icons-material/AudioFile';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import { useAuth } from '../../hooks/useAuthWrapper';
import axios from 'axios';

interface AudioUploaderProps {
  encounterId: string;
  patientId: string;
  onUploadComplete?: (transcriptionId: string) => void;
  formatPreference?: string;
}

interface UploadStatus {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
  transcriptionId?: string;
  error?: string;
}

const AudioUploader: React.FC<AudioUploaderProps> = ({
  encounterId,
  patientId,
  onUploadComplete,
  formatPreference = 'soap'
}) => {
  const { getToken } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploads, setUploads] = useState<UploadStatus[]>([]);
  const [isPlaying, setIsPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    Array.from(files).forEach(file => {
      if (file.type.startsWith('audio/')) {
        uploadFile(file);
      } else {
        console.error('Invalid file type:', file.type);
      }
    });
  };

  const uploadFile = async (file: File) => {
    const uploadStatus: UploadStatus = {
      file,
      progress: 0,
      status: 'pending'
    };

    setUploads(prev => [...prev, uploadStatus]);
    const uploadIndex = uploads.length;

    try {
      uploadStatus.status = 'uploading';
      setUploads(prev => [...prev.slice(0, uploadIndex), uploadStatus, ...prev.slice(uploadIndex + 1)]);

      const formData = new FormData();
      formData.append('audio_file', file);
      formData.append('encounter_id', encounterId);
      formData.append('format_preference', formatPreference);
      formData.append('language', 'en');

      const token = await getToken();
      
      const response = await axios.post(
        'http://localhost:8000/api/v1/transcription/upload',
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const progress = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            
            uploadStatus.progress = progress;
            setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);
          }
        }
      );

      uploadStatus.status = 'processing';
      uploadStatus.transcriptionId = response.data.id;
      uploadStatus.progress = 100;
      setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);

      // Subscribe to SSE updates
      const eventSource = new EventSource(
        `http://localhost:8000/api/v1/sse/subscribe?channel=transcription_${response.data.id}`,
        { withCredentials: true }
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('SSE Update:', data);
        
        if (data.type === 'workflow_complete') {
          uploadStatus.status = 'complete';
          setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);
          eventSource.close();
          
          if (onUploadComplete && uploadStatus.transcriptionId) {
            onUploadComplete(uploadStatus.transcriptionId);
          }
        } else if (data.type === 'workflow_error') {
          uploadStatus.status = 'error';
          uploadStatus.error = data.data.error;
          setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);
          eventSource.close();
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        uploadStatus.status = 'error';
        uploadStatus.error = 'Connection lost';
        setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);
        eventSource.close();
      };

    } catch (error: any) {
      console.error('Upload error:', error);
      uploadStatus.status = 'error';
      uploadStatus.error = error.response?.data?.detail || error.message;
      setUploads(prev => [...prev.slice(0, uploadIndex), { ...uploadStatus }, ...prev.slice(uploadIndex + 1)]);
    }
  };

  const handlePlayPause = (file: File) => {
    if (isPlaying === file.name) {
      audioRef.current?.pause();
      setIsPlaying(null);
    } else {
      const url = URL.createObjectURL(file);
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play();
        setIsPlaying(file.name);
      }
    }
  };

  const removeUpload = (index: number) => {
    setUploads(prev => prev.filter((_, i) => i !== index));
  };

  const getStatusColor = (status: UploadStatus['status']) => {
    switch (status) {
      case 'complete': return 'success';
      case 'error': return 'error';
      case 'processing': return 'warning';
      case 'uploading': return 'info';
      default: return 'default';
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Audio File Upload
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          multiple
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          onClick={() => fileInputRef.current?.click()}
          fullWidth
        >
          Upload Audio Files
        </Button>
      </Box>

      {uploads.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <List>
            {uploads.map((upload, index) => (
              <ListItem key={index}>
                <AudioFileIcon sx={{ mr: 2, color: 'action.active' }} />
                <ListItemText
                  primary={upload.file.name}
                  secondary={
                    <Box>
                      {upload.status === 'uploading' && (
                        <LinearProgress
                          variant="determinate"
                          value={upload.progress}
                          sx={{ my: 1 }}
                        />
                      )}
                      <Chip
                        label={upload.status}
                        size="small"
                        color={getStatusColor(upload.status)}
                      />
                      {upload.error && (
                        <Typography variant="caption" color="error" display="block">
                          {upload.error}
                        </Typography>
                      )}
                      {upload.transcriptionId && (
                        <Typography variant="caption" display="block">
                          ID: {upload.transcriptionId}
                        </Typography>
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => handlePlayPause(upload.file)}
                    disabled={upload.status === 'uploading'}
                  >
                    {isPlaying === upload.file.name ? <PauseIcon /> : <PlayArrowIcon />}
                  </IconButton>
                  <IconButton
                    edge="end"
                    onClick={() => removeUpload(index)}
                    disabled={upload.status === 'uploading' || upload.status === 'processing'}
                  >
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </>
      )}

      <audio ref={audioRef} onEnded={() => setIsPlaying(null)} style={{ display: 'none' }} />

      <Alert severity="info" sx={{ mt: 2 }}>
        Supported formats: MP3, WAV, M4A, WEBM, OGG. Max file size: 100MB
      </Alert>
    </Paper>
  );
};

export default AudioUploader;