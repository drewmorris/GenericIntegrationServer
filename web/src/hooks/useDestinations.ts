/**
 * Hook for fetching destinations
 * Provides access to configured destinations for the current organization
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type Destination = {
  id: string;
  name: string;
  displayName?: string;
  config: Record<string, any>;
  status: 'active' | 'inactive' | 'error';
  createdAt: string;
  updatedAt: string;
  lastSync?: string;
  syncCount?: number;
  errorCount?: number;
  connectorCount?: number;
};

const fetchDestinations = async (): Promise<Destination[]> => {
  const response = await api.get('/destinations');
  return response.data as Destination[];
};

export const useDestinations = () => {
  const result = useQuery({
    queryKey: ['destinations'],
    queryFn: fetchDestinations,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    ...result,
    destinations: result.data || [],
  };
};
