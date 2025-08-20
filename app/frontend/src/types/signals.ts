// AI Signals Types - 6-Layer Decision System

export type SignalDirection = 'BUY' | 'SELL' | 'HOLD';
export type MarketRegime = 'sideways' | 'trending_up' | 'trending_down' | 'volatile';
export type StrategyType = 'mean_reversion' | 'trend_following' | 'breakout' | 'reversal';

export interface LSTMPrediction {
  timeframe: '1h' | '4h' | '24h';
  direction: SignalDirection;
  confidence: number;
  probability_up: number;
  probability_down: number;
  model_version: string;
}

export interface ReversalSignal {
  whale_volume_detected: boolean;
  rsi_extreme: boolean;
  divergence_detected: boolean;
  momentum_shift: boolean;
  support_resistance_level: boolean;
  overall_confidence: number;
}

export interface SmartFilters {
  rsi_threshold_passed: boolean;
  volume_confirmation: boolean;
  disagreement_filter_passed: boolean;
  trend_alignment: boolean;
  risk_reward_ratio: number;
  overall_score: number;
}

export interface Signal {
  id: string;
  symbol: string;
  direction: SignalDirection;
  confidence: number;
  
  // Layer 1: Market Regime
  market_regime: MarketRegime;
  regime_confidence: number;
  
  // Layer 2: LSTM Predictions
  lstm_predictions: LSTMPrediction[];
  lstm_consensus: SignalDirection;
  lstm_confidence: number;
  
  // Layer 3: Reversal Detection
  reversal_signals: ReversalSignal;
  
  // Layer 4: Smart Filters
  smart_filters: SmartFilters;
  
  // Layer 5: Confidence Scoring
  final_confidence: number;
  risk_score: number;
  
  // Layer 6: Adaptive Hold Time & Strategy
  recommended_hold_time: number; // in minutes
  strategy_type: StrategyType;
  entry_price_range: {
    min: number;
    max: number;
    optimal: number;
  };
  
  // Additional metadata
  signal_strength: 'weak' | 'moderate' | 'strong' | 'very_strong';
  price_at_signal: number;
  volume_at_signal: number;
  created_at: string;
  expires_at?: string;
  executed: boolean;
  trade_id?: string;
}

export interface SignalFeedItem {
  signal: Signal;
  status: 'active' | 'executed' | 'expired' | 'cancelled';
  performance?: {
    entry_price: number;
    current_price: number;
    pnl: number;
    pnl_percentage: number;
    duration: number; // in minutes
  };
}

export interface SignalAnalytics {
  total_signals: number;
  signals_today: number;
  buy_signals: number;
  sell_signals: number;
  hold_signals: number;
  average_confidence: number;
  executed_signals: number;
  execution_rate: number;
  successful_signals: number;
  success_rate: number;
  average_hold_time: number;
  best_performing_signal?: Signal;
  worst_performing_signal?: Signal;
}

export interface TechnicalIndicators {
  rsi: number;
  macd: {
    macd: number;
    signal: number;
    histogram: number;
  };
  bollinger_bands: {
    upper: number;
    middle: number;
    lower: number;
  };
  sma_20: number;
  sma_50: number;
  sma_200: number;
  ema_12: number;
  ema_26: number;
  volume_sma: number;
  volume_ratio: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  volume: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  market_cap?: number;
  timestamp: string;
  technical_indicators: TechnicalIndicators;
}

// API Request/Response Types
export interface GetSignalsRequest {
  symbol?: string;
  direction?: SignalDirection;
  min_confidence?: number;
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
}

export interface GetSignalsResponse {
  signals: SignalFeedItem[];
  total_count: number;
  has_more: boolean;
  analytics: SignalAnalytics;
}

export interface CreateSignalRequest {
  symbol: string;
  direction: SignalDirection;
  confidence: number;
  strategy_type: StrategyType;
  entry_price_range: {
    min: number;
    max: number;
    optimal: number;
  };
  recommended_hold_time: number;
  notes?: string;
}

// Real-time signal updates
export interface SignalUpdate {
  signal_id: string;
  type: 'confidence_update' | 'price_update' | 'status_change' | 'expiry_warning';
  data: any;
  timestamp: string;
} 