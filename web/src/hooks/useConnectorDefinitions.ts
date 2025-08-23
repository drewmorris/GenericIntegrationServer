/**
 * Hook for fetching available connector definitions
 * Provides type-safe access to connector metadata and configuration schemas
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type ConnectorDefinition = {
  source: string;
  name: string;
  description: string;
  auth_type: 'oauth' | 'static' | 'none';
  category: string;
};

const fetchConnectorDefinitions = async (): Promise<ConnectorDefinition[]> => {
  const response = await api.get('/connectors/definitions');
  return response.data as ConnectorDefinition[];
};

export const useConnectorDefinitions = () => {
  return useQuery({
    queryKey: ['connector-definitions'],
    queryFn: fetchConnectorDefinitions,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });
};
