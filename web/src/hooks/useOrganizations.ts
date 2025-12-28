/**
 * Organizations & Users Management Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

// ============================================================================
// Types
// ============================================================================

export interface Organization {
  org_id: string;
  org_name: string;
  org_slug: string;
  owner_id: string;
  created_at: string;
  settings?: Record<string, any>;
}

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  role: 'owner' | 'admin' | 'member' | 'viewer' | 'auditor';
  is_active: boolean;
  email_verified: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface InviteUserRequest {
  email: string;
  role: string;
}

// ============================================================================
// API Functions
// ============================================================================

const organizationsApi = {
  getOrganization: async (): Promise<Organization> => {
    const response = await apiClient.get<Organization>('/orgs/current');
    return response.data;
  },

  getOrganizationUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/orgs/current/users');
    return response.data;
  },

  inviteUser: async (data: InviteUserRequest): Promise<void> => {
    await apiClient.post('/orgs/current/invite', data);
  },

  removeUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/orgs/current/users/${userId}`);
  },
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Get current organization details
 */
export function useOrganization() {
  return useQuery({
    queryKey: ['organization'],
    queryFn: organizationsApi.getOrganization,
  });
}

/**
 * Get organization users
 */
export function useOrganizationUsers() {
  return useQuery({
    queryKey: ['organization-users'],
    queryFn: organizationsApi.getOrganizationUsers,
  });
}

/**
 * Invite user to organization
 */
export function useInviteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: organizationsApi.inviteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-users'] });
    },
  });
}

/**
 * Remove user from organization
 */
export function useRemoveUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: organizationsApi.removeUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-users'] });
    },
  });
}
