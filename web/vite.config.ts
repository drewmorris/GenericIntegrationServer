// @ts-nocheck
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/auth': { target: 'http://localhost:8000', changeOrigin: true, secure: false },
            '/profiles': { target: 'http://localhost:8000', changeOrigin: true, secure: false },
            '/orchestrator': { target: 'http://localhost:8000', changeOrigin: true, secure: false },
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './vitest.setup.ts',
    },
}); 