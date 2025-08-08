// @ts-nocheck
import { createContext, useContext, useState, useEffect } from 'react';
import { api, setupInterceptors } from '../lib/api';
import { useSnack } from '../components/Snackbar';

interface AuthState {
    accessToken: string | null;
    refreshToken: string | null;
}

interface AuthCtx extends AuthState {
    login: (access: string, refresh: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [accessToken, setAccess] = useState<string | null>(() => localStorage.getItem('access_token'));
    const [refreshToken, setRefresh] = useState<string | null>(() => localStorage.getItem('refresh_token'));

    const login = (access: string, refresh: string) => {
        setAccess(access);
        setRefresh(refresh);
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    };

    const logout = () => {
        setAccess(null);
        setRefresh(null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    };

    const snack = useSnack();

    useEffect(() => {
        setupInterceptors({ accessToken, refreshToken, login, logout, enqueue: snack.enqueue });

        const id = api.interceptors.response.use(undefined, async (error) => {
            if (error.response?.status === 401 && refreshToken) {
                try {
                    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
                    login(data.access_token, data.refresh_token);
                    error.config.headers.Authorization = `Bearer ${data.access_token}`;
                    return api.request(error.config);
                } catch {
                    logout();
                }
            }
            return Promise.reject(error);
        });
        return () => api.interceptors.response.eject(id);
    }, [accessToken, refreshToken]);

    return <AuthContext.Provider value={{ accessToken, refreshToken, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('AuthContext not found');
    return ctx;
}; 