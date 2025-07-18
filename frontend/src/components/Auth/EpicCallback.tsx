import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import axios from 'axios';

const EpicCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('Processing Epic authentication...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get authorization code and state from URL
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        // Check for errors from Epic
        if (error) {
          throw new Error(errorDescription || `Epic authorization error: ${error}`);
        }

        if (!code) {
          throw new Error('No authorization code received from Epic');
        }

        // Verify state to prevent CSRF attacks
        const savedState = sessionStorage.getItem('epic_auth_state');
        if (state !== savedState) {
          throw new Error('Invalid state parameter - possible CSRF attack');
        }

        setStatus('Exchanging authorization code for access token...');

        // Exchange code for token
        const tokenResponse = await axios.post('/api/auth/epic/token', {
          code,
          state,
          redirect_uri: process.env.REACT_APP_EPIC_REDIRECT_URI
        });

        const { access_token, patient, encounter, refresh_token } = tokenResponse.data;

        // Store tokens securely
        localStorage.setItem('epic_access_token', access_token);
        if (refresh_token) {
          localStorage.setItem('epic_refresh_token', refresh_token);
        }

        // Store context
        if (patient) {
          sessionStorage.setItem('epic_patient_id', patient);
        }
        if (encounter) {
          sessionStorage.setItem('epic_encounter_id', encounter);
        }

        setStatus('Fetching patient information...');

        // If we have a patient context, sync the patient data
        if (patient) {
          const syncResponse = await axios.post('/api/ehr/sync/patient', {
            organization_id: 'epic',
            ehr_patient_id: patient,
            sync_historical: true
          });

          if (syncResponse.data.success) {
            // Navigate to encounter page with synced patient
            navigate(`/encounter/new?patient=${syncResponse.data.patient_id}`);
          } else {
            navigate('/dashboard');
          }
        } else {
          // No patient context, go to dashboard
          navigate('/dashboard');
        }

      } catch (error) {
        console.error('Epic callback error:', error);
        setError(error instanceof Error ? error.message : 'An error occurred during Epic authentication');
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: 3,
      }}
    >
      {error ? (
        <Alert severity="error" sx={{ maxWidth: 500 }}>
          <Typography variant="h6">Authentication Failed</Typography>
          <Typography>{error}</Typography>
          <Typography variant="body2" sx={{ mt: 2 }}>
            Please close this window and try again from Epic.
          </Typography>
        </Alert>
      ) : (
        <>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 3 }}>
            Connecting to Epic
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {status}
          </Typography>
        </>
      )}
    </Box>
  );
};

export default EpicCallback;