import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";

type ProtectedRouteProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading" role="status" aria-live="polite">
        <span>Loading account…</span>
      </div>
    );
  }

  if (!user) {
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
}

export default ProtectedRoute;

