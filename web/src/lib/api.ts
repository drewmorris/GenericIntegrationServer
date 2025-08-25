/**
 * API client configuration
 * Provides axios instance with authentication and error handling
 */
import axios from 'axios';

// Extend the AxiosRequestConfig interface to include skipAuthRefresh
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    skipAuthRefresh?: boolean;
  }
}

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
  if (token && !config.skipAuthRefresh) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const orgId = localStorage.getItem('org_id');
  if (orgId) {
    config.headers['X-Org-ID'] = orgId;
  }

  return config;
});

// Global response interceptor ID to manage cleanup
let responseInterceptorId: number | null = null;

// Setup interceptors function for AuthContext
export const setupInterceptors = (onUnauthorized: () => void) => {
  // Clear existing interceptor if any
  if (responseInterceptorId !== null) {
    api.interceptors.response.eject(responseInterceptorId);
  }

  // Set up single response interceptor with proper error handling
  responseInterceptorId = api.interceptors.response.use(
    (response) => response,
    (error) => {
      // Handle authentication errors globally
      if (error.response?.status === 401) {
        console.warn('Authentication failed - redirecting to login');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('org_id');
        onUnauthorized();
      }
      return Promise.reject(error);
    },
  );

  return () => {
    if (responseInterceptorId !== null) {
      api.interceptors.response.eject(responseInterceptorId);
      responseInterceptorId = null;
    }
  };
};
