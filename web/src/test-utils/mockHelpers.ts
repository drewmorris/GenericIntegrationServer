/**
 * Test utility helpers for creating proper React Query mocks
 * Provides type-safe mock implementations that satisfy TypeScript interfaces
 */

import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import { vi } from 'vitest';

/**
 * Creates a properly typed mock UseQueryResult (simplified version)
 */
export function createMockQueryResult<TData = unknown, TError = Error>(
  overrides: Partial<UseQueryResult<TData, TError>> = {},
): any {
  return {
    data: overrides.data ?? undefined,
    error: overrides.error ?? null,
    isError: overrides.isError ?? false,
    isPending: overrides.isPending ?? overrides.isLoading ?? false,
    isLoading: overrides.isLoading ?? false,
    isLoadingError: false,
    isRefetchError: false,
    isSuccess: overrides.isSuccess ?? (!overrides.isError && !overrides.isLoading),
    status: overrides.isLoading ? 'pending' : overrides.isError ? 'error' : 'success',
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    fetchStatus: overrides.isLoading ? 'fetching' : 'idle',
    isFetched: !overrides.isLoading,
    isFetchedAfterMount: !overrides.isLoading,
    isFetching: overrides.isLoading ?? false,
    isInitialLoading: overrides.isLoading ?? false,
    isPlaceholderData: false,
    isRefetching: false,
    isStale: false,
    refetch: vi.fn(),
    promise: Promise.resolve(overrides.data),
    ...overrides,
  };
}

/**
 * Creates a properly typed mock UseMutationResult (simplified version)
 */
export function createMockMutationResult<TData = unknown, TError = Error, TVariables = void>(
  overrides: Partial<UseMutationResult<TData, TError, TVariables>> = {},
): any {
  return {
    data: overrides.data ?? undefined,
    error: overrides.error ?? null,
    isError: overrides.isError ?? false,
    isIdle: overrides.isIdle ?? true,
    isPending: overrides.isPending ?? false,
    isSuccess: overrides.isSuccess ?? false,
    status: overrides.status ?? 'idle',
    variables: overrides.variables ?? undefined,
    failureCount: 0,
    failureReason: null,
    isPaused: false,
    mutate: overrides.mutate ?? vi.fn(),
    mutateAsync: overrides.mutateAsync ?? vi.fn(),
    reset: vi.fn(),
    submittedAt: 0,
    ...overrides,
  };
}
