import { apiClient } from './client';
import type { Policy, CreatePolicyRequest, UpdatePolicyRequest, TestPolicyRequest, DeployPolicyRequest } from './types';

/**
 * Get list of policies
 */
export const getPolicies = async (params?: {
  workspace_id?: string;
  policy_type?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}): Promise<{ policies: Policy[]; total: number; page: number; page_size: number }> => {
  const response = await apiClient.get('/policies', { params });
  return response.data;
};

/**
 * Get single policy by ID
 */
export const getPolicy = async (policyId: string): Promise<Policy> => {
  const response = await apiClient.get(`/policies/${policyId}`);
  return response.data;
};

/**
 * Create new policy
 */
export const createPolicy = async (data: CreatePolicyRequest): Promise<Policy> => {
  const response = await apiClient.post('/policies', data);
  return response.data;
};

/**
 * Update existing policy
 */
export const updatePolicy = async (policyId: string, data: UpdatePolicyRequest): Promise<Policy> => {
  const response = await apiClient.patch(`/policies/${policyId}`, data);
  return response.data;
};

/**
 * Delete policy
 */
export const deletePolicy = async (policyId: string): Promise<void> => {
  await apiClient.delete(`/policies/${policyId}`);
};

/**
 * Test policy against sample input
 */
export const testPolicy = async (policyId: string, data: TestPolicyRequest): Promise<{
  matched: boolean;
  match_details: any;
  action_taken: string;
  redacted_output: string | null;
  explanation: string;
}> => {
  const response = await apiClient.post(`/policies/${policyId}/test`, data);
  return response.data;
};

/**
 * Deploy policy with canary rollout
 */
export const deployPolicy = async (policyId: string, data: DeployPolicyRequest): Promise<{
  policy_id: string;
  test_percentage: number;
  deployed_at: string;
  message: string;
}> => {
  const response = await apiClient.post(`/policies/${policyId}/deploy`, data);
  return response.data;
};

/**
 * Rollback policy to parent version
 */
export const rollbackPolicy = async (policyId: string): Promise<Policy> => {
  const response = await apiClient.post(`/policies/${policyId}/rollback`);
  return response.data;
};
