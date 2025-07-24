import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import { UserButton } from '@clerk/clerk-react';

const AuthenticatedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const navButtonStyle = (path: string) => ({
    color: isActive(path) ? '#1976d2' : '#5f6368',
    fontWeight: isActive(path) ? 600 : 500,
    fontSize: '0.95rem',
    px: 2,
    py: 1,
    borderRadius: '8px',
    transition: 'all 0.2s ease',
    borderBottom: isActive(path) ? '3px solid #1976d2' : '3px solid transparent',
    '&:hover': { 
      bgcolor: 'rgba(25, 118, 210, 0.08)',
      color: '#1976d2'
    }
  });

  return (
    <>
      <AppBar 
        position="sticky" 
        sx={{ 
          bgcolor: '#ffffff', 
          color: '#333333', 
          boxShadow: '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.05)',
          borderBottom: '1px solid #e0e0e0'
        }}
      >
        <Toolbar sx={{ py: 0.25, minHeight: '56px' }}>
          <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}>
            <Box 
              component={Link}
              to="/dashboard"
              sx={{ 
                display: 'flex',
                alignItems: 'center',
                textDecoration: 'none',
                mr: 2
              }}
            >
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 600,
                  color: '#1976d2',
                  letterSpacing: '0.5px',
                  fontSize: '1.1rem'
                }}
              >
                PROFIXMED AI
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button 
                component={Link} 
                to="/dashboard"
                sx={navButtonStyle('/dashboard')}
              >
                Dashboard
              </Button>
              <Button 
                component={Link} 
                to="/patient-records"
                sx={navButtonStyle('/patient-records')}
              >
                Patient Records
              </Button>
              <Button 
                component={Link} 
                to="/clinical-notes"
                sx={navButtonStyle('/clinical-notes')}
              >
                Clinical Notes
              </Button>
              <Button 
                component={Link} 
                to="/ehr"
                sx={navButtonStyle('/ehr')}
              >
                EHR Integration
              </Button>
            </Box>
          </Box>
          
          <Box sx={{ ml: 2 }}>
            <UserButton 
              afterSignOutUrl="/login"
              appearance={{
                elements: {
                  userButtonAvatarBox: {
                    width: '40px',
                    height: '40px'
                  }
                }
              }}
            />
          </Box>
        </Toolbar>
      </AppBar>
      {children}
    </>
  );
};

export default AuthenticatedLayout;