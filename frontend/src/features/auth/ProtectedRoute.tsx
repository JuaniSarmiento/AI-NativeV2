import { Navigate } from 'react-router-dom';
import { useAuthStore } from './store';
import type { UserRole } from './types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: UserRole | UserRole[];
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const userRole = useAuthStore((s) => s.user?.role);

  if (isLoading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[var(--color-surface)]">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-neutral-300)] border-t-[var(--color-accent-600)]" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && userRole) {
    const allowed = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!allowed.includes(userRole)) {
      return (
        <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-[var(--color-surface)] px-6">
          <span className="text-[5rem] font-bold leading-none tracking-tighter text-[var(--color-neutral-200)]">
            403
          </span>
          <p className="mt-3 text-[0.9375rem] text-[var(--color-text-secondary)]">
            No tenes permisos para acceder a esta pagina.
          </p>
        </div>
      );
    }
  }

  return <>{children}</>;
}
