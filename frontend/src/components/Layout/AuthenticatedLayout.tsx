import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link } from 'react-router-dom';
import { UserButton } from '@clerk/clerk-react';

const AuthenticatedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <>
      <AppBar position="static" sx={{ mb: 3 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Medical Scribe System
          </Typography>
          <Button color="inherit" component={Link} to="/dashboard">
            Dashboard
          </Button>
          <Button color="inherit" component={Link} to="/patient-records">
            Patient Records
          </Button>
          <Button color="inherit" component={Link} to="/clinical-notes">
            Clinical Notes
          </Button>
          <Button color="inherit" component={Link} to="/ehr">
            EHR Integration
          </Button>
          <Box sx={{ ml: 2 }}>
            <UserButton afterSignOutUrl="/login" />
          </Box>
        </Toolbar>
      </AppBar>
      {children}
    </>
  );
};

export default AuthenticatedLayout;