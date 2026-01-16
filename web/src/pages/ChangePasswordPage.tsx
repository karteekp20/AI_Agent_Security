import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, Loader2, Lock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { changePassword } from '@/api/auth';
import { useMutation } from '@tanstack/react-query';

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one digit'),
  confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
});

type PasswordFormData = z.infer<typeof passwordSchema>;

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isRequired = searchParams.get('required') === 'true';
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const { mutate: submitPasswordChange, isPending, error } = useMutation({
    mutationFn: changePassword,
    onSuccess: (data) => {
      setSuccessMessage(data.message);
      reset();
      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    },
  });

  const onSubmit = (data: PasswordFormData) => {
    submitPasswordChange(data);
  };

  // Password strength indicator
  const getPasswordStrength = (password: string): { strength: string; color: string } => {
    if (password.length === 0) return { strength: '', color: '' };

    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score <= 2) return { strength: 'Weak', color: 'text-destructive' };
    if (score <= 4) return { strength: 'Medium', color: 'text-yellow-600' };
    return { strength: 'Strong', color: 'text-green-600' };
  };

  const [passwordStrength, setPasswordStrength] = useState({ strength: '', color: '' });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="flex justify-center">
            <div className="p-3 bg-primary/10 rounded-full">
              <Lock className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">
            {isRequired ? 'Change Your Password' : 'Update Password'}
          </CardTitle>
          <CardDescription>
            {isRequired
              ? 'For security reasons, you must change your temporary password before continuing.'
              : 'Create a new password for your account.'
            }
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {isRequired && (
              <Alert className="border-amber-200 bg-amber-50 dark:bg-amber-950/20">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <AlertDescription className="text-amber-800 dark:text-amber-400">
                  Your temporary password must be changed before you can access the application.
                </AlertDescription>
              </Alert>
            )}

            {successMessage && (
              <Alert className="border-green-200 bg-green-50 dark:bg-green-950/20">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800 dark:text-green-400">
                  {successMessage} Redirecting to dashboard...
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>
                  {(error as any)?.response?.data?.detail || error.message || 'Failed to change password'}
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                placeholder="Enter your current password"
                {...register('current_password')}
                disabled={isPending || !!successMessage}
              />
              {errors.current_password && (
                <p className="text-sm text-destructive">{errors.current_password.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                placeholder="Enter your new password"
                {...register('new_password')}
                onChange={(e) => {
                  setPasswordStrength(getPasswordStrength(e.target.value));
                }}
                disabled={isPending || !!successMessage}
              />
              {passwordStrength.strength && (
                <p className={`text-sm ${passwordStrength.color}`}>
                  Password strength: {passwordStrength.strength}
                </p>
              )}
              {errors.new_password && (
                <p className="text-sm text-destructive">{errors.new_password.message}</p>
              )}
              <div className="text-xs text-muted-foreground space-y-1 mt-2">
                <p>Password must contain:</p>
                <ul className="list-disc list-inside space-y-0.5 ml-2">
                  <li>At least 8 characters</li>
                  <li>One uppercase letter</li>
                  <li>One lowercase letter</li>
                  <li>One number</li>
                </ul>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                placeholder="Confirm your new password"
                {...register('confirm_password')}
                disabled={isPending || !!successMessage}
              />
              {errors.confirm_password && (
                <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-2">
            <Button
              type="submit"
              className="w-full"
              disabled={isPending || !!successMessage}
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Changing Password...
                </>
              ) : successMessage ? (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Password Changed
                </>
              ) : (
                'Change Password'
              )}
            </Button>

            {!isRequired && (
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => navigate('/dashboard')}
                disabled={isPending}
              >
                Cancel
              </Button>
            )}
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
