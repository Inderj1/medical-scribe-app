import React, { useEffect, useState } from 'react';
import { Box, Typography, Paper, Grid, Chip } from '@mui/material';

interface SystemStatus {
  frontend: boolean;
  backend: boolean;
  database: boolean;
  redis: boolean;
}

function HomePage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    frontend: true,
    backend: false,
    database: false,
    redis: false
  });

  useEffect(() => {
    // Check backend health
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(data => {
        setSystemStatus({
          frontend: true,
          backend: data.status === 'healthy',
          database: data.database === 'connected',
          redis: data.redis === 'connected'
        });
      })
      .catch(() => {
        setSystemStatus(prev => ({ ...prev, backend: false }));
      });
  }, []);

  const getStatusColor = (status: boolean) => status ? 'success' : 'error';

  return (
    <Box>
      <Paper elevation={3} sx={{ p: 4, mb: 3 }}>
        <Typography variant="h3" gutterBottom align="center">
          Welcome to Medical Scribe System
        </Typography>
        <Typography variant="h6" color="text.secondary" align="center">
          A comprehensive medical documentation platform
        </Typography>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              System Status
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography>Frontend</Typography>
                <Chip 
                  label={systemStatus.frontend ? 'Running' : 'Down'} 
                  color={getStatusColor(systemStatus.frontend)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography>Backend API</Typography>
                <Chip 
                  label={systemStatus.backend ? 'Running' : 'Down'} 
                  color={getStatusColor(systemStatus.backend)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography>Database</Typography>
                <Chip 
                  label={systemStatus.database ? 'Connected' : 'Disconnected'} 
                  color={getStatusColor(systemStatus.database)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography>Redis Cache</Typography>
                <Chip 
                  label={systemStatus.redis ? 'Connected' : 'Disconnected'} 
                  color={getStatusColor(systemStatus.redis)}
                  size="small"
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Quick Links
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography>
                <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
                  API Documentation
                </a>
              </Typography>
              <Typography>
                <a href="http://localhost:8000/health" target="_blank" rel="noopener noreferrer">
                  Health Check Endpoint
                </a>
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default HomePage;