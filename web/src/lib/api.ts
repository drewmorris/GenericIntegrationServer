/**
 * API client configuration
 * Provides axios instance with authentication and error handling
 */
import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const orgId = localStorage.getItem('organization_id');
  if (orgId) {
    config.headers['X-Org-ID'] = orgId;
  }

  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could trigger logout
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    return Promise.reject(new Error((error as Error).message || 'API request failed'));
  },
);

// Setup interceptors function for AuthContext
export const setupInterceptors = (onUnauthorized?: () => void) => {
  // Update response interceptor to handle unauthorized with callback
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (onUnauthorized) {
          onUnauthorized();
        }
      }
      return Promise.reject(new Error((error as Error).message || 'API request failed'));
    },
  );
};
