import { useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';

import type { ConnectorProfile } from '../types';

export function useProfiles() {
  return useQuery<ConnectorProfile[], Error>({
    queryKey: ['profiles'],
    queryFn: async () => {
      const { data } = await api.get<ConnectorProfile[]>('/profiles');
      return data;
    },
  });
}
