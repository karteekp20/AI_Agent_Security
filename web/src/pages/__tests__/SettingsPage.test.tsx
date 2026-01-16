import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsPage } from '../SettingsPage';
import * as authHooks from '@/hooks/useAuth';
import * as orgHooks from '@/hooks/useOrganizations';
import * as apiKeyHooks from '@/hooks/useAPIKeys';

// Mock the hooks
vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('@/hooks/useOrganizations', () => ({
  useOrganization: vi.fn(),
  useOrganizationUsers: vi.fn(),
  useInviteUser: vi.fn(),
  useRemoveUser: vi.fn(),
}));

vi.mock('@/hooks/useAPIKeys', () => ({
  useAPIKeys: vi.fn(),
  useCreateAPIKey: vi.fn(),
  useRevokeAPIKey: vi.fn(),
}));

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('SettingsPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();
    mockNavigate.mockClear();

    // Create a new QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Default mock implementations
    vi.mocked(orgHooks.useOrganization).mockReturnValue({
      data: {
        org_id: 'org-123',
        org_name: 'Test Organization',
        plan: 'Pro',
        is_active: true,
        api_requests_this_month: 500,
        max_api_requests_per_month: 1000,
        created_at: '2024-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    vi.mocked(orgHooks.useOrganizationUsers).mockReturnValue({
      data: {
        users: [
          {
            user_id: 'user-1',
            email: 'owner@example.com',
            full_name: 'Owner User',
            role: 'owner',
            is_active: true,
          },
          {
            user_id: 'user-2',
            email: 'member@example.com',
            full_name: 'Member User',
            role: 'member',
            is_active: true,
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    vi.mocked(apiKeyHooks.useAPIKeys).mockReturnValue({
      data: {
        api_keys: [
          {
            key_id: 'key-1',
            key_name: 'Production Key',
            key_prefix: 'sk_live_abc123...',
            is_active: true,
            created_at: '2024-01-15T00:00:00Z',
            last_used_at: '2024-01-20T00:00:00Z',
          },
        ],
      },
      isLoading: false,
      isError: false,
      error: null,
    } as any);

    vi.mocked(orgHooks.useInviteUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(orgHooks.useRemoveUser).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(apiKeyHooks.useCreateAPIKey).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(apiKeyHooks.useRevokeAPIKey).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
  });

  const renderSettingsPage = () => {
    return render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <SettingsPage />
        </QueryClientProvider>
      </BrowserRouter>
    );
  };

  describe('User Management RBAC', () => {
    it('shows invite user form to admin users', () => {
      // Mock: Current user is admin
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Admin should see the invite form
      expect(screen.getByText('Invite User')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('user@example.com')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send invitation/i })).toBeInTheDocument();
    });

    it('shows invite user form to owner users', () => {
      // Mock: Current user is owner
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'owner-user',
          email: 'owner@example.com',
          role: 'owner',
          full_name: 'Owner User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Owner should see the invite form
      expect(screen.getByText('Invite User')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send invitation/i })).toBeInTheDocument();
    });

    it('shows permission denied message to viewer users', () => {
      // Mock: Current user is viewer
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'viewer-user',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Viewer should see permission denied message
      expect(screen.getByText(/you don't have permission to invite users/i)).toBeInTheDocument();

      // Should NOT see the invite form fields
      expect(screen.queryByPlaceholderText('John Doe')).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('user@example.com')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /send invitation/i })).not.toBeInTheDocument();
    });

    it('shows permission denied message to member users', () => {
      // Mock: Current user is member
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'member-user',
          email: 'member@example.com',
          role: 'member',
          full_name: 'Member User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Member should see permission denied message
      expect(screen.getByText(/you don't have permission to invite users/i)).toBeInTheDocument();
    });

    it('disables remove user button for non-admin users', () => {
      // Mock: Current user is viewer
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'viewer-user',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Find all delete/remove buttons (trash icons)
      const removeButtons = screen.getAllByRole('button', { name: '' }).filter(
        (btn) => btn.querySelector('svg')
      );

      // All remove buttons should be disabled for viewer
      removeButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it('enables remove user button for admin users', () => {
      // Mock: Current user is admin
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Find remove buttons (should be enabled for non-owner users)
      const teamMembersSection = screen.getByText('Team Members').closest('div');
      const removeButtons = within(teamMembersSection as HTMLElement).getAllByRole('button', { name: '' });

      // At least one remove button should be enabled (for the member user, not owner)
      const enabledButtons = removeButtons.filter((btn) => !btn.hasAttribute('disabled'));
      expect(enabledButtons.length).toBeGreaterThan(0);
    });
  });

  describe('API Keys RBAC', () => {
    it('shows create API key form to admin users', () => {
      // Mock: Current user is admin
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Admin should see the create form
      expect(screen.getByText('Create API Key')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Production API Key')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate api key/i })).toBeInTheDocument();
    });

    it('shows create API key form to owner users', () => {
      // Mock: Current user is owner
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'owner-user',
          email: 'owner@example.com',
          role: 'owner',
          full_name: 'Owner User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Owner should see the create form
      expect(screen.getByRole('button', { name: /generate api key/i })).toBeInTheDocument();
    });

    it('shows permission denied message to viewer users for API keys', () => {
      // Mock: Current user is viewer
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'viewer-user',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Viewer should see permission denied message
      expect(screen.getByText(/you don't have permission to create api keys/i)).toBeInTheDocument();

      // Should NOT see the create form
      expect(screen.queryByPlaceholderText('Production API Key')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /generate api key/i })).not.toBeInTheDocument();
    });

    it('shows permission denied message to member users for API keys', () => {
      // Mock: Current user is member
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'member-user',
          email: 'member@example.com',
          role: 'member',
          full_name: 'Member User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Member should see permission denied message
      expect(screen.getByText(/you don't have permission to create api keys/i)).toBeInTheDocument();
    });

    it('disables revoke button for non-admin users', () => {
      // Mock: Current user is viewer
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'viewer-user',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Find the API keys list section
      const apiKeysSection = screen.getByText('API Keys').closest('div');
      const revokeButtons = within(apiKeysSection as HTMLElement).getAllByRole('button', { name: '' });

      // Revoke button should be disabled for viewer
      revokeButtons.forEach((button) => {
        if (button.querySelector('svg')) {
          expect(button).toBeDisabled();
        }
      });
    });

    it('enables revoke button for admin users', () => {
      // Mock: Current user is admin
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Find the revoke button in API keys list
      const apiKeysSection = screen.getByText('API Keys').closest('div');
      const buttons = within(apiKeysSection as HTMLElement).getAllByRole('button', { name: '' });

      // At least one button should be enabled (the revoke button for active key)
      const enabledButtons = buttons.filter((btn) => !btn.hasAttribute('disabled'));
      expect(enabledButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Security Tab - Password Change', () => {
    it('shows password change section to all users', () => {
      // Mock: Current user is viewer (lowest permission)
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'viewer-user',
          email: 'viewer@example.com',
          role: 'viewer',
          full_name: 'Viewer User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Security tab
      const securityTab = screen.getByRole('button', { name: /security/i });
      userEvent.click(securityTab);

      // All users should see password change section
      expect(screen.getByText('Change Password')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument();
    });

    it('navigates to /change-password when button is clicked', async () => {
      const user = userEvent.setup();

      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'user-1',
          email: 'user@example.com',
          role: 'member',
          full_name: 'Test User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Security tab
      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      // Click the Change Password button
      const changePasswordButton = screen.getByRole('button', { name: /change password/i });
      await user.click(changePasswordButton);

      // Should navigate to /change-password
      expect(mockNavigate).toHaveBeenCalledWith('/change-password');
    });

    it('shows security recommendations', () => {
      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'user-1',
          email: 'user@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Security tab
      const securityTab = screen.getByRole('button', { name: /security/i });
      userEvent.click(securityTab);

      // Should show security recommendations
      expect(screen.getByText('Account Security')).toBeInTheDocument();
      expect(screen.getByText('Strong Password')).toBeInTheDocument();
      expect(screen.getByText('Regular Updates')).toBeInTheDocument();
      expect(screen.getByText('Temporary Passwords')).toBeInTheDocument();
    });
  });

  describe('Tab Navigation', () => {
    it('shows organization tab by default', () => {
      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'user-1',
          email: 'user@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Organization tab content should be visible
      expect(screen.getByText('Organization Information')).toBeInTheDocument();
      expect(screen.getByText('Test Organization')).toBeInTheDocument();
    });

    it('switches to users tab when clicked', async () => {
      const user = userEvent.setup();

      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Click Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      await user.click(usersTab);

      // Users tab content should be visible
      expect(screen.getByText('Team Members')).toBeInTheDocument();
    });

    it('switches to api-keys tab when clicked', async () => {
      const user = userEvent.setup();

      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Click API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      await user.click(apiKeysTab);

      // API Keys tab content should be visible
      expect(screen.getByText('Create API Key')).toBeInTheDocument();
    });

    it('switches to security tab when clicked', async () => {
      const user = userEvent.setup();

      // Mock: Current user
      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'user-1',
          email: 'user@example.com',
          role: 'member',
          full_name: 'Test User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Click Security tab
      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      // Security tab content should be visible
      expect(screen.getByText('Change Password')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('shows loading spinner while fetching organization data', () => {
      // Mock: Loading organization
      vi.mocked(orgHooks.useOrganization).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'user-1',
          email: 'user@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Should show loading spinner in organization tab
      const loaders = screen.getAllByRole('img', { hidden: true });
      expect(loaders.length).toBeGreaterThan(0);
    });

    it('shows loading spinner while fetching users', () => {
      // Mock: Loading users
      vi.mocked(orgHooks.useOrganizationUsers).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to Users tab
      const usersTab = screen.getByRole('button', { name: /users/i });
      userEvent.click(usersTab);

      // Should show loading spinner
      const loaders = screen.getAllByRole('img', { hidden: true });
      expect(loaders.length).toBeGreaterThan(0);
    });

    it('shows loading spinner while fetching API keys', () => {
      // Mock: Loading API keys
      vi.mocked(apiKeyHooks.useAPIKeys).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      vi.mocked(authHooks.useCurrentUser).mockReturnValue({
        data: {
          user_id: 'admin-user',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Admin User',
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderSettingsPage();

      // Navigate to API Keys tab
      const apiKeysTab = screen.getByRole('button', { name: /api keys/i });
      userEvent.click(apiKeysTab);

      // Should show loading spinner
      const loaders = screen.getAllByRole('img', { hidden: true });
      expect(loaders.length).toBeGreaterThan(0);
    });
  });
});
