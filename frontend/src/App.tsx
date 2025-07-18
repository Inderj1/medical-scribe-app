import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Container } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from '@clerk/clerk-react';
import EpicLaunch from './components/Auth/EpicLaunch';
import EpicCallback from './components/Auth/EpicCallback';
import LoginPage from './components/Auth/LoginPage';
import SignUpPage from './components/Auth/SignUpPage';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import AuthenticatedLayout from './components/Layout/AuthenticatedLayout';

// Page imports
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import PatientRecordsPage from './pages/PatientRecordsPage';
import ClinicalNotesPage from './pages/ClinicalNotesPage';
import EHRIntegrationPage from './pages/EHRIntegrationPage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function AppContent() {
  const { isSignedIn } = useAuth();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {isSignedIn && (
        <AuthenticatedLayout>
          <span />
        </AuthenticatedLayout>
      )}

      {/* Main Content */}
      <Container>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/sign-up" element={<SignUpPage />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } />
          <Route path="/patient-records" element={
            <ProtectedRoute>
              <PatientRecordsPage />
            </ProtectedRoute>
          } />
          <Route path="/clinical-notes" element={
            <ProtectedRoute>
              <ClinicalNotesPage />
            </ProtectedRoute>
          } />
          <Route path="/ehr" element={
            <ProtectedRoute>
              <EHRIntegrationPage />
            </ProtectedRoute>
          } />
          <Route path="/api/auth/epic/callback" element={
            <ProtectedRoute>
              <EpicCallback />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Container>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AppContent />
      </Router>
    </QueryClientProvider>
  );
}

export default App;