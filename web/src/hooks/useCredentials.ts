import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export type Credential = {
    id: string;
    organization_id: string;
    user_id: string;
    connector_name: string;
    provider_key: string;
};

export function useCredentials(params: { organization_id?: string; user_id?: string; connector_name?: string }) {
    return useQuery<Credential[], Error>({
        queryKey: ['credentials', params],
        queryFn: async () => {
            const { data } = await api.get<Credential[]>('/credentials', { params });
            return data;
        },
    });
} 