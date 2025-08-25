/**
 * Hook for deleting destinations
 * Handles destination deletion with proper error handling and cache updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

const deleteDestinationTarget = async (destinationId: string): Promise<void> => {
  await api.delete(`/targets/${destinationId}`);
};

export const useDeleteDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDestinationTarget,
    onSuccess: (_, destinationId) => {
      // Remove from destinations cache
      queryClient.setQueryData(['destinations'], (old: Array<{ id: string }> | undefined) => {
        return old ? old.filter((dest) => dest.id !== destinationId) : [];
      });

      // Invalidate related queries
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      void queryClient.invalidateQueries({ queryKey: ['sync-monitor-stats'] });
    },
    onError: (error) => {
      console.error('Failed to delete destination target:', error);
    },
  });
};
