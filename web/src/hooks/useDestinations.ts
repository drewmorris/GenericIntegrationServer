/**
 * Hook for fetching destinations
 * Provides access to configured destinations for the current organization
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type DestinationTarget = {
  id: string;
  name: string;
  display_name: string;
  displayName?: string; // For backwards compatibility
  config: Record<string, any>;
  status?: 'active' | 'inactive' | 'error';
  createdAt?: string;
  updatedAt?: string;
  created_at?: string; // API format
  updated_at?: string; // API format
  lastSync?: string;
  syncCount?: number;
  errorCount?: number;
  connectorCount?: number;
};

const fetchDestinations = async (): Promise<DestinationTarget[]> => {
  const response = await api.get('/targets/');
  return response.data as DestinationTarget[];
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
