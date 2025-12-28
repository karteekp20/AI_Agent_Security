import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as policiesApi from '@/api/policies';
import type { CreatePolicyRequest, UpdatePolicyRequest, TestPolicyRequest, DeployPolicyRequest } from '@/api/types';

/**
 * Hook to fetch policies list
 */
export function usePolicies(params?: {
  workspace_id?: string;
  policy_type?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ['policies', params],
    queryFn: () => policiesApi.getPolicies(params),
  });
}

/**
 * Hook to fetch single policy
 */
export function usePolicy(policyId: string) {
  return useQuery({
    queryKey: ['policy', policyId],
    queryFn: () => policiesApi.getPolicy(policyId),
    enabled: !!policyId,
  });
}

/**
 * Hook to create policy
 */
export function useCreatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreatePolicyRequest) => policiesApi.createPolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

/**
 * Hook to update policy
 */
export function useUpdatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ policyId, data }: { policyId: string; data: UpdatePolicyRequest }) =>
      policiesApi.updatePolicy(policyId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', variables.policyId] });
    },
  });
}

/**
 * Hook to delete policy
 */
export function useDeletePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (policyId: string) => policiesApi.deletePolicy(policyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

/**
 * Hook to test policy
 */
export function useTestPolicy() {
  return useMutation({
    mutationFn: ({ policyId, data }: { policyId: string; data: TestPolicyRequest }) =>
      policiesApi.testPolicy(policyId, data),
  });
}

/**
 * Hook to deploy policy
 */
export function useDeployPolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ policyId, data }: { policyId: string; data: DeployPolicyRequest }) =>
      policiesApi.deployPolicy(policyId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', variables.policyId] });
    },
  });
}

/**
 * Hook to rollback policy
 */
export function useRollbackPolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (policyId: string) => policiesApi.rollbackPolicy(policyId),
    onSuccess: (_, policyId) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', policyId] });
    },
  });
}
