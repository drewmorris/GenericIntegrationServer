/**
 * Enhanced API client with retry mechanisms, better error handling, and user feedback
 */
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Enhanced error class with user-friendly messages
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public userMessage?: string,
    public retryable?: boolean,
    public originalError?: Error,
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Retry configuration
interface RetryConfig {
  retries: number;
  retryDelay: number;
  retryCondition?: (error: AxiosError) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  retries: 3,
  retryDelay: 1000, // 1 second
  retryCondition: (error: AxiosError) => {
    // Retry on network errors or 5xx server errors
    return !error.response || (error.response.status >= 500 && error.response.status < 600);
  },
};

// Create axios instance with enhanced configuration
export const enhancedApi = axios.create({
  baseURL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication and org headers
enhancedApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const orgId = localStorage.getItem('org_id');
  if (orgId) {
    config.headers['X-Org-ID'] = orgId;
  }

  return config;
});

// Enhanced response interceptor with retry logic
enhancedApi.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & {
      _retryCount?: number;
      _retryConfig?: RetryConfig;
    };

    // Initialize retry count
    config._retryCount = config._retryCount || 0;
    config._retryConfig = config._retryConfig || defaultRetryConfig;

    // Check if we should retry
    const shouldRetry =
      config._retryCount < config._retryConfig.retries &&
      config._retryConfig.retryCondition?.(error);

    if (shouldRetry) {
      config._retryCount++;

      // Exponential backoff with jitter
      const delay =
        config._retryConfig.retryDelay * Math.pow(2, config._retryCount - 1) + Math.random() * 1000;

      await new Promise((resolve) => setTimeout(resolve, delay));

      return enhancedApi.request(config);
    }

    // Convert to APIError with user-friendly messages
    const apiError = createAPIError(error);
    throw apiError;
  },
);

// Create user-friendly error messages
function createAPIError(error: AxiosError): APIError {
  let userMessage = 'An unexpected error occurred. Please try again.';
  let retryable = false;
  let statusCode = error.response?.status;

  if (error.code === 'NETWORK_ERROR' || error.code === 'ECONNABORTED') {
    userMessage = 'Network connection failed. Please check your internet connection and try again.';
    retryable = true;
  } else if (error.response) {
    statusCode = error.response.status;

    switch (statusCode) {
      case 400:
        userMessage =
          extractErrorMessage(error.response.data) ||
          'The request was invalid. Please check your input and try again.';
        break;
      case 401:
        userMessage = 'Your session has expired. Please log in again.';
        break;
      case 403:
        userMessage = "You don't have permission to perform this action.";
        break;
      case 404:
        userMessage = 'The requested resource was not found.';
        break;
      case 409:
        userMessage =
          extractErrorMessage(error.response.data) ||
          'A conflict occurred. The resource may have been modified by another user.';
        break;
      case 422:
        userMessage =
          extractErrorMessage(error.response.data) ||
          'The provided data is invalid. Please check your input.';
        break;
      case 429:
        userMessage = 'Too many requests. Please wait a moment and try again.';
        retryable = true;
        break;
      case 500:
        userMessage = 'A server error occurred. Our team has been notified.';
        retryable = true;
        break;
      case 502:
      case 503:
      case 504:
        userMessage = 'The service is temporarily unavailable. Please try again in a few moments.';
        retryable = true;
        break;
      default:
        userMessage = `Server error (${statusCode}). Please try again or contact support.`;
        retryable = statusCode >= 500;
    }
  } else if (error.code === 'ECONNABORTED') {
    userMessage = 'The request timed out. Please try again.';
    retryable = true;
  }

  return new APIError(error.message, statusCode, userMessage, retryable, error);
}

// Extract error message from API response
function extractErrorMessage(data: any): string | null {
  if (typeof data === 'string') {
    return data;
  }

  if (data && typeof data === 'object') {
    // Try common error message fields
    const messageFields = ['detail', 'message', 'error', 'error_message'];

    for (const field of messageFields) {
      if (data[field] && typeof data[field] === 'string') {
        return data[field];
      }
    }

    // Handle validation errors
    if (data.errors && Array.isArray(data.errors)) {
      return data.errors.map((err: any) => err.message || err).join(', ');
    }
  }

  return null;
}

// Wrapper function to make API calls with enhanced error handling
export const apiRequest = async <T = any>(
  config: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
): Promise<T> => {
  const { retryConfig, ...requestConfig } = config;

  // Merge retry config
  const finalConfig = {
    ...requestConfig,
    _retryConfig: { ...defaultRetryConfig, ...retryConfig },
  };

  const response = await enhancedApi.request(finalConfig);
  return response.data;
};

// Convenience methods
export const apiGet = <T = any>(
  url: string,
  config?: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
) => apiRequest<T>({ ...config, method: 'GET', url });

export const apiPost = <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
) => apiRequest<T>({ ...config, method: 'POST', url, data });

export const apiPut = <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
) => apiRequest<T>({ ...config, method: 'PUT', url, data });

export const apiPatch = <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
) => apiRequest<T>({ ...config, method: 'PATCH', url, data });

export const apiDelete = <T = any>(
  url: string,
  config?: AxiosRequestConfig & { retryConfig?: Partial<RetryConfig> },
) => apiRequest<T>({ ...config, method: 'DELETE', url });

// Setup function for auth context
export const setupEnhancedInterceptors = (onUnauthorized?: () => void) => {
  // Clear existing response interceptors
  enhancedApi.interceptors.response.clear();

  enhancedApi.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError) => {
      // Handle auth errors first
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (onUnauthorized) {
          onUnauthorized();
        }

        // Don't retry 401 errors
        throw createAPIError(error);
      }

      // Then handle retry logic for other errors
      const config = error.config as AxiosRequestConfig & {
        _retryCount?: number;
        _retryConfig?: RetryConfig;
      };

      config._retryCount = config._retryCount || 0;
      config._retryConfig = config._retryConfig || defaultRetryConfig;

      const shouldRetry =
        config._retryCount < config._retryConfig.retries &&
        config._retryConfig.retryCondition?.(error);

      if (shouldRetry) {
        config._retryCount++;
        const delay =
          config._retryConfig.retryDelay * Math.pow(2, config._retryCount - 1) +
          Math.random() * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
        return enhancedApi.request(config);
      }

      throw createAPIError(error);
    },
  );
};
