module.exports = {
    ci: {
        collect: {
            url: ['http://localhost:4173'], // Use preview server port
            startServerCommand: 'npm run preview',
            startServerReadyPattern: 'Local:   http://localhost:4173',
            startServerReadyTimeout: 30000,
            numberOfRuns: 3, // Run lighthouse 3 times and take median
        },
        assert: {
            assertions: {
                // Performance budgets
                'categories:performance': ['error', { minScore: 0.8 }],
                'categories:accessibility': ['error', { minScore: 0.9 }],
                'categories:best-practices': ['error', { minScore: 0.8 }],
                'categories:seo': ['error', { minScore: 0.8 }],

                // Core Web Vitals
                'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
                'largest-contentful-paint': ['error', { maxNumericValue: 4000 }],
                'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
                'total-blocking-time': ['warn', { maxNumericValue: 500 }],
            },
        },
        upload: {
            target: 'temporary-public-storage', // For CI - results stored temporarily
        },
    },
};
