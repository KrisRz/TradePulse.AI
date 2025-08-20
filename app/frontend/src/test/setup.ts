import '@testing-library/jest-dom';
// TODO: Fix ES module issue with @testing-library/preact
// import { configure } from '@testing-library/preact';

// Configure testing library
// configure({
//   // Custom queries timeout
//   asyncUtilTimeout: 5000,
//   
//   // Test ID attribute
//   testIdAttribute: 'data-testid',
//   
//   // Custom render options
//   renderOptions: {
//     wrapper: ({ children }) => children,
//   },
// });

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock window.IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock window.location
const mockLocation = {
  href: 'http://localhost:3000',
  origin: 'http://localhost:3000',
  protocol: 'http:',
  host: 'localhost:3000',
  hostname: 'localhost',
  port: '3000',
  pathname: '/',
  search: '',
  hash: '',
  assign: jest.fn(),
  replace: jest.fn(),
  reload: jest.fn(),
};

// Delete the existing location property and redefine it
delete (window as any).location;
window.location = mockLocation as any;

// Mock console methods to reduce noise in tests
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

// Suppress jsdom navigation warning and other test noise
console.error = (...args: any[]) => {
  if (
    args[0] && 
    ((typeof args[0] === 'object' && args[0].message && args[0].message.includes('Not implemented: navigation')) ||
     (typeof args[0] === 'string' && 
      (args[0].includes('Warning: ReactDOM.render is no longer supported') ||
       args[0].includes('Warning: An invalid form control') ||
       args[0].includes('Warning: validateDOMNesting'))))
  ) {
    return;
  }
  originalConsoleError.apply(console, args);
};



console.warn = (...args: any[]) => {
  // Suppress specific warnings that are expected in tests
  if (
    args[0]?.includes?.('Warning: Component') ||
    args[0]?.includes?.('Warning: React.createFactory')
  ) {
    return;
  }
  originalConsoleWarn.apply(console, args);
};

// Mock fetch API
global.fetch = jest.fn();

// Mock WebSocket
(global as any).WebSocket = jest.fn().mockImplementation(() => ({
  close: jest.fn(),
  send: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: 1,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
}));

// Mock import.meta
Object.defineProperty(global, 'import', {
  value: {
    meta: {
      env: {
        DEV: true,
        PROD: false,
        MODE: 'test',
      },
    },
  },
});

// Global test utilities
(global as any).testUtils = {
  // Mock API responses
  mockApiResponse: <T>(data: T, success = true) => ({
    success,
    data,
    message: success ? 'Success' : 'Error',
    timestamp: new Date().toISOString(),
  }),
  
  // Mock user data
  mockUser: {
    id: 'test-user-id',
    email: 'test@example.com',
    role: 'user' as const,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  
  // Mock admin user
  mockAdmin: {
    id: 'test-admin-id',
    email: 'admin@example.com',
    role: 'admin' as const,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  
  // Mock portfolio data
  mockPortfolio: {
    id: 'test-portfolio-id',
    userId: 'test-user-id',
    balance: 10000,
    totalValue: 10500,
    totalPnL: 500,
    totalPnLPercent: 5.0,
    updatedAt: new Date().toISOString(),
  },
  
  // Mock JWT token
  mockJwtToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoidXNlciIsImV4cCI6MTcwMDAwMDAwMCwiaWF0IjoxNjAwMDAwMDAwLCJqdGkiOiJ0ZXN0LWp0aS1pZCJ9.signature',
  
  // Wait for async updates
  waitForAsync: () => new Promise(resolve => setTimeout(resolve, 0)),
};

// Types for global test utilities
declare global {
  var testUtils: {
    mockApiResponse: <T>(data: T, success?: boolean) => any;
    mockUser: any;
    mockAdmin: any;
    mockPortfolio: any;
    mockJwtToken: string;
    waitForAsync: () => Promise<void>;
  };
} 