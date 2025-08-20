/** @type {import('jest').Config} */
module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Setup files
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  
  // Module name mapping for path aliases and static assets
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@contexts/(.*)$': '<rootDir>/src/contexts/$1',
    '^@lib/(.*)$': '<rootDir>/src/lib/$1',
    '^@types/(.*)$': '<rootDir>/src/types/$1',
    '^@utils/(.*)$': '<rootDir>/src/utils/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': '<rootDir>/src/test/__mocks__/fileMock.js',
  },
  
  // File extensions
  moduleFileExtensions: ['js', 'jsx', 'ts', 'tsx', 'json'],
  
  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      useESM: true,
      tsconfig: {
        jsx: 'react-jsx',
        jsxImportSource: 'preact',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
    }],
  },
  
  // Transform ignore patterns for ES modules
  transformIgnorePatterns: [
    'node_modules/(?!(@testing-library/preact|preact|@preact|lucide-preact)/)',
  ],
  
  // Test file patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js|jsx)',
    '<rootDir>/src/**/?(*.)(test|spec).(ts|tsx|js|jsx)',
  ],
  
  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.{ts,tsx,js,jsx}',
    '!src/**/*.d.ts',
    '!src/test/**',
    '!src/**/__tests__/**',
    '!src/**/*.stories.*',
    '!src/**/*.config.*',
    '!src/**/index.ts',
  ],
  
  // Coverage thresholds
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  
  // Coverage reporting
  coverageReporters: ['text', 'lcov', 'html'],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/', 
    '<rootDir>/dist/',
    '<rootDir>/src/test/e2e/',  // Exclude Playwright tests
  ],
  
  // Clear mocks automatically
  clearMocks: true,
  
  // Restore mocks automatically
  restoreMocks: true,
  
  // Verbose output
  verbose: true,
  

  
  // ESM support
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  
  // Test timeout
  testTimeout: 10000,
  
  // Error handling
  errorOnDeprecated: true,
  
  // Watch plugins
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname',
  ],
}; 