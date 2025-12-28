import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import * as authApi from '@/api/auth';
import type { RegisterRequest, LoginRequest } from '@/api/types';

/**
 * Hook to get current user
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    retry: false,
    enabled: authApi.isAuthenticated(),
  });
}

/**
 * Hook to handle user registration
 */
export function useRegister() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: () => {
      // Invalidate and refetch current user
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      // Navigate to dashboard
      navigate('/dashboard');
    },
  });
}

/**
 * Hook to handle user login
 */
export function useLogin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: () => {
      // Invalidate and refetch current user
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      // Navigate to dashboard
      navigate('/dashboard');
    },
  });
}

/**
 * Hook to handle user logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      authApi.logout();
    },
    onSuccess: () => {
      // Clear all queries
      queryClient.clear();
    },
  });
}

/**
 * Hook to check if user is authenticated
 */
export function useIsAuthenticated() {
  return authApi.isAuthenticated();
}
