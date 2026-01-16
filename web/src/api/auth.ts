import { apiClient, setAuthTokens, clearAuthTokens, isAuthenticated as checkAuth } from './client';

export { checkAuth as isAuthenticated };
import type {
  RegisterRequest,
  RegisterResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  CurrentUser,
  ChangePasswordRequest,
  ChangePasswordResponse,
} from './types';

/**
 * Register a new user and organization
 */
export const register = async (data: RegisterRequest): Promise<RegisterResponse> => {
  const response = await apiClient.post<RegisterResponse>('/auth/register', data);

  // Store tokens
  setAuthTokens(response.data.access_token, response.data.refresh_token);

  // Store user data
  localStorage.setItem('user', JSON.stringify({
    user_id: response.data.user_id,
    org_id: response.data.org_id,
    email: response.data.email,
    full_name: response.data.full_name,
    role: response.data.role,
  }));

  return response.data;
};

/**
 * Login with email and password
 */
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', data);

  // Store tokens
  setAuthTokens(response.data.access_token, response.data.refresh_token);

  // Store user data
  localStorage.setItem('user', JSON.stringify({
    user_id: response.data.user_id,
    org_id: response.data.org_id,
    email: response.data.email,
    role: response.data.role,
  }));

  return response.data;
};

/**
 * Refresh access token
 */
export const refreshToken = async (data: RefreshTokenRequest): Promise<RefreshTokenResponse> => {
  const response = await apiClient.post<RefreshTokenResponse>('/auth/refresh', data);
  return response.data;
};

/**
 * Get current user information
 */
export const getCurrentUser = async (): Promise<CurrentUser> => {
  const response = await apiClient.get<CurrentUser>('/auth/me');
  return response.data;
};

/**
 * Logout user
 */
export const logout = () => {
  clearAuthTokens();
  window.location.href = '/login';
};

/**
 * Change user password
 */
export const changePassword = async (data: ChangePasswordRequest): Promise<ChangePasswordResponse> => {
  const response = await apiClient.post<ChangePasswordResponse>('/auth/change-password', data);
  return response.data;
};
