import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';

import type { ConnectorProfile } from '../types';

type CreateProfileInput = {
  name: string;
  interval_minutes: number;
  [key: string]: unknown;
};

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation<ConnectorProfile, Error, CreateProfileInput>({
    mutationFn: async (payload: CreateProfileInput) => {
      const { data } = await api.post<ConnectorProfile>('/profiles', payload);
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}
