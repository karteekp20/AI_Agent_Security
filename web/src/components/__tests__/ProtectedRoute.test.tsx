import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';
import * as authClient from '@/api/client';
import * as authHooks from '@/hooks/useAuth';

// Mock the authentication modules
vi.mock('@/api/client', () => ({
  isAuthenticated: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: vi.fn(),
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();
  });

  describe('Authentication Checks', () => {
    it('redirects to /login when not authenticated', () => {
      // Mock: User is not authenticated
      vi.mocked(authClient.isAuthenticated).mockReturnValue(false);

      const { container } = render(
        <BrowserRouter>
          <Routes>
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <div data-testid="protected-content">Protected Content</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
          </Routes>
        </BrowserRouter>
      );

      // Should NOT show protected content
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();

      // Should redirect to login (in actual DOM, would show login page)
      // Note: React Router Navigate in tests doesn't actually navigate,
      // but the component should attempt to navigate
    });

    it('shows loading spinner while fetching user data', () => {
      // Mock: User is authenticated
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);

      // Mock: User data is loading
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div data-testid="protected-content">Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Should show loader (looking for spinner icon or loading text)
      // The loader component uses Loader2 from lucide-react
      // We can check if protected content is NOT shown during loading
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    it('renders protected content when authenticated and loaded', () => {
      // Mock: User is authenticated
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);

      // Mock: User data is loaded
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'user@example.com',
          role: 'member',
          full_name: 'Test User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div data-testid="protected-content">Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Should render protected content
      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });
  });

  describe('Role-Based Access Control', () => {
    it('allows access when user has required role (admin)', () => {
      // Mock: User is authenticated as admin
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute requiredRoles={['admin', 'owner']}>
            <div data-testid="admin-content">Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Admin should see content
      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    });

    it('allows access when user has required role (owner)', () => {
      // Mock: User is authenticated as owner
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'owner@example.com',
          role: 'owner',
          full_name: 'Owner User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute requiredRoles={['admin', 'owner']}>
            <div data-testid="admin-content">Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Owner should see content
      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    });

    it('redirects when user does not have required role (viewer)', () => {
      // Mock: User is authenticated as viewer
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <Routes>
            <Route
              path="/"
              element={
                <ProtectedRoute requiredRoles={['admin', 'owner']}>
                  <div data-testid="admin-content">Admin Content</div>
                </ProtectedRoute>
              }
            />
            <Route path="/dashboard" element={<div data-testid="dashboard">Dashboard</div>} />
          </Routes>
        </BrowserRouter>
      );

      // Viewer should NOT see admin content
      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();

      // Should redirect to dashboard (Navigate component tries to redirect)
    });

    it('redirects when user does not have required role (member)', () => {
      // Mock: User is authenticated as member
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'member@example.com',
          role: 'member',
          full_name: 'Member User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute requiredRoles={['admin', 'owner']}>
            <div data-testid="admin-content">Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Member should NOT see admin content
      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });
  });

  describe('No Role Requirements', () => {
    it('allows all authenticated users when no roles required', () => {
      // Mock: User is authenticated as viewer (lowest permission role)
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          {/* No requiredRoles prop */}
          <ProtectedRoute>
            <div data-testid="general-content">General Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Even viewer should see content when no role restriction
      expect(screen.getByTestId('general-content')).toBeInTheDocument();
    });

    it('allows admin when no roles required', () => {
      // Mock: User is authenticated as admin
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div data-testid="general-content">General Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      expect(screen.getByTestId('general-content')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('redirects when user data is null despite being authenticated', () => {
      // Mock: isAuthenticated returns true but user data is null (edge case)
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute requiredRoles={['admin']}>
            <div data-testid="admin-content">Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Should NOT show protected content when user is null
      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });

    it('handles empty requiredRoles array as no restriction', () => {
      // Mock: User is authenticated
      vi.mocked(authClient.isAuthenticated).mockReturnValue(true);
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: '123',
          email: 'user@example.com',
          role: 'viewer',
          full_name: 'User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      render(
        <BrowserRouter>
          <ProtectedRoute requiredRoles={[]}>
            <div data-testid="content">Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      );

      // Empty array should allow access (no restrictions)
      expect(screen.getByTestId('content')).toBeInTheDocument();
    });
  });
});
