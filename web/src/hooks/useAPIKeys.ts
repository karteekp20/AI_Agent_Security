/**
 * React Query Hooks for API Keys Management
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiKeysApi } from '@/api/apiKeys';
import type { CreateAPIKeyRequest, UpdateAPIKeyRequest } from '@/api/apiKeys';

export function useAPIKeys(includeRevoked: boolean = false) {
  return useQuery({
    queryKey: ['apiKeys', includeRevoked],
    queryFn: () => apiKeysApi.listAPIKeys(includeRevoked),
  });
}

export function useCreateAPIKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateAPIKeyRequest) => apiKeysApi.createAPIKey(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });
}

export function useUpdateAPIKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ keyId, data }: { keyId: string; data: UpdateAPIKeyRequest }) =>
      apiKeysApi.updateAPIKey(keyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });
}

export function useRevokeAPIKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (keyId: string) => apiKeysApi.revokeAPIKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });
}
