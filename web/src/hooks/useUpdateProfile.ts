// @ts-nocheck
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useUpdateProfile() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, payload }: { id: string; payload: any }) => {
            const { data } = await api.patch(`/profiles/${id}`, payload);
            return data;
        },
        onSuccess: () => {
            qc.invalidateQueries(['profiles']);
        },
    });
} 