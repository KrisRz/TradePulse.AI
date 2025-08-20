import { useEffect, useState } from 'preact/hooks';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../ui/LoadingSpinner';
import type { UserRole } from '../../types/auth';

interface ProtectedRouteProps {
  children: preact.ComponentChildren;
  requiredRole?: UserRole;
  fallback?: preact.ComponentChildren;
  redirectTo?: string;
}

export default function ProtectedRoute({
  children,
  requiredRole,
  fallback,
  redirectTo = '/login'
}: ProtectedRouteProps) {
  const [isClient, setIsClient] = useState(false);

  // Handle client-side hydration
  useEffect(() => {
    setIsClient(true);
  }, []);

  // During SSR, just render loading state
  if (!isClient) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  // Now we're on the client side, safe to use useAuth
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    // Redirect if not authenticated
    if (!isLoading && !isAuthenticated) {
      window.location.href = redirectTo;
    }
  }, [isAuthenticated, isLoading, redirectTo]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Show fallback if not authenticated
  if (!isAuthenticated) {
    return fallback ? (
      <>{fallback}</>
    ) : (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
              Access Restricted
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Please log in to access this page
            </p>
            <div className="mt-4">
              <a
                href="/login"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Go to Login
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Check role-based access
  if (requiredRole && user?.role !== requiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-red-500">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900 dark:text-white">
              Access Denied
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              You don't have permission to access this page
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
              Required role: {requiredRole} | Your role: {user?.role || 'none'}
            </p>
            <div className="mt-4">
              <a
                href="/dashboard"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Go to Dashboard
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // User is authenticated and authorized
  return <>{children}</>;
} 