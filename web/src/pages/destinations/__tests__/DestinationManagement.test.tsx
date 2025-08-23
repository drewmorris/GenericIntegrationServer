/**
 * Tests for DestinationManagement page
 * Simplified version with proper Vitest mocking
 */

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DestinationManagement } from '../DestinationManagement';

// Mock hooks
vi.mock('../../../hooks/useDestinations');
vi.mock('../../../hooks/useDeleteDestination');

const mockDestinations = [
  {
    id: 'dest-1',
    name: 'cleverbrag',
    displayName: 'CleverBrag',
    status: 'active',
    config: { api_key: 'test' },
    createdAt: '2025-01-20T10:00:00Z',
    updatedAt: '2025-01-21T10:00:00Z',
    connectorCount: 3,
    syncCount: 150,
    errorCount: 2,
  },
];

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
        <BrowserRouter>{children}</BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

const renderDestinationManagement = () => {
  return render(
    <TestWrapper>
      <DestinationManagement />
    </TestWrapper>,
  );
};

describe('DestinationManagement', () => {
  const mockDeleteDestination = vi.fn();
  const mockRefetch = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();

    const { useDestinations } = await import('../../../hooks/useDestinations');
    const { useDeleteDestination } = await import('../../../hooks/useDeleteDestination');

    vi.mocked(useDestinations).mockReturnValue({
      data: mockDestinations,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    vi.mocked(useDeleteDestination).mockReturnValue({
      mutateAsync: mockDeleteDestination,
    });
  });

  it('renders destination management page', () => {
    renderDestinationManagement();

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Destinations')).toBeInTheDocument();
  });

  it('displays status overview cards', () => {
    renderDestinationManagement();

    expect(screen.getByText('Total Destinations')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Inactive')).toBeInTheDocument();
    expect(screen.getByText('Errors')).toBeInTheDocument();
  });

  it('shows loading state', async () => {
    const { useDestinations } = await import('../../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: mockRefetch,
    });

    renderDestinationManagement();

    // Should show loading skeletons
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('shows error state with retry option', async () => {
    const { useDestinations } = await import('../../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
      refetch: mockRefetch,
    });

    renderDestinationManagement();

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Failed to load destinations. Please try again.')).toBeInTheDocument();
  });

  it('shows empty state when no destinations exist', async () => {
    const { useDestinations } = await import('../../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    renderDestinationManagement();

    expect(screen.getByText('No Destinations Yet')).toBeInTheDocument();
    expect(screen.getByText('Add Your First Destination')).toBeInTheDocument();
  });
});
