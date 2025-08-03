import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import { MockAuthProvider } from './contexts/MockAuthContext';
import './index.css';
import App from './App';

const clerkPubKey = process.env.REACT_APP_CLERK_PUBLISHABLE_KEY;
const isDevelopment = process.env.NODE_ENV === 'development';

// Use mock auth in development if Clerk key is invalid
const shouldUseMockAuth = isDevelopment && (!clerkPubKey || clerkPubKey.includes('$'));

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

if (shouldUseMockAuth) {
  console.warn('⚠️ Running in development mode with mock authentication');
  root.render(
    <React.StrictMode>
      <MockAuthProvider>
        <App />
      </MockAuthProvider>
    </React.StrictMode>
  );
} else {
  if (!clerkPubKey) {
    throw new Error("Missing Clerk Publishable Key");
  }
  root.render(
    <React.StrictMode>
      <ClerkProvider publishableKey={clerkPubKey}>
        <App />
      </ClerkProvider>
    </React.StrictMode>
  );
}