import { useQuery } from '@tanstack/react-query';

import { api } from '../lib/api';

import type { SyncRun } from '../types';

export function useSyncRuns(profileId: string) {
  return useQuery<SyncRun[], Error>({
    queryKey: ['runs', profileId],
    queryFn: async () => {
      const { data } = await api.get<SyncRun[]>(`/sync_runs/${profileId}`);
      return data;
    },
  });
}
