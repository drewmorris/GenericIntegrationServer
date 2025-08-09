import axios, { type AxiosError } from 'axios';

export const api = axios.create({ baseURL: '/' });

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
