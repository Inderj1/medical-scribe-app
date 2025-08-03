// This approach won't work due to React hooks rules
// Instead, we need to handle this at the provider level
export const useAuth = () => {
  // For now, just create a mock auth object
  return {
    isLoaded: true,
    isSignedIn: true,
    signIn: () => console.log('Mock sign in'),
    signOut: () => console.log('Mock sign out'),
    getToken: async () => 'mock-dev-token'
  };
};

export const useUser = () => {
  return {
    user: {
      id: 'dev-user-123',
      emailAddresses: [{ emailAddress: 'dev@medicalscribe.com' }],
      firstName: 'Dev',
      lastName: 'User',
      fullName: 'Dev User'
    },
    isSignedIn: true,
    isLoaded: true
  };
};