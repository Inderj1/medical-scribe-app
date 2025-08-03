import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Development mode without Clerk authentication
const DevApp = () => {
  // Mock user context for development
  const mockUser = {
    id: 'dev-user-123',
    emailAddresses: [{ emailAddress: 'dev@example.com' }],
    firstName: 'Dev',
    lastName: 'User'
  };

  // Provide mock auth context
  return (
    <div>
      <div style={{ 
        background: '#ff6b6b', 
        color: 'white', 
        padding: '10px', 
        textAlign: 'center',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999
      }}>
        ⚠️ DEVELOPMENT MODE - Authentication Bypassed
      </div>
      <div style={{ marginTop: '40px' }}>
        <App />
      </div>
    </div>
  );
};

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <DevApp />
  </React.StrictMode>
);