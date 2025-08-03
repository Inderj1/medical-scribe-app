import React, { createContext, useContext } from 'react';

interface MockUser {
  id: string;
  emailAddresses: Array<{ emailAddress: string }>;
  firstName?: string;
  lastName?: string;
  fullName?: string;
}

interface MockAuthContextType {
  isLoaded: boolean;
  isSignedIn: boolean;
  user: MockUser | null;
  signIn: () => void;
  signOut: () => void;
}

const MockAuthContext = createContext<MockAuthContextType | undefined>(undefined);

export const useMockAuth = () => {
  const context = useContext(MockAuthContext);
  if (!context) {
    throw new Error('useMockAuth must be used within MockAuthProvider');
  }
  return context;
};

export const MockAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const mockUser: MockUser = {
    id: 'dev-user-123',
    emailAddresses: [{ emailAddress: 'dev@medicalscribe.com' }],
    firstName: 'Dev',
    lastName: 'User',
    fullName: 'Dev User'
  };

  const value: MockAuthContextType = {
    isLoaded: true,
    isSignedIn: true,
    user: mockUser,
    signIn: () => console.log('Mock sign in'),
    signOut: () => console.log('Mock sign out')
  };

  return (
    <MockAuthContext.Provider value={value}>
      {children}
    </MockAuthContext.Provider>
  );
};

// Mock Clerk hooks for development
export const useUser = () => {
  const { user, isSignedIn, isLoaded } = useMockAuth();
  return { user, isSignedIn, isLoaded };
};

export const useAuth = () => {
  const { signIn, signOut } = useMockAuth();
  return { signIn, signOut };
};

export const useClerk = () => {
  return {
    signOut: () => console.log('Mock sign out'),
    redirectToSignIn: () => console.log('Mock redirect to sign in')
  };
};