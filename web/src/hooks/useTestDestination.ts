/**
 * Hook for testing destination connections
 * Provides real-time feedback on connection status and performance
 */
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';

export type TestDestinationRequest = {
  name: string;
  config: Record<string, any>;
};

export type TestDestinationResponse = {
  success: boolean;
  message: string;
  details?: {
    connectivity: boolean;
    authentication: boolean;
    performance: {
      responseTime: number;
      status: 'excellent' | 'good' | 'poor';
    };
  };
  errors?: string[];
};

const testDestination = async (data: TestDestinationRequest): Promise<TestDestinationResponse> => {
  const response = await api.post(`/destinations/${data.name}/test`, {
    config: data.config,
  });
  return response.data as TestDestinationResponse;
};

export const useTestDestination = () => {
  return useMutation({
    mutationFn: testDestination,
    onError: (error) => {
      console.error('Destination test failed:', error);
    },
  });
};
