/**
 * Trading API endpoints
 */

import { apiClient } from '../api-client';
import type { ApiResponse } from '../api-client';
import type {
  TradingSignal,
  ExecuteTradeRequest,
  ExecuteTradeResponse,
  TradingSession,
} from './types';

export const tradingApi = {
  /**
   * Get current trading signals
   */
  getSignals: async (params?: {
    symbol?: string;
    min_confidence?: number;
  }): Promise<ApiResponse<TradingSignal[]>> => {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : '';
    return apiClient.get<TradingSignal[]>(`/api/v1/signals${queryString}`);
  },

  /**
   * Get signal for specific symbol
   */
  getSignalBySymbol: async (
    symbol: string
  ): Promise<ApiResponse<TradingSignal>> => {
    return apiClient.get<TradingSignal>(`/api/v1/signals/${symbol}`);
  },

  /**
   * Execute a trade
   */
  executeTrade: async (
    trade: ExecuteTradeRequest
  ): Promise<ApiResponse<ExecuteTradeResponse>> => {
    return apiClient.post<ExecuteTradeResponse>('/api/v1/trades/execute', trade);
  },

  /**
   * Get trading history
   */
  getTradeHistory: async (params?: {
    portfolio_id?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<ApiResponse<any[]>> => {
    const queryString = params
      ? `?${new URLSearchParams(params as any).toString()}`
      : '';
    return apiClient.get<any[]>(`/api/v1/trades/history${queryString}`);
  },

  /**
   * Get active trading session
   */
  getActiveSession: async (): Promise<ApiResponse<TradingSession>> => {
    return apiClient.get<TradingSession>('/api/v1/trading/session/active');
  },

  /**
   * Start new trading session
   */
  startSession: async (params?: {
    strategy?: string;
  }): Promise<ApiResponse<TradingSession>> => {
    return apiClient.post<TradingSession>('/api/v1/trading/session/start', params);
  },

  /**
   * End trading session
   */
  endSession: async (
    sessionId: string
  ): Promise<ApiResponse<TradingSession>> => {
    return apiClient.post<TradingSession>(
      `/api/v1/trading/session/${sessionId}/end`
    );
  },

  /**
   * Get session statistics
   */
  getSessionStats: async (
    sessionId: string
  ): Promise<ApiResponse<any>> => {
    return apiClient.get(`/api/v1/trading/session/${sessionId}/stats`);
  },
};
