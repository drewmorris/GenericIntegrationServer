/**
 * Hook for creating new destinations
 * Handles destination creation with proper error handling and optimistic updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export type CreateDestinationRequest = {
  name: string;
  config: Record<string, any>;
  description?: string;
};

export type Destination = {
  id: string;
  name: string;
  config: Record<string, any>;
  description?: string;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'inactive' | 'error';
};

const createDestination = async (data: CreateDestinationRequest): Promise<Destination> => {
  const response = await api.post('/destinations', data);
  return response.data as Destination;
};

export const useCreateDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDestination,
    onSuccess: (newDestination) => {
      // Update the destinations cache
      queryClient.setQueryData(['destinations'], (old: Destination[] | undefined) => {
        return old ? [...old, newDestination] : [newDestination];
      });

      // Invalidate related queries
      void queryClient.invalidateQueries({ queryKey: ['destinations'] });
    },
    onError: (error) => {
      console.error('Failed to create destination:', error);
    },
  });
};
