/**
 * Tests for DestinationSetupWizard component
 * Simplified version with proper Vitest mocking
 */

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMockMutationResult } from '../../../test-utils/mockHelpers';
import { DestinationSetupWizard } from '../DestinationSetupWizard';

// Mock hooks and components
vi.mock('../../../hooks/useCreateDestination');

// Mock the step components
vi.mock('../../../components/onboarding/DestinationSelector', () => ({
  DestinationSelector: vi.fn(() => (
    <div data-testid="destination-selector">Destination Selector</div>
  )),
}));

vi.mock('../../../components/onboarding/DestinationConfiguration', () => ({
  DestinationConfiguration: vi.fn(() => (
    <div data-testid="destination-configuration">Destination Configuration</div>
  )),
}));

vi.mock('../../../components/onboarding/ConnectionTest', () => ({
  ConnectionTest: vi.fn(() => <div data-testid="connection-test">Connection Test</div>),
}));

vi.mock('../../../components/onboarding/SetupComplete', () => ({
  SetupComplete: vi.fn(() => <div data-testid="setup-complete">Setup Complete</div>),
}));

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

const renderWizard = () => {
  return render(
    <TestWrapper>
      <DestinationSetupWizard />
    </TestWrapper>,
  );
};

describe('DestinationSetupWizard', () => {
  const mockCreateDestination = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    const { useCreateDestination } = await import('../../../hooks/useCreateDestination');
    vi.mocked(useCreateDestination).mockReturnValue(
      createMockMutationResult({
        mutateAsync: mockCreateDestination,
      }),
    );
  });

  it('renders wizard with main heading', () => {
    renderWizard();

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Set Up Your First Destination')).toBeInTheDocument();
  });

  it('shows progress indicator', () => {
    renderWizard();

    expect(screen.getByText('Step 1 of 4')).toBeInTheDocument();
  });

  it('renders the first step component', () => {
    renderWizard();

    expect(screen.getByTestId('destination-selector')).toBeInTheDocument();
  });

  it('has navigation buttons', () => {
    renderWizard();

    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Continue')).toBeInTheDocument();
  });
});
