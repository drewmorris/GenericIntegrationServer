/**
 * Lighthouse CI configuration for performance and accessibility testing
 */
module.exports = {
    ci: {
        collect: {
            url: [
                'http://localhost:5173/',
                'http://localhost:5173/login',
                'http://localhost:5173/connectors',
                'http://localhost:5173/destinations',
            ],
            startServerCommand: 'npm run dev',
            startServerReadyPattern: 'Local:',
            numberOfRuns: 3,
            settings: {
                chromeFlags: '--no-sandbox --disable-dev-shm-usage',
            },
        },
        assert: {
            assertions: {
                // Performance thresholds
                'categories:performance': ['error', { minScore: 0.8 }],
                'categories:accessibility': ['error', { minScore: 0.95 }],
                'categories:best-practices': ['error', { minScore: 0.9 }],
                'categories:seo': ['error', { minScore: 0.8 }],

                // Core Web Vitals
                'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
                'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
                'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
                'total-blocking-time': ['error', { maxNumericValue: 300 }],

                // Accessibility specific
                'color-contrast': 'error',
                'heading-order': 'error',
                'html-has-lang': 'error',
                'image-alt': 'error',
                'label': 'error',
                'link-name': 'error',
                'button-name': 'error',
                'aria-allowed-attr': 'error',
                'aria-required-attr': 'error',
                'aria-roles': 'error',
                'aria-valid-attr': 'error',
                'aria-valid-attr-value': 'error',
                'bypass': 'error',
                'document-title': 'error',
                'duplicate-id-aria': 'error',
                'focus-traps': 'error',
                'focusable-controls': 'error',
                'interactive-element-affordance': 'error',
                'logical-tab-order': 'error',
                'managed-focus': 'error',
                'use-landmarks': 'error',

                // Performance specific
                'unused-css-rules': ['warn', { maxLength: 2 }],
                'unused-javascript': ['warn', { maxLength: 2 }],
                'modern-image-formats': 'warn',
                'uses-optimized-images': 'warn',
                'uses-text-compression': 'error',
                'uses-responsive-images': 'warn',
            },
        },
        upload: {
            target: 'temporary-public-storage',
        },
    },
};


