import { createContext } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { useContext } from 'preact/compat';
import { authStore } from '../lib/auth-store';
import { getSecurityConfig } from '../config/environments';
import type { User, AuthState, LoginRequest, RegisterRequest } from '../types/auth';

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<boolean>;
  register: (userData: RegisterRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  isAdmin: boolean;
  isUser: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: preact.ComponentChildren;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  });

  // Token refresh interval (15 minutes)
  const TOKEN_REFRESH_INTERVAL = 15 * 60 * 1000;

  // Subscribe to auth store changes
  useEffect(() => {
    const updateAuthState = () => {
      if (authStore.authState?.value) {
        setAuthState(authStore.authState.value);
      }
    };

    // Initial state
    updateAuthState();

    // Set up periodic token refresh
    let refreshInterval: number | null = null;

    if (authStore.isAuthenticated?.value) {
      refreshInterval = setInterval(async () => {
        if (authStore.isAuthenticated?.value) {
          try {
            await authStore.refreshUser();
          } catch (error) {
            console.error('Token refresh failed:', error);
            await authStore.logout();
          }
        }
      }, TOKEN_REFRESH_INTERVAL);
    }

    // Set up listeners for auth store changes - with safety checks
    const unsubscribeUser = authStore.user?.subscribe?.(updateAuthState);
    const unsubscribeToken = authStore.token?.subscribe?.(updateAuthState);
    const unsubscribeLoading = authStore.isLoading?.subscribe?.(updateAuthState);
    const unsubscribeError = authStore.error?.subscribe?.(updateAuthState);

    // Cleanup
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
      unsubscribeUser?.();
      unsubscribeToken?.();
      unsubscribeLoading?.();
      unsubscribeError?.();
    };
  }, []);

  // Session management - check token validity on app start
  useEffect(() => {
    const checkTokenValidity = async () => {
      if (authStore.token?.value) {
        try {
          await authStore.refreshUser();
        } catch (error) {
          console.warn('Token validation failed, logging out:', error);
          await authStore.logout();
        }
      }
    };

    checkTokenValidity();
  }, []);

  // Listen for storage changes (multi-tab support)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      // Unified token storage key ('token') from config/environments.ts
      if (e.key === getSecurityConfig().tokenStorageKey && e.newValue === null) {
        // Token was removed in another tab
        authStore.logout();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const contextValue: AuthContextType = {
    ...authState,
    login: async (credentials: LoginRequest) => {
      const result = await authStore.login(credentials.email, credentials.password);
      return result.success;
    },
    register: async (userData: RegisterRequest) => {
      const result = await authStore.register(userData.username, userData.email, userData.password);
      return result.success;
    },
    logout: async () => {
      authStore.logout();
    },
    refreshUser: async () => {
      await authStore.refreshUser();
    },
    clearError: () => {
      authStore.clearError();
    },
    isAdmin: authStore.isAdmin || false,
    isUser: authStore.isUser || false,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;