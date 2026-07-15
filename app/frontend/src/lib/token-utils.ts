/**
 * Token Storage Utilities
 * 
 * Environment-aware token management for consistent localStorage keys
 * across local development and AWS production deployments.
 */

import { getEnvironmentConfig } from '@/config/environments';

/**
 * Get the current environment's token storage key
 * - Development: 'tradepulse_token'
 * - Production: 'tradepulse_token'
 * 
 * This ensures consistent token storage across environments
 */
export function getTokenKey(): string {
  const envConfig = getEnvironmentConfig();
  return envConfig.security.tokenStorageKey;
}

/**
 * Get auth token from localStorage (environment-aware)
 */
export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(getTokenKey());
}

/**
 * Set auth token in localStorage (environment-aware)
 */
export function setStoredToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(getTokenKey(), token);
}

/**
 * Remove auth token from localStorage (environment-aware)
 */
export function removeStoredToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(getTokenKey());
}

/**
 * Check if token exists in localStorage
 */
export function hasStoredToken(): boolean {
  return !!getStoredToken();
}

