// @ts-nocheck
import { useProfiles } from './useProfiles';

export function useDashboardStats() {
    const { data: profiles } = useProfiles();
    const totalProfiles = profiles?.length ?? 0;
    return { totalProfiles };
} 