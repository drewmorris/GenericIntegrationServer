import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';

import type { ConnectorProfile } from '../types';

type UpdateProfileInput = {
  id: string;
  payload: Partial<ConnectorProfile>;
};

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation<ConnectorProfile, Error, UpdateProfileInput>({
    mutationFn: async ({ id, payload }: UpdateProfileInput) => {
      const { data } = await api.patch<ConnectorProfile>(`/profiles/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}
