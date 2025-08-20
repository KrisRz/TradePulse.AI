import { fireEvent, screen, waitFor } from '@testing-library/preact';
import { renderWithAuth, testUtils } from '../../../test/utils/render';
import LoginForm from '../LoginForm';

// Mock the auth store
jest.mock('../../../lib/auth-store');

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    testUtils.clearAuth();
  });

  it('renders login form correctly', () => {
    renderWithAuth(<LoginForm />);
    
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('displays validation errors for empty fields', async () => {
    renderWithAuth(<LoginForm />);
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('displays validation error for invalid email', async () => {
    renderWithAuth(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('displays validation error for short password', async () => {
    renderWithAuth(<LoginForm />);
    
    const passwordInput = screen.getByLabelText(/password/i);
    fireEvent.change(passwordInput, { target: { value: '123' } });
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
    });
  });

  it('clears validation errors when user starts typing', async () => {
    renderWithAuth(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    // Trigger validation error
    fireEvent.click(submitButton);
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });

    // Start typing to clear error
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    
    await waitFor(() => {
      expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument();
    });
  });

  it('calls login function with correct credentials', async () => {
    const mockLogin = jest.fn().mockResolvedValue(true);
    const mockOnSuccess = jest.fn();
    
    // Mock the auth store login method
    require('../../../lib/auth-store').authStore.login = mockLogin;
    
    renderWithAuth(<LoginForm onSuccess={mockOnSuccess} />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('displays error message when login fails', async () => {
    const mockLogin = jest.fn().mockResolvedValue(false);
    const errorMessage = 'Invalid credentials';
    
    // Mock the auth store
    const mockAuthStore = require('../../../lib/auth-store').authStore;
    mockAuthStore.login = mockLogin;
    mockAuthStore.error = { value: errorMessage };
    
    renderWithAuth(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/login failed/i)).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('shows loading state during login', async () => {
    const mockLogin = jest.fn().mockImplementation(() => new Promise(resolve => setTimeout(() => resolve(true), 100)));
    
    // Mock the auth store
    const mockAuthStore = require('../../../lib/auth-store').authStore;
    mockAuthStore.login = mockLogin;
    mockAuthStore.isLoading = { value: true };
    
    renderWithAuth(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);

    expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });

  it('shows switch to register link when provided', () => {
    const mockOnSwitchToRegister = jest.fn();
    
    renderWithAuth(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />);
    
    const switchLink = screen.getByText(/sign up here/i);
    expect(switchLink).toBeInTheDocument();
    
    fireEvent.click(switchLink);
    expect(mockOnSwitchToRegister).toHaveBeenCalled();
  });

  it('dismisses error when dismiss button is clicked', async () => {
    const mockClearError = jest.fn();
    
    // Mock the auth store with error
    const mockAuthStore = require('../../../lib/auth-store').authStore;
    mockAuthStore.error = { value: 'Login failed' };
    mockAuthStore.clearError = mockClearError;
    
    renderWithAuth(<LoginForm />);
    
    const dismissButton = screen.getByText(/dismiss/i);
    fireEvent.click(dismissButton);
    
    expect(mockClearError).toHaveBeenCalled();
  });
}); 