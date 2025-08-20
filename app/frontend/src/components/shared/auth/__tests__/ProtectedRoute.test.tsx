import { screen, waitFor } from '@testing-library/preact';
import { renderWithAuth, testUtils } from '../../../test/utils/render';
import ProtectedRoute from '../ProtectedRoute';

// Mock window.location.href
const mockLocationHref = jest.fn();
Object.defineProperty(window, 'location', {
  value: {
    href: mockLocationHref,
  },
  writable: true,
});

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    testUtils.clearAuth();
  });

  it('shows loading spinner when authentication is loading', () => {
    // Mock loading state
    require('../../../lib/auth-store').authStore.isLoading.value = true;
    
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
  });

  it('redirects to login when user is not authenticated', async () => {
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    await waitFor(() => {
      expect(mockLocationHref).toHaveBeenCalledWith('/login');
    });
  });

  it('shows fallback content when user is not authenticated', () => {
    renderWithAuth(
      <ProtectedRoute fallback={<div>Please log in</div>}>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Please log in')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows access restricted message when user is not authenticated and no fallback', () => {
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Access Restricted')).toBeInTheDocument();
    expect(screen.getByText('Please log in to access this page')).toBeInTheDocument();
    expect(screen.getByText('Go to Login')).toBeInTheDocument();
  });

  it('renders children when user is authenticated', () => {
    testUtils.setAuthenticatedUser();
    
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('shows access denied when user role does not match required role', () => {
    testUtils.setAuthenticatedUser(); // Regular user
    
    renderWithAuth(
      <ProtectedRoute requiredRole="admin">
        <div>Admin Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.getByText("You don't have permission to access this page")).toBeInTheDocument();
    expect(screen.getByText('Required role: admin | Your role: user')).toBeInTheDocument();
  });

  it('renders children when user has required role', () => {
    testUtils.setAdminUser(); // Admin user
    
    renderWithAuth(
      <ProtectedRoute requiredRole="admin">
        <div>Admin Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('uses custom redirect URL', async () => {
    renderWithAuth(
      <ProtectedRoute redirectTo="/custom-login">
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    await waitFor(() => {
      expect(mockLocationHref).toHaveBeenCalledWith('/custom-login');
    });
  });

  it('shows go to dashboard link in access denied message', () => {
    testUtils.setAuthenticatedUser(); // Regular user
    
    renderWithAuth(
      <ProtectedRoute requiredRole="admin">
        <div>Admin Content</div>
      </ProtectedRoute>
    );
    
    const dashboardLink = screen.getByText('Go to Dashboard');
    expect(dashboardLink).toBeInTheDocument();
    expect(dashboardLink.getAttribute('href')).toBe('/dashboard');
  });

  it('handles undefined user role gracefully', () => {
    // Set authenticated user without role
    const mockAuthStore = require('../../../lib/auth-store').authStore;
    mockAuthStore.user.value = { 
      id: 'test-user-id', 
      email: 'test@example.com',
      role: undefined 
    };
    mockAuthStore.token.value = global.testUtils.mockJwtToken;
    mockAuthStore.isAuthenticated.value = true;
    
    renderWithAuth(
      <ProtectedRoute requiredRole="admin">
        <div>Admin Content</div>
      </ProtectedRoute>
    );
    
    expect(screen.getByText('Required role: admin | Your role: none')).toBeInTheDocument();
  });

  it('does not redirect when user is authenticated', async () => {
    testUtils.setAuthenticatedUser();
    
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );
    
    // Wait a bit to ensure no redirect happens
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(mockLocationHref).not.toHaveBeenCalled();
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
}); 