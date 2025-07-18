import React from 'react';
import { SignUp } from '@clerk/clerk-react';
import { Box, Container, Typography, Paper } from '@mui/material';

const SignUpPage: React.FC = () => {
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
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Create Your Account
          </Typography>
          <Typography variant="body1" align="center" color="text.secondary" sx={{ mb: 3 }}>
            Join Medical Scribe System to start managing patient records
          </Typography>
          
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <SignUp 
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
              signInUrl="/login"
            />
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default SignUpPage;