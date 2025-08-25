/**
 * Hook for updating destination targets
 * Handles destination target configuration updates with optimistic updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { DestinationTarget } from './useDestinations';

export type UpdateDestinationTargetRequest = {
  id: string;
  config?: Record<string, any>;
  display_name?: string;
};

const updateDestinationTarget = async (
  data: UpdateDestinationTargetRequest,
): Promise<DestinationTarget> => {
  const response = await api.put(`/targets/${data.id}`, {
    config: data.config,
    display_name: data.display_name,
  });
  return response.data as DestinationTarget;
};

export const useUpdateDestinationTarget = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateDestinationTarget,
    onSuccess: (updatedTarget) => {
      // Update the destinations cache with the updated target
      queryClient.setQueryData(['destinations'], (old: DestinationTarget[] | undefined) => {
        return old
          ? old.map((dest) => (dest.id === updatedTarget.id ? updatedTarget : dest))
          : [updatedTarget];
      });

      // Invalidate related queries
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
    onError: (error) => {
      console.error('Failed to update destination target:', error);
    },
  });
};

// Export alias for backwards compatibility
export { useUpdateDestinationTarget as useUpdateDestination };
