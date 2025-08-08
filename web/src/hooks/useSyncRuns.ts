// @ts-nocheck
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useSyncRuns(profileId: string) {
    return useQuery(['runs', profileId], async () => {
        const { data } = await api.get(`/sync_runs/${profileId}`);
        return data as Array<{ id: string; status: string; started_at: string; finished_at?: string }>;
    });
} 