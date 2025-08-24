/**
 * Accessibility tests for DestinationGuard component  
 * Tests WCAG compliance, ARIA attributes, and screen reader compatibility
 */

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import type React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DestinationGuard } from '../DestinationGuard';
import { createMockQueryResult } from '../../test-utils/mockHelpers';

// Mock the useDestinations hook
vi.mock('../../hooks/useDestinations');

// Extend expect with jest-axe matchers
expect.extend(toHaveNoViolations);

const TestComponent = () => <div>Protected Content</div>;

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
                staleTime: Number.POSITIVE_INFINITY,
            },
        },
    });

    const theme = createTheme();

    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
                <MemoryRouter>{children}</MemoryRouter>
            </ThemeProvider>
        </QueryClientProvider>
    );
};

describe('DestinationGuard - Accessibility', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should not have accessibility violations when loading', async () => {
        const { useDestinations } = await import('../../hooks/useDestinations');
        vi.mocked(useDestinations).mockReturnValue({
            ...createMockQueryResult({
                data: undefined,
                isLoading: true,
                error: null,
            }),
            destinations: [],
        });

        const { container } = render(
            <TestWrapper>
                <DestinationGuard>
                    <TestComponent />
                </DestinationGuard>
            </TestWrapper>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });

    it('should not have accessibility violations when showing content', async () => {
        const { useDestinations } = await import('../../hooks/useDestinations');
        vi.mocked(useDestinations).mockReturnValue({
            ...createMockQueryResult({
                data: [{
                    id: '1',
                    name: 'Test Destination',
                    displayName: 'Test Destination',
                    config: { api_key: 'test' },
                    status: 'active' as const,
                    createdAt: '2025-01-20T10:00:00Z',
                    updatedAt: '2025-01-21T10:00:00Z',
                }],
                isLoading: false,
                error: null,
                isSuccess: true,
            }),
            destinations: [{
                id: '1',
                name: 'Test Destination',
                displayName: 'Test Destination',
                config: { api_key: 'test' },
                status: 'active' as const,
                createdAt: '2025-01-20T10:00:00Z',
                updatedAt: '2025-01-21T10:00:00Z',
            }],
        });

        const { container } = render(
            <TestWrapper>
                <DestinationGuard>
                    <TestComponent />
                </DestinationGuard>
            </TestWrapper>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA attributes for loading state', async () => {
        const { useDestinations } = await import('../../hooks/useDestinations');
        vi.mocked(useDestinations).mockReturnValue({
            ...createMockQueryResult({
                data: undefined,
                isLoading: true,
                error: null,
            }),
            destinations: [],
        });

        const { getByRole } = render(
            <TestWrapper>
                <DestinationGuard>
                    <TestComponent />
                </DestinationGuard>
            </TestWrapper>
        );

        // Check for loading indicator with proper ARIA attributes
        expect(getByRole('status')).toBeInTheDocument();
        expect(getByRole('progressbar')).toBeInTheDocument();
    });
});
