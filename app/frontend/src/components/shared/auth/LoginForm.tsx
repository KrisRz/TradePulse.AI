import { useState } from 'preact/hooks';
import { authStore } from '@/lib/auth-store';
import type { LoginRequest } from '../../types/auth';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

export default function LoginForm({ onSuccess, onSwitchToRegister }: LoginFormProps) {
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
    const success = await authStore.login(formData);
    console.log('🔐 LoginForm: Login result:', success);
    
    if (success) {
      console.log('🔐 LoginForm: Login successful, handling redirect');
      
      // Handle redirect directly in the component
      const userData = localStorage.getItem('user_data');
      console.log('🔐 LoginForm: User data from localStorage:', userData);
      
      if (userData) {
        const user = JSON.parse(userData);
        console.log('🔐 LoginForm: Parsed user:', user);
        
        if (user.role === 'admin') {
          console.log('🔐 LoginForm: Redirecting admin to /admin/dashboard');
          window.location.href = '/admin/dashboard';
        } else {
          console.log('🔐 LoginForm: Redirecting user to /user_dashboard');
          window.location.href = '/user_dashboard';
        }
      } else {
        console.log('🔐 LoginForm: No user data, fallback to /user_dashboard');
        window.location.href = '/user_dashboard';
      }
      
      // Also call the callback if provided (for compatibility)
      onSuccess?.();
    } else {
      console.error('🔐 LoginForm: Login failed');
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

      {authStore.error.value && (
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
                {authStore.error.value}
              </div>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => authStore.clearError()}
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
          disabled={authStore.isLoading.value}
          className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {authStore.isLoading.value ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
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