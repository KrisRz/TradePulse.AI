/**
 * Portfolio API endpoints
 */

import { apiClient } from '../api-client';
import type { ApiResponse } from '../api-client';
import type {
  Portfolio,
  Position,
  CreatePortfolioRequest,
} from './types';

export const portfolioApi = {
  /**
   * Get all portfolios for current user
   */
  getAll: async (): Promise<ApiResponse<Portfolio[]>> => {
    return apiClient.get<Portfolio[]>('/api/v1/portfolio');
  },

  /**
   * Get single portfolio by ID
   */
  getById: async (portfolioId: string): Promise<ApiResponse<Portfolio>> => {
    return apiClient.get<Portfolio>(`/api/v1/portfolio/${portfolioId}`);
  },

  /**
   * Create new portfolio
   */
  create: async (
    data: CreatePortfolioRequest
  ): Promise<ApiResponse<Portfolio>> => {
    return apiClient.post<Portfolio>('/api/v1/portfolio', data);
  },

  /**
   * Update portfolio
   */
  update: async (
    portfolioId: string,
    data: Partial<CreatePortfolioRequest>
  ): Promise<ApiResponse<Portfolio>> => {
    return apiClient.put<Portfolio>(`/api/v1/portfolio/${portfolioId}`, data);
  },

  /**
   * Delete portfolio
   */
  delete: async (portfolioId: string): Promise<ApiResponse<void>> => {
    return apiClient.delete<void>(`/api/v1/portfolio/${portfolioId}`);
  },

  /**
   * Get all positions in a portfolio
   */
  getPositions: async (
    portfolioId: string
  ): Promise<ApiResponse<Position[]>> => {
    return apiClient.get<Position[]>(
      `/api/v1/portfolio/${portfolioId}/positions`
    );
  },

  /**
   * Get portfolio performance metrics
   */
  getPerformance: async (
    portfolioId: string
  ): Promise<ApiResponse<any>> => {
    return apiClient.get(`/api/v1/portfolio/${portfolioId}/performance`);
  },

  /**
   * Get portfolio history
   */
  getHistory: async (
    portfolioId: string,
    params?: { start_date?: string; end_date?: string }
  ): Promise<ApiResponse<any>> => {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : '';
    return apiClient.get(
      `/api/v1/portfolio/${portfolioId}/history${queryString}`
    );
  },
};
