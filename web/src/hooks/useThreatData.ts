import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface ThreatData {
  threatId: string;
  description: string;
  severity: string;
  timestamp: string;
}

interface Anomaly {
  anomalyId: string;
  userId: string;
  anomalyScore: number;
  timestamp: string;
}

interface PolicyVersion {
  versionId: string;
  policyId: string;
  version: number;
  createdAt: string;
}

const fetchThreats = async (orgId: string, timeRange: string): Promise<ThreatData[]> => {
  const response = await apiClient.get<ThreatData[]>(`/dashboard/threats`, {
    params: { org_id: orgId, time_range: timeRange },
  });
  return response.data;
};

const fetchAnomalies = async (orgId: string, userId?: string): Promise<Anomaly[]> => {
  const response = await apiClient.get<Anomaly[]>(`/ml/anomaly/list`, {
    params: { org_id: orgId, ...(userId && { user_id: userId }) },
  });
  return response.data;
};

const fetchPolicyVersions = async (policyId: string): Promise<PolicyVersion[]> => {
  const response = await apiClient.get<PolicyVersion[]>(`/policies/${policyId}/versions`);
  return response.data;
};

const createPolicyVersion = async (data: { policyId: string; description?: string }): Promise<PolicyVersion> => {
  const response = await apiClient.post<PolicyVersion>(
    `/policies/${data.policyId}/versions`,
    { description: data.description }
  );
  return response.data;
};

export const useThreatData = (orgId: string, timeRange: string) => {
  return useQuery({
    queryKey: ['threats', orgId, timeRange],
    queryFn: () => fetchThreats(orgId, timeRange),
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000,
  });
};

export const useAnomalyData = (orgId: string, userId?: string) => {
  return useQuery({
    queryKey: ['anomalies', orgId, userId],
    queryFn: () => fetchAnomalies(orgId, userId),
    enabled: !!orgId,
  });
};

export const usePolicyVersions = (policyId: string) => {
  return useQuery({
    queryKey: ['policyVersions', policyId],
    queryFn: () => fetchPolicyVersions(policyId),
  });
};

export const useCreatePolicyVersion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { policyId: string; description?: string }) => createPolicyVersion(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['policyVersions', variables.policyId]
      });
    },
  });
};