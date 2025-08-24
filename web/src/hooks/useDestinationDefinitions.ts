/**
 * Hook for fetching available destination definitions
 * Provides type-safe access to destination metadata and configuration schemas
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type DestinationDefinition = {
  name: string;
  displayName: string;
  description: string;
  configSchema: Record<string, any>;
  authType: 'static' | 'oauth' | 'none';
  features: string[];
  category: string;
  schema?: {
    title?: string;
    properties?: Record<string, any>;
    required?: string[];
  };
};

const fetchDestinationDefinitions = async (): Promise<DestinationDefinition[]> => {
  const response = await api.get('/destinations/definitions');
  return response.data as DestinationDefinition[];
};

export const useDestinationDefinitions = () => {
  return useQuery({
    queryKey: ['destination-definitions'],
    queryFn: fetchDestinationDefinitions,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};
