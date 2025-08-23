/**
 * Hook for deleting destinations
 * Handles destination deletion with proper error handling and cache updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

const deleteDestination = async (destinationId: string): Promise<void> => {
  await api.delete(`/destinations/${destinationId}`);
};

export const useDeleteDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDestination,
    onSuccess: (_, destinationId) => {
      // Remove from destinations cache
      queryClient.setQueryData(['destinations'], (old: Array<{ id: string }> | undefined) => {
        return old ? old.filter((dest) => dest.id !== destinationId) : [];
      });

      // Invalidate related queries
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
      void queryClient.invalidateQueries({ queryKey: ['destination-health'] });
      void queryClient.invalidateQueries({ queryKey: ['destination-metrics'] });
    },
    onError: (error) => {
      console.error('Failed to delete destination:', error);
    },
  });
};
