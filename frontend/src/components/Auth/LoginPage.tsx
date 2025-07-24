import React from 'react';
import { SignIn } from '@clerk/clerk-react';
import { Box, Container, Typography, Paper } from '@mui/material';

const LoginPage: React.FC = () => {
  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
            <img 
              src="/2.png" 
              alt="Medical Scribe Logo" 
              style={{ 
                height: '100px',
                width: 'auto',
                objectFit: 'contain'
              }} 
            />
          </Box>
          <Typography variant="body1" align="center" color="text.secondary" sx={{ mb: 3 }}>
            Sign in to access your medical scribe dashboard
          </Typography>
          
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <SignIn 
              appearance={{
                elements: {
                  rootBox: {
                    width: '100%',
                  },
                  card: {
                    boxShadow: 'none',
                    border: 'none',
                  },
                },
              }}
              redirectUrl="/dashboard"
              signUpUrl="/sign-up"
            />
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;