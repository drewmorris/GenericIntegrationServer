/**
 * Global error handler for React Query and general application errors
 * Provides consistent error handling and user feedback
 */
import { useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { useCallback, useEffect, useMemo } from 'react';

import { APIError } from '../lib/enhanced-api';

export interface ErrorHandlerOptions {
  showSnackbar?: boolean;
  logToConsole?: boolean;
  reportToService?: boolean;
}

const defaultOptions: ErrorHandlerOptions = {
  showSnackbar: true,
  logToConsole: true,
  reportToService: false, // Set to true in production with error service
};

export const useGlobalErrorHandler = (options: ErrorHandlerOptions = {}) => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const finalOptions = useMemo(() => ({ ...defaultOptions, ...options }), [options]);

  // Function to handle individual errors
  const handleError = useCallback(
    (error: Error | APIError, context?: string) => {
      // Skip handling authentication errors - they're handled by AuthContext
      if (error instanceof APIError && error.statusCode === 401) {
        return;
      }

      // Log to console if enabled
      if (finalOptions.logToConsole) {
        console.error(`[${context || 'Global'}] Error:`, error);
      }

      // Show user-friendly snackbar
      if (finalOptions.showSnackbar) {
        let message = 'An unexpected error occurred';
        let variant: 'error' | 'warning' | 'info' = 'error';

        if (error instanceof APIError) {
          message = error.userMessage || error.message;
          variant = error.retryable ? 'warning' : 'error';
        } else if (error.message) {
          message = error.message;
        }

        // Don't show error messages for authentication issues
        if (
          !message.toLowerCase().includes('unauthorized') &&
          !message.toLowerCase().includes('authentication')
        ) {
          enqueueSnackbar(message, {
            variant,
            autoHideDuration: error instanceof APIError && error.retryable ? 5000 : 4000,
          });
        }
      }

      // Report to error service (implement when needed)
      if (finalOptions.reportToService) {
        // TODO: Integrate with error reporting service (Sentry, LogRocket, etc.)
        // reportError(error, context);
      }
    },
    [enqueueSnackbar, finalOptions],
  );

  // Setup global React Query error handling
  useEffect(() => {
    const queryCache = queryClient.getQueryCache();
    const mutationCache = queryClient.getMutationCache();

    // Handle query errors
    const unsubscribeQuery = queryCache.subscribe((event) => {
      if (event.type === 'updated' && event.query.state.status === 'error') {
        const error = event.query.state.error as Error | APIError;
        handleError(error, 'Query');
      }
    });

    // Handle mutation errors
    const unsubscribeMutation = mutationCache.subscribe((event) => {
      if (event.type === 'updated' && event.mutation.state.status === 'error') {
        const error = event.mutation.state.error as Error | APIError;
        handleError(error, 'Mutation');
      }
    });

    return () => {
      unsubscribeQuery();
      unsubscribeMutation();
    };
  }, [queryClient, handleError]);

  // Setup global error event handler
  useEffect(() => {
    const handleGlobalError = (event: ErrorEvent) => {
      handleError(event.error || new Error(event.message), 'Global');
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      handleError(error, 'Unhandled Promise');
    };

    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleGlobalError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleError]);

  // Return the handler for manual error handling
  return {
    handleError,
    showErrorMessage: (message: string, variant: 'error' | 'warning' | 'info' = 'error') => {
      enqueueSnackbar(message, { variant });
    },
    showSuccessMessage: (message: string) => {
      enqueueSnackbar(message, { variant: 'success' });
    },
  };
};

// Hook for showing loading states with error recovery
export const useErrorRecovery = () => {
  const { handleError, showErrorMessage } = useGlobalErrorHandler();

  const withErrorRecovery = useCallback(
    async <T>(
      operation: () => Promise<T>,
      context?: string,
      options?: {
        showError?: boolean;
        customErrorMessage?: string;
        onError?: (error: Error) => void;
      },
    ): Promise<T | null> => {
      try {
        return await operation();
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));

        if (options?.showError !== false) {
          if (options?.customErrorMessage) {
            showErrorMessage(options.customErrorMessage);
          } else {
            handleError(err, context);
          }
        }

        if (options?.onError) {
          options.onError(err);
        }

        return null;
      }
    },
    [handleError, showErrorMessage],
  );

  return { withErrorRecovery };
};
