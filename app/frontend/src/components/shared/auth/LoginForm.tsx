import { useState } from 'preact/hooks';
import { authStore, authActions } from '@/lib/auth-store';
import { Loader2 } from 'lucide-preact';
import type { LoginRequest } from '../../types/auth';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

export default function LoginForm({ onSuccess, onSwitchToRegister }: LoginFormProps) {
  console.log('🔐 LoginForm: Component initialized with callbacks:', { 
    hasOnSuccess: !!onSuccess, 
    hasOnSwitchToRegister: !!onSwitchToRegister 
  });
  
  const [formData, setFormData] = useState<LoginRequest>({
    email: '',
    password: '',
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const handleInputChange = (e: Event) => {
    const target = e.target as HTMLInputElement;
    const { name, value } = target;
    
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear validation error when user starts typing
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    
    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }
    
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      errors.password = 'Password must be at least 6 characters long';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    console.log('🔐 LoginForm: Submitting login for:', formData.email);
    console.log('🔐 LoginForm: Password length:', formData.password.length);
    
    const success = await authActions.login(formData.email, formData.password);
    console.log('🔐 LoginForm: Login result:', success);
    console.log('🔐 LoginForm: Login success type:', typeof success);
    console.log('🔐 LoginForm: Login success.success:', success.success);
    
    if (success.success) {
      console.log('🔐 LoginForm: Login successful, calling onSuccess callback');
      console.log('🔐 LoginForm: Current localStorage before callback:', {
        token: localStorage.getItem('auth_token'),
        userData: localStorage.getItem('user_data')
      });
      
      // Handle redirect internally since Astro props don't work reliably
      console.log('🔐 LoginForm: About to call onSuccess callback, callback exists:', !!onSuccess);
      
      if (onSuccess) {
        console.log('🔐 LoginForm: Calling onSuccess callback now...');
        onSuccess();
        console.log('🔐 LoginForm: onSuccess callback completed');
      } else {
        console.log('🔐 LoginForm: No callback provided, handling redirect internally...');
        
        // Handle redirect internally with detailed logging
        setTimeout(() => {
          const userData = localStorage.getItem('user_data');
          const authToken = localStorage.getItem('auth_token');
          
          console.log('🔐 LoginForm: Internal redirect - Auth token exists:', !!authToken);
          console.log('🔐 LoginForm: Internal redirect - User data exists:', !!userData);
          console.log('🔐 LoginForm: Internal redirect - Raw user data:', userData);
          
          if (userData) {
            try {
              const user = JSON.parse(userData);
              console.log('🔐 LoginForm: Internal redirect - Parsed user:', user);
              console.log('🔐 LoginForm: Internal redirect - User role:', user.role);
              console.log('🔐 LoginForm: Internal redirect - User is_admin:', user.is_admin);
              
              if (user.role === 'admin' || user.is_admin === true) {
                console.log('🔐 LoginForm: ✅ Internal redirect ADMIN to /admin/dashboard');
                window.location.href = '/admin/dashboard';
              } else {
                console.log('🔐 LoginForm: ✅ Internal redirect USER to /user_dashboard');
                window.location.href = '/user_dashboard';
              }
            } catch (parseError) {
              console.error('🔐 LoginForm: ❌ Error parsing user data:', parseError);
              console.log('🔐 LoginForm: Fallback redirect to /user_dashboard');
              window.location.href = '/user_dashboard';
            }
          } else {
            console.log('🔐 LoginForm: No user data, fallback redirect to /user_dashboard');
            window.location.href = '/user_dashboard';
          }
        }, 100);
      }
    } else {
      console.error('🔐 LoginForm: Login failed');
      console.error('🔐 LoginForm: Error details:', success.error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-900 dark:text-gray-100">
          Email address
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={formData.email}
          onChange={handleInputChange}
          className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
          placeholder="Enter your email"
        />
        {validationErrors.email && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.email}</p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-900 dark:text-gray-100">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={formData.password}
          onChange={handleInputChange}
          className="mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
          placeholder="Enter your password"
        />
        {validationErrors.password && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{validationErrors.password}</p>
        )}
      </div>

      {authStore.error?.value && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Login failed
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                {authStore.error?.value}
              </div>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => authActions.clearError()}
                  className="text-sm font-medium text-red-800 dark:text-red-200 hover:text-red-900 dark:hover:text-red-100"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div>
        <button
          type="submit"
          disabled={authStore.isLoading?.value}
          className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {authStore.isLoading?.value ? (
            <>
              <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </button>
      </div>

      {onSwitchToRegister && (
        <div className="text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Don't have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Sign up here
            </button>
          </p>
        </div>
      )}
    </form>
  );
} 