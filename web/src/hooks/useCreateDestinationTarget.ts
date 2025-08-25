/**
 * Hook for creating new destination targets
 * Handles destination target creation with proper error handling and cache updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { DestinationTarget } from './useDestinations';

export type CreateDestinationTargetRequest = {
  name: string;
  display_name: string;
  config: Record<string, any>;
};

const createDestinationTarget = async (
  data: CreateDestinationTargetRequest,
): Promise<DestinationTarget> => {
  const response = await api.post('/targets/', data);
  return response.data as DestinationTarget;
};

export const useCreateDestinationTarget = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDestinationTarget,
    onSuccess: (newTarget) => {
      // Update the destinations cache with the new target
      queryClient.setQueryData(['destinations'], (old: DestinationTarget[] | undefined) => {
        return old ? [...old, newTarget] : [newTarget];
      });

      // Invalidate related queries to refresh UI
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
      void queryClient.invalidateQueries({ queryKey: ['sync-monitor-stats'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
    onError: (error) => {
      console.error('Failed to create destination target:', error);
    },
  });
};
