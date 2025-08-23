/* eslint-env node */
module.exports = {
    root: true,
    parser: '@typescript-eslint/parser',
    parserOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
        ecmaFeatures: {
            jsx: true,
        },
    },
    env: {
        browser: true,
        node: true,
        es2022: true,
    },
    settings: {
        react: { version: 'detect' },
    },
    plugins: [
        '@typescript-eslint',
        'react',
        'react-hooks',
        'import',
        'jsx-a11y',
    ],
    extends: [
        'eslint:recommended',
        'plugin:react/recommended',
        'plugin:react-hooks/recommended',
        'plugin:@typescript-eslint/recommended',
        'plugin:import/recommended',
        'plugin:import/typescript',
        'plugin:jsx-a11y/recommended',
        'prettier',
    ],
    ignorePatterns: [
        'node_modules/',
        'dist/',
        'build/',
        'coverage/',
        '*.config.js',
        '*.config.cjs',
    ],
    rules: {
        // React rules
        'react/react-in-jsx-scope': 'off',
        'react/prop-types': 'off',
        'react/no-unescaped-entities': 'off',
        'react/no-array-index-key': 'warn',
        'react-hooks/exhaustive-deps': 'warn',

        // TypeScript rules (simplified)
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-unused-vars': 'off',
        '@typescript-eslint/consistent-type-definitions': ['error', 'type'],
        '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],

        // Import rules
        'import/no-unresolved': 'error',
        'import/no-extraneous-dependencies': ['error', { 
            devDependencies: [
                '**/*.{test,spec}.{ts,tsx,js,jsx}', 
                '**/*.config.{js,cjs,ts}', 
                '**/vite.{config,env}.{js,cjs,ts}'
            ] 
        }],
        'import/order': [
            'error',
            {
                'groups': [
                    'builtin',
                    'external',
                    'internal',
                    'parent',
                    'sibling',
                    'index'
                ],
                'newlines-between': 'always',
                'alphabetize': {
                    'order': 'asc',
                    'caseInsensitive': true
                }
            }
        ],

        // General rules
        'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
    overrides: [
        {
            files: ['**/*.{test,spec}.{ts,tsx,js,jsx}'],
            env: { jest: true },
        },
        {
            files: ['*.config.{js,cjs,ts}', 'vite.{config,env}.{js,cjs,ts}'],
        },
    ],
};