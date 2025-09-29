import { signal } from '@preact/signals';
import { api } from './api';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

// Initial state
const initialState: AuthState = {
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null,
  isAuthenticated: false,
  loading: false,
  error: null
};

// Create signals
const authStateSignal = signal<AuthState>(initialState);
const userSignal = signal<User | null>(initialState.user);
const tokenSignal = signal<string | null>(initialState.token);
const isAuthenticatedSignal = signal<boolean>(initialState.isAuthenticated);
const isLoadingSignal = signal<boolean>(initialState.loading);
const errorSignal = signal<string | null>(initialState.error);

// Auth actions
export const authActions = {
  login: async (email: string, password: string) => {
    isLoadingSignal.value = true;
    errorSignal.value = null;
    
    try {
      // Use new API client
      const response = await api.auth.login(email, password);

      if (response.success && response.data) {
        const data = response.data;
        const token = data.access_token;
        
        console.log('🔐 Auth Store: Raw API response:', data);
        
        // Create user object from API response
        const user = {
          id: data.user.user_id,
          email: data.user.email,
          name: data.user.username || data.user.email.split('@')[0],
          role: data.user.is_admin ? 'admin' : 'user' as 'user' | 'admin',
          is_admin: data.user.is_admin
        };

        console.log('🔐 Auth Store: Created user object:', user);

        if (typeof window !== 'undefined') {
          console.log('🔐 Auth Store: Setting localStorage - token:', token);
          console.log('🔐 Auth Store: Setting localStorage - user:', user);
          localStorage.setItem('auth_token', token);
          localStorage.setItem('user_data', JSON.stringify(user));
          console.log('🔐 Auth Store: ✅ localStorage updated successfully');
        }
        
        // Update all signals
        userSignal.value = user;
        tokenSignal.value = token;
        isAuthenticatedSignal.value = true;
        isLoadingSignal.value = false;
        errorSignal.value = null;
        
        authStateSignal.value = {
          user,
          token,
          isAuthenticated: true,
          loading: false,
          error: null
        };

        return { success: true };
      } else {
        const errorMsg = response.error?.message || 'Login failed';
        
        isLoadingSignal.value = false;
        errorSignal.value = errorMsg;
        
        authStateSignal.value = { 
          ...authStateSignal.value, 
          loading: false, 
          error: errorMsg 
        };
        
        return { success: false, error: errorMsg };
      }
    } catch (error) {
      const errorMessage = 'Network error';
      
      isLoadingSignal.value = false;
      errorSignal.value = errorMessage;
      
      authStateSignal.value = { 
        ...authStateSignal.value, 
        loading: false, 
        error: errorMessage 
      };
      
      return { success: false, error: errorMessage };
    }
  },

  register: async (name: string, email: string, password: string) => {
    isLoadingSignal.value = true;
    errorSignal.value = null;
    
    try {
      // Use new API client
      const response = await api.auth.register(email, password, name);

      if (response.success && response.data) {
        // Note: Register endpoint returns different structure than login
        // Typically need to login after register, but if it returns token:
        const data = response.data;
        
        // For now, registration just creates account - need to login after
        isLoadingSignal.value = false;
        
        return { 
          success: true,
          message: 'Registration successful. Please login.'
        };
      } else {
        const errorMsg = response.error?.message || 'Registration failed';
        
        isLoadingSignal.value = false;
        errorSignal.value = errorMsg;
        
        authStateSignal.value = { 
          ...authStateSignal.value, 
          loading: false, 
          error: errorMsg 
        };
        
        return { success: false, error: errorMsg };
      }
    } catch (error) {
      const errorMessage = 'Network error';
      
      isLoadingSignal.value = false;
      errorSignal.value = errorMessage;
      
      authStateSignal.value = { 
        ...authStateSignal.value, 
        loading: false, 
        error: errorMessage 
      };
      
      return { success: false, error: errorMessage };
    }
  },

  logout: () => {
    // Clear API client token
    api.auth.logout();
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
    }
    
    // Reset all signals
    userSignal.value = null;
    tokenSignal.value = null;
    isAuthenticatedSignal.value = false;
    isLoadingSignal.value = false;
    errorSignal.value = null;
    
    authStateSignal.value = {
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false,
      error: null
    };
  },

  clearError: () => {
    errorSignal.value = null;
    authStateSignal.value = { ...authStateSignal.value, error: null };
  },

  checkAuth: async () => {
    if (typeof window === 'undefined') {
      return;
    }
    
    const token = localStorage.getItem('auth_token');
    if (!token) {
      return;
    }

    // Set token in API client
    api.auth.setAuthToken(token);

    isLoadingSignal.value = true;

    try {
      // Use new API client
      const response = await api.auth.getCurrentUser();

      if (response.success && response.data) {
        const data = response.data;
        const user = {
          id: data.user_id,
          email: data.email,
          name: data.username || data.email.split('@')[0],
          role: data.is_admin ? 'admin' : 'user' as 'user' | 'admin'
        };
        
        if (typeof window !== 'undefined') {
          localStorage.setItem('user_data', JSON.stringify(user));
        }
        
        // Update all signals
        userSignal.value = user;
        tokenSignal.value = token;
        isAuthenticatedSignal.value = true;
        isLoadingSignal.value = false;
        errorSignal.value = null;
        
        authStateSignal.value = {
          user,
          token,
          isAuthenticated: true,
          loading: false,
          error: null
        };
      } else {
        // Token is invalid - clear everything
        api.auth.logout();
        
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_data');
        }
        
        // Reset all signals
        userSignal.value = null;
        tokenSignal.value = null;
        isAuthenticatedSignal.value = false;
        isLoadingSignal.value = false;
        errorSignal.value = null;
        
        authStateSignal.value = {
          user: null,
          token: null,
          isAuthenticated: false,
          loading: false,
          error: null
        };
      }
    } catch (error) {
      isLoadingSignal.value = false;
      authStateSignal.value = { ...authStateSignal.value, loading: false };
    }
  }
};

export const authStore = {
  // Signal access
  authState: authStateSignal,
  user: userSignal,
  token: tokenSignal,
  isAuthenticated: isAuthenticatedSignal,
  isLoading: isLoadingSignal,
  error: errorSignal,
  
  // Role helpers
  get isAdmin() { return userSignal.value?.role === 'admin'; },
  get isUser() { return userSignal.value?.role === 'user'; },
  
  // Methods
  login: authActions.login,
  register: authActions.register, 
  logout: authActions.logout,
  clearError: authActions.clearError,
  refreshUser: authActions.checkAuth
};

// Initialize auth check on load (disabled for development)
// if (typeof window !== 'undefined') {
//   authActions.checkAuth();
// }