# Frontend Testing Guide

This guide covers the testing setup and best practices for the TradePulse.AI frontend application.

## 🧪 Testing Stack

- **Jest** - JavaScript testing framework
- **@testing-library/preact** - Testing utilities for Preact components
- **@testing-library/jest-dom** - Custom Jest matchers for DOM testing
- **ts-jest** - TypeScript support for Jest
- **jsdom** - DOM environment for Node.js

## 📁 Test Structure

```
src/
├── test/
│   ├── __mocks__/          # Mock files for static assets
│   ├── utils/              # Testing utilities
│   ├── setup.ts            # Jest setup file
│   └── README.md           # This file
├── components/
│   └── __tests__/          # Component tests
│       ├── Component.test.tsx
│       └── Component.spec.tsx
├── lib/
│   └── __tests__/          # Utility function tests
└── contexts/
    └── __tests__/          # Context tests
```

## 🚀 Running Tests

### Basic Commands

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run tests for CI/CD
npm run test:ci

# Debug tests
npm run test:debug

# Update snapshots
npm run test:update
```

### Test Patterns

```bash
# Run specific test file
npm test -- LoginForm.test.tsx

# Run tests matching pattern
npm test -- --testNamePattern="should render"

# Run tests in specific directory
npm test -- src/components/auth

# Run tests with verbose output
npm test -- --verbose
```

## 🔧 Configuration

### Jest Configuration (`jest.config.js`)

- **Test Environment**: jsdom for DOM testing
- **Setup File**: `src/test/setup.ts`
- **Coverage**: 80% threshold for branches, functions, lines, statements
- **TypeScript**: Full TypeScript support with ts-jest
- **Path Mapping**: Supports @ aliases for imports

### Setup File (`src/test/setup.ts`)

- Configures testing-library/preact
- Mocks browser APIs (localStorage, sessionStorage, etc.)
- Global test utilities and mocks
- Console warning suppression for tests

## 🎯 Testing Best Practices

### 1. Component Testing

```typescript
import { render, screen, fireEvent } from '@testing-library/preact';
import MyComponent from '../MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles user interaction', () => {
    const handleClick = jest.fn();
    render(<MyComponent onClick={handleClick} />);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalled();
  });
});
```

### 2. Authentication Testing

```typescript
import { testUtils } from '../../test/utils/render';

describe('Protected Component', () => {
  it('shows content when user is authenticated', () => {
    testUtils.setAuthenticatedUser();
    
    testUtils.renderWithAuth(<ProtectedComponent />);
    
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
```

### 3. API Testing

```typescript
describe('API Integration', () => {
  it('handles successful API response', async () => {
    testUtils.mockApiSuccess({ data: 'test' });
    
    render(<ComponentThatCallsAPI />);
    
    await waitFor(() => {
      expect(screen.getByText('test')).toBeInTheDocument();
    });
  });
});
```

### 4. Hook Testing

```typescript
import { renderHook, act } from '@testing-library/preact';
import { useMyHook } from '../useMyHook';

describe('useMyHook', () => {
  it('returns correct initial state', () => {
    const { result } = renderHook(() => useMyHook());
    
    expect(result.current.value).toBe(0);
  });

  it('updates state correctly', () => {
    const { result } = renderHook(() => useMyHook());
    
    act(() => {
      result.current.increment();
    });
    
    expect(result.current.value).toBe(1);
  });
});
```

## 🔍 Testing Utilities

### Global Test Utils

Available via `global.testUtils`:

- `mockApiResponse<T>(data: T, success?: boolean)` - Mock API responses
- `mockUser` - Default mock user object
- `mockAdmin` - Default mock admin object
- `mockPortfolio` - Default mock portfolio object
- `mockJwtToken` - Mock JWT token
- `waitForAsync()` - Wait for async operations

### Render Utils

Available via `testUtils` from `src/test/utils/render`:

- `renderWithAuth(component)` - Render with AuthProvider
- `setAuthenticatedUser(user?)` - Set authenticated user
- `setAdminUser(user?)` - Set admin user
- `clearAuth()` - Clear authentication state
- `mockApiSuccess<T>(data: T)` - Mock successful API call
- `mockApiError(message?)` - Mock API error
- `mockWebSocket()` - Mock WebSocket connection

## 📊 Coverage Reports

### Coverage Thresholds

- **Branches**: 80%
- **Functions**: 80%
- **Lines**: 80%
- **Statements**: 80%

### Coverage Files

- `coverage/lcov-report/index.html` - HTML coverage report
- `coverage/lcov.info` - Coverage data for CI/CD
- `coverage/coverage-final.json` - JSON coverage data

### Viewing Coverage

```bash
# Generate and view coverage report
npm run test:coverage
open coverage/lcov-report/index.html
```

## 🚫 What NOT to Test

- Third-party libraries (React, Preact, etc.)
- Browser APIs (unless mocking behavior)
- CSS styling (use visual regression testing instead)
- Implementation details (focus on behavior)

## 🎭 Mocking Guidelines

### Mock External Dependencies

```typescript
// Mock entire modules
jest.mock('../lib/api', () => ({
  api: {
    login: jest.fn(),
    logout: jest.fn(),
  },
}));

// Mock specific functions
jest.mock('../lib/utils', () => ({
  ...jest.requireActual('../lib/utils'),
  formatDate: jest.fn(),
}));
```

### Mock Browser APIs

```typescript
// Mock fetch
global.fetch = jest.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
```

## 🔄 Continuous Integration

Tests run automatically on:
- Pull requests to main/develop
- Pushes to main/develop
- Changes to frontend code

### CI/CD Steps

1. **Type Checking** - `npm run type-check`
2. **Linting** - `npm run lint`
3. **Testing** - `npm run test:ci`
4. **Coverage Upload** - Codecov integration
5. **Build** - `npm run build`

## 🆘 Troubleshooting

### Common Issues

1. **Tests timeout**: Increase timeout in `jest.config.js`
2. **Module not found**: Check path mapping in `jest.config.js`
3. **Mock not working**: Ensure mock is defined before import
4. **Coverage not accurate**: Check `collectCoverageFrom` pattern

### Debug Mode

```bash
# Run tests in debug mode
npm run test:debug

# Then in Chrome DevTools:
# chrome://inspect
# Click "Open dedicated DevTools for Node"
```

## 📚 Further Reading

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Testing Library Docs](https://testing-library.com/docs/preact-testing-library/intro)
- [Jest DOM Matchers](https://github.com/testing-library/jest-dom)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library) 