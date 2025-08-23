/**
 * Hook for creating connector-credential pairs
 * Handles CC-Pair creation with proper error handling and cache updates
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export type CreateConnectorCredentialPairRequest = {
  connector_source: string;
  credential_id: string;
  destination_target_id: string;
  name: string;
  sync_settings?: Record<string, any>;
};

export type ConnectorCredentialPair = {
  id: string;
  connector_source: string;
  credential_id: string;
  destination_target_id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  sync_settings: Record<string, any>;
  createdAt: string;
  updatedAt: string;
};

const createConnectorCredentialPair = async (
  data: CreateConnectorCredentialPairRequest,
): Promise<ConnectorCredentialPair> => {
  const response = await api.post('/cc-pairs', data);
  return response.data as ConnectorCredentialPair;
};

export const useCreateConnectorCredentialPair = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createConnectorCredentialPair,
    onSuccess: (newPair) => {
      // Update the cc-pairs cache
      queryClient.setQueryData(['cc-pairs'], (old: ConnectorCredentialPair[] | undefined) => {
        return old ? [...old, newPair] : [newPair];
      });

      // Invalidate related queries
      void queryClient.invalidateQueries({ queryKey: ['cc-pairs'] });
    },
    onError: (error) => {
      console.error('Failed to create connector-credential pair:', error);
    },
  });
};
