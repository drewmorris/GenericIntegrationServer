/**
 * Enhanced testing utilities with Material-UI and accessibility support
 */

import { CssBaseline } from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { RenderOptions } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { SnackbarProvider } from 'notistack';
import type React from 'react';
import type { ReactElement } from 'react';
import { BrowserRouter } from 'react-router-dom';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Create test theme with accessibility enhancements
const testTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e',
      contrastText: '#ffffff',
    },
  },
  components: {
    // Ensure proper contrast ratios
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 44, // WCAG touch target size
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          minWidth: 44, // WCAG touch target size
          minHeight: 44,
        },
      },
    },
  },
});

type AllTheProvidersProps = {
  children: React.ReactNode;
};

const AllTheProviders: React.FC<AllTheProvidersProps> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Number.POSITIVE_INFINITY,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider theme={testTheme}>
          <CssBaseline />
          <SnackbarProvider maxSnack={3}>{children}</SnackbarProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

const customRender = (ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) =>
  render(ui, { wrapper: AllTheProviders, ...options });

// Accessibility testing utilities
export const runAxeTest = async (container: HTMLElement) => {
  const results = await axe(container);
  expect(results).toHaveNoViolations();
};

// Keyboard navigation testing
export const testKeyboardNavigation = (element: HTMLElement) => {
  element.focus();
  expect(document.activeElement).toBe(element);
};

// Material-UI specific testing utilities
export const getMuiButton = (name: string) => screen.getByRole('button', { name });
export const getMuiTextField = (label: string) => screen.getByLabelText(label);
export const getMuiSelect = (label: string) => screen.getByLabelText(label);

// Performance testing utilities
export const measureRenderTime = (renderFn: () => void) => {
  const start = performance.now();
  renderFn();
  const end = performance.now();
  return end - start;
};

// Re-export everything except render to avoid conflicts
export {
  act,
  cleanup,
  createEvent,
  findAllByAltText,
  findAllByDisplayValue,
  findAllByLabelText,
  findAllByRole,
  findAllByTestId,
  findAllByText,
  findAllByTitle,
  findByAltText,
  findByDisplayValue,
  findByLabelText,
  findByRole,
  findByTestId,
  findByText,
  findByTitle,
  fireEvent,
  getAllByAltText,
  getAllByDisplayValue,
  getAllByLabelText,
  getAllByRole,
  getAllByTestId,
  getAllByText,
  getAllByTitle,
  getByAltText,
  getByDisplayValue,
  getByLabelText,
  getByRole,
  getByTestId,
  getByText,
  getByTitle,
  queryAllByAltText,
  queryAllByDisplayValue,
  queryAllByLabelText,
  queryAllByRole,
  queryAllByTestId,
  queryAllByText,
  queryAllByTitle,
  queryByAltText,
  queryByDisplayValue,
  queryByLabelText,
  queryByRole,
  queryByTestId,
  queryByText,
  queryByTitle,
  renderHook,
  screen,
  waitFor,
  waitForElementToBeRemoved,
  within,
} from '@testing-library/react';

// Export our custom render function
export { customRender as render };
export { testTheme };
