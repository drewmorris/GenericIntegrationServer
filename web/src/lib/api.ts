// @ts-nocheck
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

export const api = axios.create({ baseURL: '/' });

export function setupInterceptors(opts: { accessToken: string | null; refreshToken: string | null; login: any; logout: any; enqueue?: (msg: string, options?: any) => void; }) {
    api.interceptors.request.use((config) => {
        if (opts.accessToken) {
            config.headers.Authorization = `Bearer ${opts.accessToken}`;
        }
        return config;
    });

    // generic error snackbar
    api.interceptors.response.use(
        (resp) => resp,
        (error) => {
            if (opts.enqueue) {
                const msg = error.response?.data?.detail || error.message || 'Unknown error';
                opts.enqueue(msg, { variant: 'error' });
            }
            return Promise.reject(error);
        },
    );
} 