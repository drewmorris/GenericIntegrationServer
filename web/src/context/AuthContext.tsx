import type { AxiosError, AxiosRequestConfig } from 'axios';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useSnack } from '../components/Snackbar';
import { api, setupInterceptors } from '../lib/api';

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
};

type AuthCtx = {
  login: (access: string, refresh: string) => void;
  logout: () => void;
} & AuthState;

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccess] = useState<string | null>(() =>
    localStorage.getItem('access_token'),
  );
  const [refreshToken, setRefresh] = useState<string | null>(() =>
    localStorage.getItem('refresh_token'),
  );

  const login = useCallback((access: string, refresh: string) => {
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
      .catch(() => {
        // ignore; user can still proceed but org-scoped lists may be empty
      });
  }, []);

  const logout = useCallback(() => {
    setAccess(null);
    setRefresh(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }, []);

  const snack = useSnack();

  useEffect(() => {
    setupInterceptors({ accessToken, refreshToken, login, logout, enqueue: snack.enqueue });

    const id = api.interceptors.response.use(undefined, async (error: AxiosError) => {
      // If token expired, attempt to refresh once then retry original request
      if (error.response?.status === 401 && refreshToken) {
        try {
          const { data } = await api.post<{ access_token: string; refresh_token: string }>(
            '/auth/refresh',
            { refresh_token: refreshToken },
          );
          login(data.access_token, data.refresh_token);

          const cfg = error.config as AxiosRequestConfig;
          if (cfg.headers) cfg.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(cfg);
        } catch {
          logout();
        }
      }
      throw error;
    });
    return () => api.interceptors.response.eject(id);
  }, [accessToken, refreshToken, login, logout, snack.enqueue]);

  return (
    <AuthContext.Provider value={{ accessToken, refreshToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('AuthContext not found');
  return ctx;
};
