/**
 * Admin API endpoints
 */

import { apiClient } from '../api-client';
import type { ApiResponse } from '../api-client';
import type {
  SystemHealth,
  BrainState,
  UserProfile,
} from './types';

export const adminApi = {
  /**
   * Get system health status
   */
  getSystemHealth: async (): Promise<ApiResponse<SystemHealth>> => {
    return apiClient.get<SystemHealth>('/api/v1/admin/system/health');
  },

  /**
   * Get brain controller state
   */
  getBrainState: async (): Promise<ApiResponse<BrainState>> => {
    return apiClient.get<BrainState>('/api/v1/admin/brain/state');
  },

  /**
   * Trigger brain controller warmup
   */
  triggerBrainWarmup: async (): Promise<ApiResponse<any>> => {
    return apiClient.post('/api/v1/admin/brain/warmup');
  },

  /**
   * Get all users (admin only)
   */
  getAllUsers: async (): Promise<ApiResponse<UserProfile[]>> => {
    return apiClient.get<UserProfile[]>('/api/v1/admin/users');
  },

  /**
   * Get user by ID (admin only)
   */
  getUserById: async (userId: string): Promise<ApiResponse<UserProfile>> => {
    return apiClient.get<UserProfile>(`/api/v1/admin/users/${userId}`);
  },

  /**
   * Update user (admin only)
   */
  updateUser: async (
    userId: string,
    data: Partial<UserProfile>
  ): Promise<ApiResponse<UserProfile>> => {
    return apiClient.put<UserProfile>(`/api/v1/admin/users/${userId}`, data);
  },

  /**
   * Deactivate user (admin only)
   */
  deactivateUser: async (userId: string): Promise<ApiResponse<void>> => {
    return apiClient.post<void>(`/api/v1/admin/users/${userId}/deactivate`);
  },

  /**
   * Get system metrics
   */
  getSystemMetrics: async (params?: {
    start_time?: string;
    end_time?: string;
  }): Promise<ApiResponse<any>> => {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : '';
    return apiClient.get(`/api/v1/admin/system/metrics${queryString}`);
  },

  /**
   * Get system logs
   */
  getSystemLogs: async (params?: {
    level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<any[]>> => {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : '';
    return apiClient.get<any[]>(`/api/v1/admin/system/logs${queryString}`);
  },

  /**
   * Restart trading engine
   */
  restartTradingEngine: async (): Promise<ApiResponse<any>> => {
    return apiClient.post('/api/v1/admin/trading-engine/restart');
  },

  /**
   * Get trading engine status
   */
  getTradingEngineStatus: async (): Promise<ApiResponse<any>> => {
    return apiClient.get('/api/v1/admin/trading-engine/status');
  },

  /**
   * Get continuous learning status
   */
  getContinuousLearningStatus: async (): Promise<ApiResponse<any>> => {
    return apiClient.get('/api/v1/admin/continuous-learning/status');
  },

  /**
   * Trigger model retraining
   */
  triggerModelRetraining: async (): Promise<ApiResponse<any>> => {
    return apiClient.post('/api/v1/admin/continuous-learning/retrain');
  },
};
