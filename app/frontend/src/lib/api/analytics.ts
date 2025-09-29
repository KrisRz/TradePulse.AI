/**
 * Analytics & AI Engine API endpoints
 */

import { apiClient } from '../api-client';
import type { ApiResponse } from '../api-client';
import type {
  MarketAnalytics,
  ComprehensiveAnalysis,
  AILayerPrediction,
  MarketDataRequest,
  MarketDataResponse,
} from './types';

export const analyticsApi = {
  /**
   * Get comprehensive analysis for a symbol
   */
  getComprehensiveAnalysis: async (
    symbol: string
  ): Promise<ApiResponse<ComprehensiveAnalysis>> => {
    return apiClient.get<ComprehensiveAnalysis>(
      `/api/v1/analytics/comprehensive/${symbol}`
    );
  },

  /**
   * Get market analytics for a symbol
   */
  getMarketAnalytics: async (
    symbol: string
  ): Promise<ApiResponse<MarketAnalytics>> => {
    return apiClient.get<MarketAnalytics>(
      `/api/v1/analytics/market/${symbol}`
    );
  },

  /**
   * Get AI layer predictions
   */
  getAIPredictions: async (
    symbol: string
  ): Promise<ApiResponse<AILayerPrediction[]>> => {
    return apiClient.get<AILayerPrediction[]>(
      `/api/v1/analytics/ai-predictions/${symbol}`
    );
  },

  /**
   * Get market data (candlesticks)
   */
  getMarketData: async (
    params: MarketDataRequest
  ): Promise<ApiResponse<MarketDataResponse>> => {
    const queryString = new URLSearchParams(params as any).toString();
    return apiClient.get<MarketDataResponse>(
      `/api/v1/market-data/candles?${queryString}`
    );
  },

  /**
   * Get real-time price for symbol
   */
  getCurrentPrice: async (symbol: string): Promise<ApiResponse<any>> => {
    return apiClient.get(`/api/v1/market-data/price/${symbol}`);
  },

  /**
   * Get multiple symbols prices
   */
  getMultiplePrices: async (
    symbols: string[]
  ): Promise<ApiResponse<Record<string, any>>> => {
    const queryString = `symbols=${symbols.join(',')}`;
    return apiClient.get(`/api/v1/market-data/prices?${queryString}`);
  },

  /**
   * Get market overview
   */
  getMarketOverview: async (): Promise<ApiResponse<any>> => {
    return apiClient.get('/api/v1/analytics/market-overview');
  },

  /**
   * Get trending symbols
   */
  getTrendingSymbols: async (
    limit: number = 10
  ): Promise<ApiResponse<any[]>> => {
    return apiClient.get(`/api/v1/analytics/trending?limit=${limit}`);
  },
};
