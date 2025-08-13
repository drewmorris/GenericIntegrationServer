import axios, { type AxiosError } from 'axios';

const devBase =
  typeof window !== 'undefined' && window.location.port === '5173' ? 'http://localhost:8000' : '/';
export const api = axios.create({ baseURL: (import.meta as any)?.env?.VITE_API_BASE || devBase });

export function setupInterceptors(opts: {
  accessToken: string | null;
  refreshToken: string | null;
  login: (access: string, refresh: string) => void;
  logout: () => void;
  enqueue?: (msg: string, options?: { variant?: 'error' | 'success' | 'info' | 'warning' }) => void;
}) {
  api.interceptors.request.use((config) => {
    if (opts.accessToken) {
      config.headers.Authorization = `Bearer ${opts.accessToken}`;
    }
    // Attach org header if available
    const orgId = typeof window === 'undefined' ? null : localStorage.getItem('org_id');
    if (orgId) {
      (config.headers as any)['X-Org-ID'] = orgId;
    }
    return config;
  });

  // generic error snackbar
  api.interceptors.response.use(
    (resp) => resp,
    (error: AxiosError<{ detail?: string }>) => {
      if (opts.enqueue) {
        const msg = error.response?.data?.detail ?? error.message ?? 'Unknown error';
        opts.enqueue(msg, { variant: 'error' });
      }
      return Promise.reject(error);
    },
  );
}
