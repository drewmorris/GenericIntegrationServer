// @ts-nocheck
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useCreateProfile() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: async (payload: any) => {
            const { data } = await api.post('/profiles', payload);
            return data;
        },
        onSuccess: () => {
            qc.invalidateQueries(['profiles']);
        },
    });
} 