/**
 * Tests for ConnectorGallery component
 * Simplified version with proper Vitest mocking
 */

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ConnectorGallery } from '../ConnectorGallery';

// Mock the hooks
vi.mock('../../hooks/useConnectorDefinitions');
vi.mock('../../hooks/useDestinations');

// Mock the logo imports
vi.mock('../../assets/connector-logos', () => ({
  getConnectorLogo: vi.fn(() => '/mock-connector-logo.png'),
  getDestinationLogo: vi.fn(() => '/mock-destination-logo.png'),
  connectorCategories: {
    'Email & Communication': ['gmail', 'slack'],
    Databases: ['postgres'],
  },
  getConnectorCategory: vi.fn((source: string) => {
    if (['gmail', 'slack'].includes(source)) return 'Email & Communication';
    if (source === 'postgres') return 'Databases';
    return 'Other';
  }),
}));

const mockConnectors = [
  {
    source: 'gmail',
    name: 'Gmail',
    description: 'Sync emails and attachments from Gmail',
    auth_type: 'oauth',
  },
];

const mockDestinations = [
  {
    id: 'dest-1',
    name: 'CleverBrag',
    displayName: 'CleverBrag',
    config: { api_key: 'test-key' },
    status: 'active' as const,
    createdAt: '2025-01-21T10:00:00Z',
    updatedAt: '2025-01-21T10:00:00Z',
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
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  );
};

describe('ConnectorGallery', () => {
  const mockOnSelectPair = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();

    // Setup default mock returns
    const { useConnectorDefinitions } = await import('../../hooks/useConnectorDefinitions');
    const { useDestinations } = await import('../../hooks/useDestinations');

    vi.mocked(useConnectorDefinitions).mockReturnValue({
      data: mockConnectors,
      isLoading: false,
      error: null,
    });

    vi.mocked(useDestinations).mockReturnValue({
      data: mockDestinations,
      isLoading: false,
      error: null,
    });
  });

  it('renders connector gallery', () => {
    render(
      <TestWrapper>
        <ConnectorGallery onSelectPair={mockOnSelectPair} />
      </TestWrapper>,
    );

    expect(screen.getByText('Add Connector')).toBeInTheDocument();
  });

  it('shows loading state', async () => {
    const { useConnectorDefinitions } = await import('../../hooks/useConnectorDefinitions');
    vi.mocked(useConnectorDefinitions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <TestWrapper>
        <ConnectorGallery onSelectPair={mockOnSelectPair} />
      </TestWrapper>,
    );

    // Should render loading component
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('shows no destinations message when no destinations exist', async () => {
    const { useDestinations } = await import('../../hooks/useDestinations');
    vi.mocked(useDestinations).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(
      <TestWrapper>
        <ConnectorGallery onSelectPair={mockOnSelectPair} />
      </TestWrapper>,
    );

    expect(screen.getByText('No Destinations Configured')).toBeInTheDocument();
    expect(screen.getByText('Set Up Your First Destination')).toBeInTheDocument();
  });
});
