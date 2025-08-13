import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type DestinationDefinition = {
  name: string;
  schema: Record<string, unknown> & {
    title?: string;
    properties?: Record<string, any>;
    required?: string[];
    uiSchema?: Record<string, any>;
  };
};

export function useDestinationDefinitions() {
  return useQuery<DestinationDefinition[], Error>({
    queryKey: ['destination-definitions'],
    queryFn: async () => {
      const { data } = await api.get<DestinationDefinition[]>('/destinations/definitions');
      return data;
    },
  });
}
