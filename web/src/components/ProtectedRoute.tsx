import { Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { isAuthenticated } from '@/api/client';
import { useCurrentUser } from '@/hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[]; // Optional role requirements
}

function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { data: currentUser, isLoading } = useCurrentUser();

  // Check 1: Not authenticated - redirect to login
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  // Check 2: Loading user data - show spinner
  if (isLoading) {
    return <PageLoader />;
  }

  // Check 3: Role-based access control (if roles specified)
  if (requiredRoles && requiredRoles.length > 0) {
    if (!currentUser || !requiredRoles.includes(currentUser.role)) {
      // User doesn't have required role - redirect to dashboard
      return <Navigate to="/dashboard" replace />;
    }
  }

  // Check 4: All checks passed - render children
  return <>{children}</>;
}
