import { signal } from '@preact/signals';
import { getEnvironmentConfig } from '@/config/environments';

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
      const config = getEnvironmentConfig();
      const apiUrl = `${config.api.base}/api/v1/auth/login`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token;
        
        console.log('🔐 Auth Store: Raw API response:', data);
        
        // Create user object from API response
        const user = {
          id: data.user_id,
          email: data.email,
          name: data.email.split('@')[0], // Extract username from email
          role: data.is_admin ? 'admin' : 'user', // Convert is_admin to role
          is_admin: data.is_admin // Keep original field too
        };

        console.log('🔐 Auth Store: Created user object:', user);

        if (typeof window !== 'undefined') {
          console.log('🔐 Auth Store: Setting localStorage - token:', token);
          console.log('🔐 Auth Store: Setting localStorage - user:', user);
          localStorage.setItem('auth_token', token);
          localStorage.setItem('user_data', JSON.stringify(user));
          console.log('🔐 Auth Store: ✅ localStorage updated successfully');
          console.log('🔐 Auth Store: Verify token saved:', localStorage.getItem('auth_token'));
          console.log('🔐 Auth Store: Verify user saved:', localStorage.getItem('user_data'));
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
        const error = await response.json();
        const errorMsg = error.detail || 'Login failed';
        
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
      const config = getEnvironmentConfig();
      const apiUrl = `${config.api.base}/api/v1/auth/register`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: name, email, password })
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token;
        
        // Create user object from API response
        const user = {
          id: data.user_id,
          email: data.email,
          name: data.email.split('@')[0],
          role: data.is_admin ? 'admin' : 'user'
        };

        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
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

        return { success: true };
      } else {
        const error = await response.json();
        const errorMsg = error.detail || 'Registration failed';
        
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

    isLoadingSignal.value = true;

    try {
      const config = getEnvironmentConfig();
      const apiUrl = `${config.api.base}/api/v1/auth/me`;
      
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        const user = {
          id: data.user_id,
          email: data.email,
          name: data.username || data.email.split('@')[0],
          role: data.is_admin ? 'admin' : 'user'
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
        // Token is invalid
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