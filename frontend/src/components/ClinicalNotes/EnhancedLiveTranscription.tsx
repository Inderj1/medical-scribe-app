import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  LinearProgress,
  Collapse,
  IconButton,
  Tooltip,
  Badge
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import InsightsIcon from '@mui/icons-material/Insights';
import enhancedWebSocketService, { 
  TranscriptionResult, 
  ClinicalAnalysis,
  QueueStatus,
  ServerMetrics 
} from '../../services/enhancedWebsocket';

interface TranscriptionSegmentUI {
  id: string;
  jobId: string;
  text: string;
  confidence: number;
  timestamp: string;
  status: 'pending' | 'processing' | 'completed' | 'error' | 'added';
  analysis?: ClinicalAnalysis;
  segments?: Array<{
    start: number;
    end: number;
    text: string;
    confidence: number;
  }>;
  processingTime?: number;
  error?: string;
}

interface EnhancedLiveTranscriptionProps {
  encounterId: string;
  onAddToSection?: (section: string, content: string, transcriptionId?: string, entities?: any[]) => void;
  noteFormat?: 'long' | 'short' | 'bullet';
}

const EnhancedLiveTranscription: React.FC<EnhancedLiveTranscriptionProps> = ({ 
  encounterId, 
  onAddToSection,
  noteFormat = 'long'
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [transcriptionSegments, setTranscriptionSegments] = useState<TranscriptionSegmentUI[]>([]);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [serverMetrics, setServerMetrics] = useState<ServerMetrics | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const segmentRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    // Listen for transcription events
    const handleTranscriptionQueued = (data: any) => {
      const newSegment: TranscriptionSegmentUI = {
        id: data.job_id,
        jobId: data.job_id,
        text: 'Processing...',
        confidence: 0,
        timestamp: data.timestamp,
        status: 'pending'
      };
      
      setTranscriptionSegments(prev => [newSegment, ...prev]);
      setQueueStatus(data.queue_status);
      setIsProcessing(true);
    };

    const handleTranscriptionResult = (result: TranscriptionResult) => {
      setTranscriptionSegments(prev => 
        prev.map(seg => 
          seg.jobId === result.job_id 
            ? {
                ...seg,
                text: result.text,
                confidence: result.confidence,
                segments: result.segments,
                processingTime: result.processing_time,
                status: 'processing',
                timestamp: result.timestamp
              }
            : seg
        )
      );
    };

    const handleClinicalAnalysis = (analysis: ClinicalAnalysis) => {
      setTranscriptionSegments(prev => 
        prev.map(seg => 
          seg.jobId === analysis.job_id 
            ? {
                ...seg,
                analysis,
                status: 'completed'
              }
            : seg
        )
      );
      setIsProcessing(false);
    };

    const handleTranscriptionError = (data: any) => {
      setTranscriptionSegments(prev => 
        prev.map(seg => 
          seg.jobId === data.job_id 
            ? {
                ...seg,
                status: 'error',
                error: data.error
              }
            : seg
        )
      );
      setIsProcessing(false);
    };

    const handleMetricsUpdate = (metrics: ServerMetrics) => {
      setServerMetrics(metrics);
      setQueueStatus(metrics.queue_status);
    };

    const handleAutoUpdate = (data: any) => {
      // Mark segment as auto-added if it matches
      if (data.source === 'ai_suggestion' && data.confidence > 0.8) {
        // Find the segment that was auto-added based on content
        setTranscriptionSegments(prev => 
          prev.map(seg => {
            if (seg.text && data.content.text.includes(seg.text)) {
              return { ...seg, status: 'added' };
            }
            return seg;
          })
        );
      }
    };

    // Subscribe to events
    enhancedWebSocketService.on('transcription:queued', handleTranscriptionQueued);
    enhancedWebSocketService.on('transcription:result', handleTranscriptionResult);
    enhancedWebSocketService.on('clinical:analysis', handleClinicalAnalysis);
    enhancedWebSocketService.on('transcription:error', handleTranscriptionError);
    enhancedWebSocketService.on('metrics:update', handleMetricsUpdate);
    enhancedWebSocketService.on('notes:auto_update', handleAutoUpdate);

    // Request initial status
    enhancedWebSocketService.getStatus();

    return () => {
      enhancedWebSocketService.off('transcription:queued', handleTranscriptionQueued);
      enhancedWebSocketService.off('transcription:result', handleTranscriptionResult);
      enhancedWebSocketService.off('clinical:analysis', handleClinicalAnalysis);
      enhancedWebSocketService.off('transcription:error', handleTranscriptionError);
      enhancedWebSocketService.off('metrics:update', handleMetricsUpdate);
      enhancedWebSocketService.off('notes:auto_update', handleAutoUpdate);
    };
  }, []);

  const handleAddToSection = (segment: TranscriptionSegmentUI, section: string) => {
    if (onAddToSection && segment.analysis) {
      // Extract relevant entities for the section
      const relevantEntities = getRelevantEntities(segment.analysis, section);
      onAddToSection(section, segment.text, segment.id, relevantEntities);
      
      // Update segment status
      setTranscriptionSegments(prev => 
        prev.map(seg => 
          seg.id === segment.id ? { ...seg, status: 'added' } : seg
        )
      );
    }
  };

  const getRelevantEntities = (analysis: ClinicalAnalysis, section: string): any[] => {
    const entities = [];
    
    switch (section) {
      case 'chief_complaint':
      case 'present_illness':
        entities.push(...analysis.entities.symptoms);
        entities.push(...analysis.entities.conditions);
        break;
      case 'medications':
        entities.push(...analysis.entities.medications);
        break;
      case 'physical_exam':
        entities.push(...analysis.entities.vitals);
        entities.push(...analysis.entities.measurements);
        break;
      case 'assessment_plan':
        entities.push(...analysis.entities.procedures);
        break;
    }
    
    return entities;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <AccessTimeIcon fontSize="small" />;
      case 'processing':
        return <CircularProgress size={16} />;
      case 'completed':
        return <CheckCircleIcon fontSize="small" color="success" />;
      case 'error':
        return <ErrorIcon fontSize="small" color="error" />;
      case 'added':
        return <CheckCircleIcon fontSize="small" color="primary" />;
      default:
        return null;
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'error';
      case 'urgent':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getSignificanceIcon = (significance: string) => {
    switch (significance) {
      case 'high':
        return <WarningIcon fontSize="small" color="error" />;
      case 'medium':
        return <WarningIcon fontSize="small" color="warning" />;
      default:
        return null;
    }
  };

  return (
    <Paper
      elevation={2}
      sx={{
        bgcolor: 'white',
        borderRadius: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <Box
        sx={{
          bgcolor: '#f8f9fa',
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <MicIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Enhanced Live Transcription
          </Typography>
          {isProcessing && <CircularProgress size={16} />}
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {queueStatus && (
            <Tooltip title="Queue Status">
              <Badge badgeContent={queueStatus.queue_size} color="primary">
                <Chip
                  size="small"
                  label={`Processing: ${queueStatus.processing_jobs}`}
                  variant="outlined"
                />
              </Badge>
            </Tooltip>
          )}
          
          <IconButton
            size="small"
            onClick={() => setIsExpanded(!isExpanded)}
            sx={{ ml: 1 }}
          >
            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={isExpanded}>
        <Box sx={{ flex: 1, overflow: 'auto', maxHeight: '60vh' }} ref={containerRef}>
          {/* Server Metrics Banner */}
          {serverMetrics && (
            <Box sx={{ p: 1, bgcolor: '#e3f2fd', borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Success Rate: {Math.round((serverMetrics.successful_transcriptions / Math.max(1, serverMetrics.total_transcriptions)) * 100)}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Avg Time: {serverMetrics.average_processing_time.toFixed(2)}s
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Active Users: {serverMetrics.client_stats.total_users}
                </Typography>
              </Box>
            </Box>
          )}

          {/* Transcription Segments */}
          <Box sx={{ p: 2 }}>
            {transcriptionSegments.length === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                Speak clearly into your microphone. AI-powered transcription will process your speech in real-time.
              </Alert>
            ) : (
              transcriptionSegments.map((segment) => (
                <Box
                  key={segment.id}
                  ref={(el: HTMLDivElement | null) => segmentRefs.current[segment.id] = el}
                  sx={{
                    mb: 2,
                    p: 2,
                    bgcolor: segment.status === 'added' ? '#f0f7ff' : '#f5f5f5',
                    borderRadius: 1,
                    border: 1,
                    borderColor: segment.status === 'added' ? 'primary.light' : 'divider',
                    transition: 'all 0.3s ease'
                  }}
                >
                  {/* Segment Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getStatusIcon(segment.status)}
                      <Typography variant="caption" color="text.secondary">
                        {new Date(segment.timestamp).toLocaleTimeString()}
                      </Typography>
                      {segment.confidence > 0 && (
                        <Chip
                          size="small"
                          label={`${Math.round(segment.confidence * 100)}%`}
                          color={segment.confidence > 0.8 ? 'success' : segment.confidence > 0.6 ? 'warning' : 'error'}
                          variant="outlined"
                        />
                      )}
                      {segment.processingTime && (
                        <Typography variant="caption" color="text.secondary">
                          {segment.processingTime.toFixed(2)}s
                        </Typography>
                      )}
                    </Box>
                    
                    {segment.analysis?.contextual_info && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {getSignificanceIcon(segment.analysis.contextual_info.clinical_significance)}
                        <Chip
                          size="small"
                          label={segment.analysis.contextual_info.urgency}
                          color={getUrgencyColor(segment.analysis.contextual_info.urgency) as any}
                          variant="outlined"
                        />
                      </Box>
                    )}
                  </Box>

                  {/* Transcription Text */}
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {segment.text}
                  </Typography>

                  {/* Clinical Analysis */}
                  {segment.analysis && (
                    <>
                      <Divider sx={{ my: 1 }} />
                      
                      {/* Key Insights */}
                      {segment.analysis.contextual_info.key_insights.length > 0 && (
                        <Box sx={{ mb: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                            <InsightsIcon fontSize="small" color="primary" />
                            <Typography variant="caption" fontWeight={600}>
                              Key Insights
                            </Typography>
                          </Box>
                          {segment.analysis.contextual_info.key_insights.map((insight, idx) => (
                            <Typography key={idx} variant="caption" display="block" sx={{ ml: 3 }}>
                              • {insight}
                            </Typography>
                          ))}
                        </Box>
                      )}

                      {/* Extracted Entities */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                        {Object.entries(segment.analysis.entities).map(([type, entities]) => 
                          entities.map((entity: any, idx: number) => (
                            <Chip
                              key={`${type}-${idx}`}
                              size="small"
                              label={`${type}: ${entity.text || entity.name || entity.type}`}
                              variant="outlined"
                              color="primary"
                            />
                          ))
                        )}
                      </Box>

                      {/* Suggested Actions */}
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<AddIcon />}
                          onClick={() => handleAddToSection(segment, segment.analysis!.suggested_section.primary_section)}
                          disabled={segment.status === 'added'}
                        >
                          Add to {segment.analysis.suggested_section.primary_section.replace('_', ' ')}
                        </Button>
                        
                        {segment.analysis.suggested_section.alternative_sections.map((section) => (
                          <Button
                            key={section}
                            size="small"
                            variant="outlined"
                            onClick={() => handleAddToSection(segment, section)}
                            disabled={segment.status === 'added'}
                          >
                            {section.replace('_', ' ')}
                          </Button>
                        ))}
                      </Box>

                      {/* Missing Information */}
                      {segment.analysis.contextual_info.missing_information.length > 0 && (
                        <Alert severity="info" sx={{ mt: 1 }}>
                          <Typography variant="caption">
                            Consider asking about: {segment.analysis.contextual_info.missing_information.join(', ')}
                          </Typography>
                        </Alert>
                      )}
                    </>
                  )}

                  {/* Error Display */}
                  {segment.error && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      {segment.error}
                    </Alert>
                  )}
                </Box>
              ))
            )}
          </Box>
        </Box>
      </Collapse>
    </Paper>
  );
};

export default EnhancedLiveTranscription;