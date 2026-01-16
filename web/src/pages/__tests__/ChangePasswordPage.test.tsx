import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChangePasswordPage } from '../ChangePasswordPage';
import * as authApi from '@/api/auth';

// Mock the auth API
vi.mock('@/api/auth', () => ({
  changePassword: vi.fn(),
}));

describe('ChangePasswordPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create a new QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Mock timers for redirect delays
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const renderChangePasswordPage = (initialUrl = '/change-password') => {
    return render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          </Routes>
        </QueryClientProvider>
      </BrowserRouter>,
      { initialEntries: [initialUrl] } as any
    );
  };

  describe('Required Password Change Flow', () => {
    it('shows warning when password change is required', () => {
      // Render with ?required=true query param
      renderChangePasswordPage('/change-password?required=true');

      // Should show the required warning
      expect(screen.getByText(/your temporary password must be changed/i)).toBeInTheDocument();

      // Should show required title
      expect(screen.getByText('Change Your Password')).toBeInTheDocument();

      // Should show required description
      expect(screen.getByText(/for security reasons, you must change your temporary password/i)).toBeInTheDocument();
    });

    it('hides cancel button when password change is required', () => {
      renderChangePasswordPage('/change-password?required=true');

      // Cancel button should NOT be present
      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    });

    it('shows update password UI when not required', () => {
      renderChangePasswordPage('/change-password');

      // Should NOT show the required warning
      expect(screen.queryByText(/your temporary password must be changed/i)).not.toBeInTheDocument();

      // Should show optional title
      expect(screen.getByText('Update Password')).toBeInTheDocument();

      // Should show optional description
      expect(screen.getByText(/create a new password for your account/i)).toBeInTheDocument();
    });

    it('shows cancel button when password change is optional', () => {
      renderChangePasswordPage('/change-password');

      // Cancel button should be present
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('validates required fields', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Submit empty form
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText('Current password is required')).toBeInTheDocument();
      });
    });

    it('validates password minimum length', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter short password
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'Short1');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show length validation error
      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
      });
    });

    it('validates password contains uppercase letter', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter password without uppercase
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'lowercase123');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show uppercase validation error
      await waitFor(() => {
        expect(screen.getByText(/password must contain at least one uppercase letter/i)).toBeInTheDocument();
      });
    });

    it('validates password contains lowercase letter', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter password without lowercase
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'UPPERCASE123');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show lowercase validation error
      await waitFor(() => {
        expect(screen.getByText(/password must contain at least one lowercase letter/i)).toBeInTheDocument();
      });
    });

    it('validates password contains digit', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter password without digit
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'NoDigitsHere');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show digit validation error
      await waitFor(() => {
        expect(screen.getByText(/password must contain at least one digit/i)).toBeInTheDocument();
      });
    });

    it('validates password confirmation matches', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter valid new password
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'ValidPass123');

      // Enter different confirm password
      const confirmPasswordInput = screen.getByLabelText(/confirm new password/i);
      await user.type(confirmPasswordInput, 'DifferentPass123');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show match validation error
      await waitFor(() => {
        expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
      });
    });

    it('accepts valid password form data', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock successful password change
      vi.mocked(authApi.changePassword).mockResolvedValue({
        success: true,
        message: 'Password changed successfully',
      });

      renderChangePasswordPage('/change-password');

      // Fill in valid form data
      const currentPasswordInput = screen.getByLabelText(/current password/i);
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm new password/i);

      await user.type(currentPasswordInput, 'OldPass123');
      await user.type(newPasswordInput, 'NewValidPass123');
      await user.type(confirmPasswordInput, 'NewValidPass123');

      // Submit
      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should call API with correct data
      await waitFor(() => {
        expect(authApi.changePassword).toHaveBeenCalledWith({
          current_password: 'OldPass123',
          new_password: 'NewValidPass123',
          confirm_password: 'NewValidPass123',
        });
      });
    });
  });

  describe('Password Strength Indicator', () => {
    it('shows weak password strength', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter weak password (only lowercase and short)
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'weak');

      // Should show weak indicator
      await waitFor(() => {
        expect(screen.getByText(/password strength: weak/i)).toBeInTheDocument();
      });
    });

    it('shows medium password strength', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter medium strength password
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'Medium123');

      // Should show medium indicator
      await waitFor(() => {
        expect(screen.getByText(/password strength: medium/i)).toBeInTheDocument();
      });
    });

    it('shows strong password strength', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Enter strong password (long, with all character types)
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      await user.type(newPasswordInput, 'VeryStrongPass123!');

      // Should show strong indicator
      await waitFor(() => {
        expect(screen.getByText(/password strength: strong/i)).toBeInTheDocument();
      });
    });

    it('does not show strength indicator when field is empty', () => {
      renderChangePasswordPage('/change-password');

      // Password field is empty by default
      // Should NOT show strength indicator
      expect(screen.queryByText(/password strength:/i)).not.toBeInTheDocument();
    });
  });

  describe('Password Requirements Display', () => {
    it('displays password requirements', () => {
      renderChangePasswordPage('/change-password');

      // Should show all requirements
      expect(screen.getByText(/password must contain:/i)).toBeInTheDocument();
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
      expect(screen.getByText(/one uppercase letter/i)).toBeInTheDocument();
      expect(screen.getByText(/one lowercase letter/i)).toBeInTheDocument();
      expect(screen.getByText(/one number/i)).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('shows loading state during submission', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock slow API response
      vi.mocked(authApi.changePassword).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ success: true, message: 'Success' }), 1000))
      );

      renderChangePasswordPage('/change-password');

      // Fill and submit form
      await user.type(screen.getByLabelText(/current password/i), 'OldPass123');
      await user.type(screen.getByLabelText(/^new password$/i), 'NewValidPass123');
      await user.type(screen.getByLabelText(/confirm new password/i), 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/changing password.../i)).toBeInTheDocument();
      });

      // Button should be disabled
      expect(submitButton).toBeDisabled();
    });

    it('shows success message after successful submission', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock successful password change
      vi.mocked(authApi.changePassword).mockResolvedValue({
        success: true,
        message: 'Password changed successfully',
      });

      renderChangePasswordPage('/change-password');

      // Fill and submit form
      await user.type(screen.getByLabelText(/current password/i), 'OldPass123');
      await user.type(screen.getByLabelText(/^new password$/i), 'NewValidPass123');
      await user.type(screen.getByLabelText(/confirm new password/i), 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/password changed successfully/i)).toBeInTheDocument();
      });

      // Should show redirecting message
      expect(screen.getByText(/redirecting to dashboard.../i)).toBeInTheDocument();
    });

    it('redirects to dashboard after successful submission', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock successful password change
      vi.mocked(authApi.changePassword).mockResolvedValue({
        success: true,
        message: 'Password changed successfully',
      });

      renderChangePasswordPage('/change-password');

      // Fill and submit form
      await user.type(screen.getByLabelText(/current password/i), 'OldPass123');
      await user.type(screen.getByLabelText(/^new password$/i), 'NewValidPass123');
      await user.type(screen.getByLabelText(/confirm new password/i), 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Wait for success message
      await waitFor(() => {
        expect(screen.getByText(/password changed successfully/i)).toBeInTheDocument();
      });

      // Fast-forward time by 2 seconds (redirect delay)
      vi.advanceTimersByTime(2000);

      // Should redirect to dashboard
      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
      });
    });

    it('shows error message on submission failure', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock API error
      const errorMessage = 'Current password is incorrect';
      vi.mocked(authApi.changePassword).mockRejectedValue({
        response: {
          data: {
            detail: errorMessage,
          },
        },
      });

      renderChangePasswordPage('/change-password');

      // Fill and submit form
      await user.type(screen.getByLabelText(/current password/i), 'WrongPass123');
      await user.type(screen.getByLabelText(/^new password$/i), 'NewValidPass123');
      await user.type(screen.getByLabelText(/confirm new password/i), 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });

      // Form should still be editable
      expect(submitButton).not.toBeDisabled();
    });

    it('disables form inputs during submission', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock slow API response
      vi.mocked(authApi.changePassword).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ success: true, message: 'Success' }), 1000))
      );

      renderChangePasswordPage('/change-password');

      const currentPasswordInput = screen.getByLabelText(/current password/i);
      const newPasswordInput = screen.getByLabelText(/^new password$/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm new password/i);

      // Fill and submit form
      await user.type(currentPasswordInput, 'OldPass123');
      await user.type(newPasswordInput, 'NewValidPass123');
      await user.type(confirmPasswordInput, 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // All inputs should be disabled during submission
      await waitFor(() => {
        expect(currentPasswordInput).toBeDisabled();
        expect(newPasswordInput).toBeDisabled();
        expect(confirmPasswordInput).toBeDisabled();
      });
    });
  });

  describe('Cancel Button', () => {
    it('navigates to dashboard when cancel is clicked', async () => {
      const user = userEvent.setup({ delay: null });
      renderChangePasswordPage('/change-password');

      // Click cancel button
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Should navigate to dashboard
      await waitFor(() => {
        expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
      });
    });

    it('disables cancel button during submission', async () => {
      const user = userEvent.setup({ delay: null });

      // Mock slow API response
      vi.mocked(authApi.changePassword).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ success: true, message: 'Success' }), 1000))
      );

      renderChangePasswordPage('/change-password');

      // Fill and submit form
      await user.type(screen.getByLabelText(/current password/i), 'OldPass123');
      await user.type(screen.getByLabelText(/^new password$/i), 'NewValidPass123');
      await user.type(screen.getByLabelText(/confirm new password/i), 'NewValidPass123');

      const submitButton = screen.getByRole('button', { name: /change password/i });
      await user.click(submitButton);

      // Cancel button should be disabled during submission
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await waitFor(() => {
        expect(cancelButton).toBeDisabled();
      });
    });
  });

  describe('UI Elements', () => {
    it('displays lock icon in header', () => {
      renderChangePasswordPage('/change-password');

      // Lock icon should be present
      const header = screen.getByText('Update Password').closest('div');
      expect(header).toBeInTheDocument();
    });

    it('shows all form fields', () => {
      renderChangePasswordPage('/change-password');

      // All form fields should be present
      expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
    });

    it('shows submit button', () => {
      renderChangePasswordPage('/change-password');

      // Submit button should be present
      expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument();
    });
  });
});
