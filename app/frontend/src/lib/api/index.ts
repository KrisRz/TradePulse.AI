/**
 * TradePulse.AI API Client
 *
 * Centralized API client with environment-aware routing.
 * Only the auth module remains here; the former portfolio/trading/analytics/admin
 * modules were dead code calling non-existent backend routes and were removed.
 * Use `apiClient` from '../api-client' directly for other endpoints.
 *
 * @example
 * ```typescript
 * const response = await api.auth.login('user@example.com', 'password');
 * if (response.success) {
 *   console.log('Token:', response.data.access_token);
 * }
 * ```
 */

// Export the core client
export { apiClient, ApiClient } from '../api-client';
export type { ApiResponse } from '../api-client';

// Export API modules
export { authApi } from './auth';

// Export all types
export * from './types';

// Convenience default export
import { authApi } from './auth';

export const api = {
  auth: authApi,
};

export default api;
