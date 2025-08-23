/**
 * Tests for DestinationGuard component
 * Simplified version with proper Vitest mocking
 */

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DestinationGuard } from '../DestinationGuard';

// Mock the useDestinations hook
vi.mock('../../hooks/useDestinations');

const TestComponent = () => <div>Protected Content</div>;

const TestWrapper: React.FC<{
  children: React.ReactNode;
  initialPath?: string;
}> = ({ children, initialPath = '/' }) => {
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
        <MemoryRouter initialEntries={[initialPath]}>{children}</MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('DestinationGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when destinations exist', async () => {
    const { useDestinations } = await import('../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: [{ id: '1', name: 'Test Destination' }],
      isLoading: false,
      error: null,
    });

    render(
      <TestWrapper>
        <DestinationGuard>
          <TestComponent />
        </DestinationGuard>
      </TestWrapper>,
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('shows loading state while fetching destinations', async () => {
    const { useDestinations } = await import('../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <TestWrapper>
        <DestinationGuard>
          <TestComponent />
        </DestinationGuard>
      </TestWrapper>,
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByLabelText('Loading destinations')).toBeInTheDocument();
  });

  it('shows error state when destinations fail to load', async () => {
    const { useDestinations } = await import('../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
    });

    render(
      <TestWrapper>
        <DestinationGuard>
          <TestComponent />
        </DestinationGuard>
      </TestWrapper>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Failed to load destinations/)).toBeInTheDocument();
  });

  it('allows access on onboarding routes', async () => {
    const { useDestinations } = await import('../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(
      <TestWrapper initialPath="/onboarding/destinations">
        <DestinationGuard>
          <TestComponent />
        </DestinationGuard>
      </TestWrapper>,
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
