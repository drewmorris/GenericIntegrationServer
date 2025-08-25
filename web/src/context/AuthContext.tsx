import type { AxiosError, AxiosRequestConfig } from 'axios';
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { api, setupInterceptors } from '../lib/api';

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
};

type AuthCtx = {
  login: (access: string, refresh: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
} & AuthState;

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccess] = useState<string | null>(() =>
    localStorage.getItem('access_token'),
  );
  const [refreshToken, setRefresh] = useState<string | null>(() =>
    localStorage.getItem('refresh_token'),
  );

  // Use ref to track if we're currently refreshing to prevent loops
  const isRefreshing = useRef(false);
  const cleanupInterceptor = useRef<(() => void) | null>(null);

  const clearAuthData = useCallback(() => {
    setAccess(null);
    setRefresh(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('org_id');
  }, []);

  const logout = useCallback(() => {
    console.log('Logout called - clearing auth data and redirecting');
    clearAuthData();

    // Force navigation to login page
    // Using window.location instead of useNavigate since this is in a context
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }, [clearAuthData]);

  const login = useCallback((access: string, refresh: string) => {
    console.log('Login called - setting tokens');
    setAccess(access);
    setRefresh(refresh);
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);

    // Populate org/user from backend
    api
      .get('/auth/me', { headers: { Authorization: `Bearer ${access}` } })
      .then((resp) => {
        const { user_id, organization_id } = resp.data as {
          user_id: string;
          organization_id: string;
        };
        localStorage.setItem('user_id', user_id);
        localStorage.setItem('org_id', organization_id);
      })
      .catch((error) => {
        console.warn('Failed to fetch user info after login:', error);
        // Don't logout on this failure - user can still use the app
      });
  }, []);

  // Set up interceptors and token refresh logic
  useEffect(() => {
    // Clean up any existing interceptor
    if (cleanupInterceptor.current) {
      cleanupInterceptor.current();
    }

    // Set up the global interceptor with logout callback
    cleanupInterceptor.current = setupInterceptors(logout);

    // Set up token refresh interceptor
    const refreshInterceptorId = api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        // Only handle 401 errors for refresh logic
        if (error.response?.status === 401 && refreshToken && !isRefreshing.current) {
          isRefreshing.current = true;

          try {
            console.log('Attempting to refresh expired token');
            const { data } = await api.post<{ access_token: string; refresh_token: string }>(
              '/auth/refresh',
              { refresh_token: refreshToken },
              {
                // Don't trigger interceptors for refresh request
                skipAuthRefresh: true,
              } as any,
            );

            // Update tokens
            login(data.access_token, data.refresh_token);

            // Retry the original request with new token
            const config = error.config as AxiosRequestConfig;
            if (config?.headers) {
              config.headers.Authorization = `Bearer ${data.access_token}`;
            }

            isRefreshing.current = false;
            return api.request(config);
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            isRefreshing.current = false;

            // Refresh failed - logout user
            logout();
            return Promise.reject(error);
          }
        }

        // For non-401 errors or if already refreshing, just pass through
        return Promise.reject(error);
      },
    );

    return () => {
      // Cleanup on unmount or deps change
      if (cleanupInterceptor.current) {
        cleanupInterceptor.current();
      }
      api.interceptors.response.eject(refreshInterceptorId);
      isRefreshing.current = false;
    };
  }, [logout, login, refreshToken]);

  // Monitor accessToken changes and redirect if needed
  useEffect(() => {
    if (
      !accessToken &&
      window.location.pathname !== '/login' &&
      window.location.pathname !== '/signup'
    ) {
      console.log('No access token found - redirecting to login');
      window.location.href = '/login';
    }
  }, [accessToken]);

  const isAuthenticated = Boolean(accessToken);

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        refreshToken,
        login,
        logout,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('AuthContext not found');
  return ctx;
};
