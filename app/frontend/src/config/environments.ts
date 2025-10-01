/**
 * Professional Environment Configuration for TradePulse.AI Frontend
 * 
 * Enterprise-grade environment management with:
 * - Type-safe configuration
 * - Environment detection
 * - Feature flags
 * - API endpoints
 * - Security settings
 */

export enum Environment {
  DEVELOPMENT = 'development',
  STAGING = 'staging',
  PRODUCTION = 'production'
}

export interface ApiEndpoints {
  base: string;
  websocket: string;
  auth: string;
  trading: string;
  portfolio: string;
  admin: string;
  analytics: string;
}

export interface SecurityConfig {
  tokenStorageKey: string;
  refreshTokenKey: string;
  sessionTimeoutMinutes: number;
  maxRetryAttempts: number;
  csrfProtection: boolean;
}

export interface FeatureFlags {
  enableLiveTrading: boolean;
  enablePaperTrading: boolean;
  enableBacktesting: boolean;
  enableAdvancedCharts: boolean;
  enableNotifications: boolean;
  enableDarkMode: boolean;
  enableAnalytics: boolean;
  enableDebugMode: boolean;
}

export interface PerformanceConfig {
  apiTimeout: number;
  retryDelay: number;
  maxConcurrentRequests: number;
  cacheTimeout: number;
  enableServiceWorker: boolean;
  enableCompression: boolean;
}

export interface EnvironmentConfig {
  environment: Environment;
  api: ApiEndpoints;
  security: SecurityConfig;
  features: FeatureFlags;
  performance: PerformanceConfig;
  debug: boolean;
  version: string;
}

// Environment-specific configurations
const configurations: Record<Environment, EnvironmentConfig> = {
  [Environment.DEVELOPMENT]: {
    environment: Environment.DEVELOPMENT,
    debug: true,
    version: '1.0.0-dev',
    api: {
      base: 'http://localhost:9002',
      websocket: 'ws://localhost:9002',
      auth: 'http://localhost:9002/api/auth',
      trading: 'http://localhost:9002/api/trading',
      portfolio: 'http://localhost:9002/api/portfolio',
      admin: 'http://localhost:9002/api/admin',
      analytics: 'http://localhost:9002/api/analytics'
    },
    security: {
      tokenStorageKey: 'tradepulse_token',
      refreshTokenKey: 'tradepulse_refresh',
      sessionTimeoutMinutes: 60,
      maxRetryAttempts: 3,
      csrfProtection: false
    },
    features: {
      enableLiveTrading: false,
      enablePaperTrading: true,
      enableBacktesting: true,
      enableAdvancedCharts: true,
      enableNotifications: true,
      enableDarkMode: true,
      enableAnalytics: true,
      enableDebugMode: true
    },
    performance: {
      apiTimeout: 30000,
      retryDelay: 1000,
      maxConcurrentRequests: 10,
      cacheTimeout: 300000, // 5 minutes
      enableServiceWorker: false,
      enableCompression: false
    }
  },

  [Environment.STAGING]: {
    environment: Environment.STAGING,
    debug: false,
    version: '1.0.0-staging',
    api: {
      base: 'https://staging-api.tradepulse.ai',
      websocket: 'wss://staging-api.tradepulse.ai',
      auth: 'https://staging-api.tradepulse.ai/api/auth',
      trading: 'https://staging-api.tradepulse.ai/api/trading',
      portfolio: 'https://staging-api.tradepulse.ai/api/portfolio',
      admin: 'https://staging-api.tradepulse.ai/api/admin',
      analytics: 'https://staging-api.tradepulse.ai/api/analytics'
    },
    security: {
      tokenStorageKey: 'tradepulse_token',
      refreshTokenKey: 'tradepulse_refresh',
      sessionTimeoutMinutes: 30,
      maxRetryAttempts: 3,
      csrfProtection: true
    },
    features: {
      enableLiveTrading: false,
      enablePaperTrading: true,
      enableBacktesting: true,
      enableAdvancedCharts: true,
      enableNotifications: true,
      enableDarkMode: true,
      enableAnalytics: true,
      enableDebugMode: false
    },
    performance: {
      apiTimeout: 20000,
      retryDelay: 1500,
      maxConcurrentRequests: 15,
      cacheTimeout: 600000, // 10 minutes
      enableServiceWorker: true,
      enableCompression: true
    }
  },

  [Environment.PRODUCTION]: {
    environment: Environment.PRODUCTION,
    debug: false,
    version: '1.0.2', // Use CloudFront domain for API requests
    api: {
      base: 'https://tradepulseai.co.uk',
      websocket: 'wss://tradepulseai.co.uk',
      auth: 'https://tradepulseai.co.uk/api/auth',
      trading: 'https://tradepulseai.co.uk/api/trading',
      portfolio: 'https://tradepulseai.co.uk/api/portfolio',
      admin: 'https://tradepulseai.co.uk/api/admin',
      analytics: 'https://tradepulseai.co.uk/api/analytics'
    },
    security: {
      tokenStorageKey: 'tradepulse_token',
      refreshTokenKey: 'tradepulse_refresh',
      sessionTimeoutMinutes: 15,
      maxRetryAttempts: 5,
      csrfProtection: true
    },
    features: {
      enableLiveTrading: true,
      enablePaperTrading: true,
      enableBacktesting: true,
      enableAdvancedCharts: true,
      enableNotifications: true,
      enableDarkMode: true,
      enableAnalytics: true,
      enableDebugMode: false
    },
    performance: {
      apiTimeout: 15000,
      retryDelay: 2000,
      maxConcurrentRequests: 20,
      cacheTimeout: 900000, // 15 minutes
      enableServiceWorker: true,
      enableCompression: true
    }
  }
};

