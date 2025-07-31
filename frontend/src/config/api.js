// API Configuration
export const getApiUrl = () => {
  // Check if we're in production (deployed) environment
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    // Use the same host as the frontend but on port 8000
    return `http://${window.location.hostname}:8000`;
  }
  
  // Use environment variable or default to localhost
  return process.env.REACT_APP_API_URL || 'http://localhost:8000';
};

export const getWsUrl = () => {
  // Check if we're in production (deployed) environment
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    // Use the same host as the frontend but on port 8000
    return `ws://${window.location.hostname}:8000`;
  }
  
  // Use environment variable or default to localhost
  return process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
};