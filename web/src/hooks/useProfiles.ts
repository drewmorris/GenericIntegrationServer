// @ts-nocheck
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useProfiles() {
    return useQuery(['profiles'], async () => {
        const { data } = await api.get('/profiles');
        return data as Array<{ id: string; name: string; source: string; interval_minutes: number }>;
    });
} 