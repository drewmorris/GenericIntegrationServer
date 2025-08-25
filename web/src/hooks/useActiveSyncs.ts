import { useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';
import type { IndexAttempt } from '../types';

export function useActiveSyncs(refreshInterval: number = 5000) {
  return useQuery<IndexAttempt[], Error>({
    queryKey: ['active-syncs'],
    queryFn: async () => {
      try {
        const { data } = await api.get<IndexAttempt[]>('/cc-pairs/active-syncs');
        return data || [];
      } catch (error: any) {
        // Handle empty state gracefully - return empty array instead of throwing
        if (error?.response?.status === 422 || error?.response?.status === 404) {
          return [];
        }
        throw error;
      }
    },
    refetchInterval: refreshInterval, // Poll every 5 seconds for real-time updates
    refetchIntervalInBackground: true, // Keep polling even when tab is not active
    refetchOnWindowFocus: true, // Refresh when user returns to tab
    retry: (failureCount, error: any) => {
      // Don't retry on authentication or validation errors
      if (error?.response?.status >= 400 && error?.response?.status < 500) {
        return false;
      }
      return failureCount < 2;
    },
    // Return empty array on error for better UX
    placeholderData: [],
  });
}
