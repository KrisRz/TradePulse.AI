/**
 * Authentication API endpoints
 */

import { apiClient } from '../api-client';
import type { ApiResponse } from '../api-client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfile,
} from './types';

export const authApi = {
  /**
   * Login with email and password
   */
  login: async (
    email: string,
    password: string
  ): Promise<ApiResponse<LoginResponse>> => {
    const response = await apiClient.post<LoginResponse>(
      '/api/v1/auth/login',
      { email, password } as LoginRequest,
      { skipAuth: true }
    );

    // Store token if login successful
    if (response.success && response.data?.access_token) {
      apiClient.setAuthToken(response.data.access_token);
    }

    return response;
  },

  /**
   * Register new user
   */
  register: async (
    email: string,
    password: string,
    username?: string
  ): Promise<ApiResponse<RegisterResponse>> => {
    return apiClient.post<RegisterResponse>(
      '/api/v1/auth/register',
      { email, password, username } as RegisterRequest,
      { skipAuth: true }
    );
  },

  /**
   * Get current user profile
   */
  getCurrentUser: async (): Promise<ApiResponse<UserProfile>> => {
    return apiClient.get<UserProfile>('/api/v1/auth/me');
  },

  /**
   * Logout (clear local token)
   */
  logout: (): void => {
    apiClient.setAuthToken(null);
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: (): boolean => {
    return apiClient.getAuthToken() !== null;
  },

  /**
   * Manually set auth token (for restoration from localStorage)
   */
  setAuthToken: (token: string | null): void => {
    apiClient.setAuthToken(token);
  },

  /**
   * Get current auth token
   */
  getAuthToken: (): string | null => {
    return apiClient.getAuthToken();
  },
};
