/**
 * TradePulse.AI API Client
 * 
 * Centralized API client with environment-aware routing
 * Perfect for professional DevOps deployment showcase
 * 
 * @example
 * ```typescript
 * // Login
 * const response = await api.auth.login('user@example.com', 'password');
 * if (response.success) {
 *   console.log('Token:', response.data.access_token);
 * }
 * 
 * // Get portfolios
 * const portfolios = await api.portfolio.getAll();
 * if (portfolios.success) {
 *   console.log('Portfolios:', portfolios.data);
 * }
 * ```
 */

// Export the core client
export { apiClient, ApiClient } from '../api-client';
export type { ApiResponse } from '../api-client';

// Export all API modules
export { authApi } from './auth';
export { portfolioApi } from './portfolio';
export { tradingApi } from './trading';
export { analyticsApi } from './analytics';
export { adminApi } from './admin';

// Export all types
export * from './types';

// Convenience default export
import { authApi } from './auth';
import { portfolioApi } from './portfolio';
import { tradingApi } from './trading';
import { analyticsApi } from './analytics';
import { adminApi } from './admin';

export const api = {
  auth: authApi,
  portfolio: portfolioApi,
  trading: tradingApi,
  analytics: analyticsApi,
  admin: adminApi,
};

export default api;
