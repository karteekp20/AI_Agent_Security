/**
 * API Keys Management API Client
 */

import { apiClient } from './client';

export interface APIKey {
  key_id: string;
  org_id: string;
  workspace_id?: string;
  key_prefix: string;
  key_name?: string;
  scopes: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  is_active: boolean;
  last_used_at?: string;
  expires_at?: string;
  created_by?: string;
  created_at: string;
  revoked_at?: string;
}

export interface CreateAPIKeyRequest {
  key_name: string;
  workspace_id?: string;
  scopes?: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  expires_at?: string;
}

export interface CreatedAPIKeyResponse {
  key_id: string;
  api_key: string; // Full key shown once
  key_prefix: string;
  key_name?: string;
  org_id: string;
  workspace_id?: string;
  scopes: string[];
  created_at: string;
  warning: string;
}

export interface UpdateAPIKeyRequest {
  key_name?: string;
  scopes?: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  is_active?: boolean;
}

export interface APIKeyListResponse {
  api_keys: APIKey[];
  total: number;
}

export const apiKeysApi = {
  /**
   * List all API keys
   */
  listAPIKeys: async (includeRevoked: boolean = false): Promise<APIKeyListResponse> => {
    const params = new URLSearchParams();
    if (includeRevoked) params.append('include_revoked', 'true');

    const response = await apiClient.get<APIKeyListResponse>(`/api-keys?${params.toString()}`);
    return response.data;
  },

  /**
   * Create new API key
   */
  createAPIKey: async (request: CreateAPIKeyRequest): Promise<CreatedAPIKeyResponse> => {
    const response = await apiClient.post<CreatedAPIKeyResponse>('/api-keys', request);
    return response.data;
  },

  /**
   * Get API key details
   */
  getAPIKey: async (keyId: string): Promise<APIKey> => {
    const response = await apiClient.get<APIKey>(`/api-keys/${keyId}`);
    return response.data;
  },

  /**
   * Update API key
   */
  updateAPIKey: async (keyId: string, request: UpdateAPIKeyRequest): Promise<APIKey> => {
    const response = await apiClient.patch<APIKey>(`/api-keys/${keyId}`, request);
    return response.data;
  },

  /**
   * Revoke API key
   */
  revokeAPIKey: async (keyId: string): Promise<void> => {
    await apiClient.delete(`/api-keys/${keyId}`);
  },
};
