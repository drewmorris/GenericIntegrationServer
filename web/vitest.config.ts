/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./vitest.setup.ts'],
        css: true,
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html', 'lcov'],
            exclude: [
                'node_modules/',
                'src/test-utils/',
                '**/*.d.ts',
                '**/*.config.*',
                '**/coverage/**',
                '**/dist/**',
                '**/.{idea,git,cache,output,temp}/**',
                '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
            ],
            thresholds: {
                global: {
                    branches: 80,
                    functions: 80,
                    lines: 80,
                    statements: 80,
                },
                // Component-specific thresholds
                'src/components/': {
                    branches: 85,
                    functions: 85,
                    lines: 85,
                    statements: 85,
                },
                'src/hooks/': {
                    branches: 90,
                    functions: 90,
                    lines: 90,
                    statements: 90,
                },
            },
        },
        // Performance testing
        benchmark: {
            include: ['**/*.{bench,benchmark}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
        },
        // Accessibility testing
        include: [
            '**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
            '**/*.a11y.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
        ],
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
            '@/test-utils': path.resolve(__dirname, './src/test-utils'),
        },
    },
});