/**
 * Detect current environment based on hostname and build mode
 */
function detectEnvironment(): Environment {
  // Server-side rendering check
  if (typeof window === 'undefined') {
    return import.meta.env.PROD ? Environment.PRODUCTION : Environment.DEVELOPMENT;
  }

  const hostname = window.location.hostname;
  
  // Production domains
  if (hostname === 'tradepulseai.co.uk' || hostname === 'app.tradepulseai.co.uk' || hostname === 'tradepulse.ai' || hostname === 'app.tradepulse.ai') {
    return Environment.PRODUCTION;
  }
  
  // Staging domains
  if (hostname.includes('staging') || hostname.includes('preview')) {
    return Environment.STAGING;
  }
  
  // Development (localhost, 127.0.0.1, etc.)
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')) {
    return Environment.DEVELOPMENT;
  }
  
  // Default based on build mode
  return import.meta.env.PROD ? Environment.PRODUCTION : Environment.DEVELOPMENT;
}

/**
 * Get current environment configuration
 */
export function getEnvironmentConfig(): EnvironmentConfig {
  const environment = detectEnvironment();
  const config = configurations[environment];
  
  // Override with environment variables if available
  if (typeof window !== 'undefined') {
    // Client-side environment variable overrides
    const envOverrides = (window as any).__TRADEPULSE_ENV__;
    if (envOverrides) {
      return { ...config, ...envOverrides };
    }
  }
  
  return config;
}

/**
 * Get current environment
 */
export function getCurrentEnvironment(): Environment {
  return detectEnvironment();
}

/**
 * Check if feature is enabled
 */
export function isFeatureEnabled(feature: keyof FeatureFlags): boolean {
  const config = getEnvironmentConfig();
  return config.features[feature];
}

/**
 * Get API endpoint for a service
 */
export function getApiEndpoint(service: keyof ApiEndpoints): string {
  const config = getEnvironmentConfig();
  return config.api[service];
}

/**
 * Check if we're in development mode
 */
export function isDevelopment(): boolean {
  return getCurrentEnvironment() === Environment.DEVELOPMENT;
}

/**
 * Check if we're in production mode
 */
export function isProduction(): boolean {
  return getCurrentEnvironment() === Environment.PRODUCTION;
}

/**
 * Get security configuration
 */
export function getSecurityConfig(): SecurityConfig {
  const config = getEnvironmentConfig();
  return config.security;
}

/**
 * Get performance configuration
 */
export function getPerformanceConfig(): PerformanceConfig {
  const config = getEnvironmentConfig();
  return config.performance;
}

// Export the current configuration as default
export const config = getEnvironmentConfig();
export default config;

