import { render as preactRender, RenderOptions } from '@testing-library/preact';
import { AuthProvider } from '../../contexts/AuthContext';
import { signal } from '@preact/signals';

// Mock auth store for testing
const mockAuthStore = {
  user: signal(null),
  token: signal(null),
  isLoading: signal(false),
  error: signal(null),
  isAuthenticated: signal(false),
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  refreshUser: jest.fn(),
  clearError: jest.fn(),
  initialize: jest.fn(),
  isAdmin: false,
  isUser: false,
  authState: {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  },
};

// Mock the auth store module
jest.mock('../../lib/auth-store', () => ({
  authStore: mockAuthStore,
}));

// Auth wrapper for testing authenticated components
const AuthWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>{children}</AuthProvider>
);

// Custom render function with auth context
export const renderWithAuth = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  return preactRender(ui, { wrapper: AuthWrapper, ...options });
};

// Mock authenticated user
const mockAuthenticatedUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  role: 'user' as const,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

// Mock admin user
const mockAdminUser = {
  id: 'test-admin-id',
  email: 'admin@example.com',
  role: 'admin' as const,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

// Test utilities
export const testUtils = {
  // Render with auth context
  renderWithAuth,
  
  // Set authenticated user
  setAuthenticatedUser: (user = mockAuthenticatedUser) => {
    mockAuthStore.user.value = user;
    mockAuthStore.token.value = global.testUtils.mockJwtToken;
    mockAuthStore.isAuthenticated.value = true;
  },
  
  // Set admin user
  setAdminUser: (user = mockAdminUser) => {
    mockAuthStore.user.value = user;
    mockAuthStore.token.value = global.testUtils.mockJwtToken;
    mockAuthStore.isAuthenticated.value = true;
  },
  
  // Clear auth
  clearAuth: () => {
    mockAuthStore.user.value = null;
    mockAuthStore.token.value = null;
    mockAuthStore.isAuthenticated.value = false;
  },
  
  // Mock API calls
  mockApiSuccess: <T,>(data: T) => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => global.testUtils.mockApiResponse(data),
    });
  },
  
  mockApiError: (message = 'API Error') => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => global.testUtils.mockApiResponse(null, false),
    });
  },
  
  // Mock WebSocket
  mockWebSocket: () => {
    const mockWs = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: 1,
    };
    (global.WebSocket as jest.Mock).mockImplementation(() => mockWs);
    return mockWs;
  },
  
  // Wait for state updates
  waitForStateUpdate: () => new Promise(resolve => setTimeout(resolve, 0)),
  
  // Mock localStorage
  mockLocalStorage: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
};

// Re-export everything from @testing-library/preact
export * from '@testing-library/preact';
export { preactRender as render };

// Make testUtils available globally
Object.assign(global.testUtils, testUtils); 