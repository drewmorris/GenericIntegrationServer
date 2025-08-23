/**
 * Hook for fetching destination performance metrics
 * Provides historical performance data and analytics
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type PerformanceMetric = {
  timestamp: string;
  responseTime: number;
  successRate: number;
  errorRate: number;
  throughput: number;
};

export type DestinationMetrics = {
  destinationId: string;
  period: '1h' | '24h' | '7d' | '30d';
  metrics: PerformanceMetric[];
  summary: {
    avgResponseTime: number;
    totalRequests: number;
    successfulRequests: number;
    failedRequests: number;
    uptime: number;
  };
};

const fetchDestinationMetrics = async (
  destinationId: string,
  period: string = '24h',
): Promise<DestinationMetrics> => {
  const response = await api.get(`/destinations/${destinationId}/metrics`, {
    params: { period },
  });
  return response.data as DestinationMetrics;
};

export const useDestinationMetrics = (
  destinationId: string,
  period: '1h' | '24h' | '7d' | '30d' = '24h',
) => {
  return useQuery({
    queryKey: ['destination-metrics', destinationId, period],
    queryFn: () => fetchDestinationMetrics(destinationId, period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 15 * 60 * 1000, // 15 minutes
  });
};
