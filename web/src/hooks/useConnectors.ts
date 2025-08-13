import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type ConnectorDefinition = {
  name: string;
  schema: Record<string, unknown> & {
    title?: string;
    properties?: Record<string, any>;
    required?: string[];
  };
};

export function useConnectorDefinitions() {
  return useQuery<ConnectorDefinition[], Error>({
    queryKey: ['connector-definitions'],
    queryFn: async () => {
      const { data } = await api.get<ConnectorDefinition[]>('/connectors/definitions');
      return data;
    },
  });
}
