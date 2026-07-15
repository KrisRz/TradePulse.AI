/**
 * Application Configuration
 * Centralized configuration for API endpoints and environment settings
 */

// Environment detection
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

// API Base URLs
const API_BASE_URL = isDevelopment 
  ? 'http://localhost:9002'
  : import.meta.env.PUBLIC_API_URL || 'https://hi3b3e4y7a.execute-api.eu-west-2.amazonaws.com/production';

// API Configuration
export const API_CONFIG = {
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer enterprise_admin_token', // TODO: Make dynamic
  },
} as const;

// API Endpoints
export const ENDPOINTS = {
  // Health
  health: '/api/health',
  
  // Auth
  auth: {
    login: '/api/auth/login',
    register: '/api/auth/register',
    logout: '/api/auth/logout',
  },
  
  // Admin
  admin: {
    users: '/api/admin/users',
    systemStatus: '/api/admin/system-status',
    virtualPortfolio: '/api/admin/virtual-portfolio',
    virtualActivePositions: '/api/portfolio/virtual/positions',
    closedPositions: '/api/admin/closed-positions',
    signalLogs: '/api/admin/signal-logs',
    tradingMonitor: '/api/admin/trading-monitor',
    aiModels: '/api/admin/ai-models',
    analytics: '/api/admin/analytics-overview',
    notifications: {
      channels: '/api/admin/notification-channels',
      logs: '/api/admin/notification-logs',
      settings: '/api/admin/notification-settings',
    },
  },
  
  // Live Data
  live: {
    bitcoinPrice: '/api/live/bitcoin-price',
  },
  
  // Trading
  trading: {
    execute: '/api/trading/execute',
    positions: '/api/trading/positions',
  },
} as const;

// Application Settings
export const APP_CONFIG = {
  name: 'TradePulse.AI',
  version: '1.0.0',
  refreshInterval: 30000, // 30 seconds
  maxRetries: 3,
  isDevelopment,
  isProduction,
} as const;

// Helper function to build full API URL
export function buildApiUrl(endpoint: string): string {
  return `${API_CONFIG.baseURL}${endpoint}`;
}

// Helper function to get API headers with optional auth token
export function getApiHeaders(authToken?: string): Record<string, string> {
  const headers = { ...API_CONFIG.headers };
  
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }
  
  return headers;
}

export default {
  API_CONFIG,
  ENDPOINTS,
  APP_CONFIG,
  buildApiUrl,
  getApiHeaders,
};