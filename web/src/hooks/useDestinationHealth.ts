/**
 * Hook for fetching destination health data
 * Provides real-time health monitoring and diagnostics
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type HealthMetric = {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'error';
  description: string;
  threshold?: {
    warning: number;
    error: number;
  };
};

export type HealthCheck = {
  id: string;
  name: string;
  status: 'pass' | 'warning' | 'fail';
  message: string;
  details?: string;
  lastChecked: string;
};

export type DestinationHealthData = {
  overallHealth: number;
  lastChecked: string;
  metrics: HealthMetric[];
  checks: HealthCheck[];
};

const fetchDestinationHealth = async (destinationId: string): Promise<DestinationHealthData> => {
  const response = await api.get(`/destinations/${destinationId}/health`);
  return response.data as DestinationHealthData;
};

export const useDestinationHealth = (destinationId: string) => {
  return useQuery({
    queryKey: ['destination-health', destinationId],
    queryFn: () => fetchDestinationHealth(destinationId),
    staleTime: 30 * 1000, // 30 seconds
    cacheTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Refetch every minute
  });
};
