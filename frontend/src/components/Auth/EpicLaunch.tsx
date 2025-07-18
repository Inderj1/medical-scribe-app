import React, { useState } from 'react';

const EpicLaunch: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEpicLaunch = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/auth/epic/launch');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.authorization_url) {
        // Store state for validation on callback
        sessionStorage.setItem('epic_oauth_state', data.state);
        
        // Redirect to Epic authorization
        window.location.href = data.authorization_url;
      } else {
        throw new Error('No authorization URL received');
      }
    } catch (err) {
      console.error('Epic launch failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      border: '1px solid #e0e0e0', 
      borderRadius: '8px',
      backgroundColor: '#f5f5f5'
    }}>
      <h4>🔗 Epic FHIR Integration</h4>
      <p>Connect to Epic EHR systems for patient data access.</p>
      
      {error && (
        <div style={{
          padding: '10px',
          marginBottom: '10px',
          backgroundColor: '#f8d7da',
          border: '1px solid #f5c6cb',
          borderRadius: '4px',
          color: '#721c24'
        }}>
          Error: {error}
        </div>
      )}
      
      <button 
        onClick={handleEpicLaunch}
        disabled={isLoading}
        style={{
          padding: '10px 20px',
          backgroundColor: isLoading ? '#6c757d' : '#0d6efd',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer'
        }}
      >
        {isLoading ? 'Launching...' : 'Launch Epic Integration'}
      </button>
    </div>
  );
};

export default EpicLaunch;