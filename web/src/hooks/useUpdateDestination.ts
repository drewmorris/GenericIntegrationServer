/**
 * Hook for updating destinations
 * Handles destination configuration updates with optimistic updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export type UpdateDestinationRequest = {
  id: string;
  config: Record<string, any>;
  displayName?: string;
};

export type Destination = {
  id: string;
  name: string;
  displayName?: string;
  config: Record<string, any>;
  status: 'active' | 'inactive' | 'error';
  createdAt: string;
  updatedAt: string;
};

const updateDestination = async (data: UpdateDestinationRequest): Promise<Destination> => {
  const response = await api.put(`/destinations/${data.id}`, {
    config: data.config,
    displayName: data.displayName,
  });
  return response.data as Destination;
};

export const useUpdateDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateDestination,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['destinations'] });

      // Snapshot the previous value
      const previousDestinations = queryClient.getQueryData(['destinations']);

      // Optimistically update
      queryClient.setQueryData(['destinations'], (old: Destination[] | undefined) => {
        return old
          ? old.map((dest) =>
              dest.id === variables.id
                ? { ...dest, config: variables.config, updatedAt: new Date().toISOString() }
                : dest,
            )
          : [];
      });

      return { previousDestinations };
    },
    onError: (error, _variables, context) => {
      // Rollback on error
      if (context?.previousDestinations) {
        queryClient.setQueryData(['destinations'], context.previousDestinations);
      }
      console.error('Failed to update destination:', error);
    },
    onSettled: () => {
      // Always refetch after error or success
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
    },
  });
};
