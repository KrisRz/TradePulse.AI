/**
 * TypeScript type definitions for TradePulse.AI API
 * 
 * Complete type safety for all API endpoints
 */

// ============================================================================
// AUTH TYPES
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username?: string;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
  username: string;
  message: string;
}

export interface UserProfile {
  user_id: string;
  email: string;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

// ============================================================================
// PORTFOLIO TYPES
// ============================================================================

export interface Portfolio {
  portfolio_id: string;
  user_id: string;
  name: string;
  description?: string;
  total_value: number;
  cash_balance: number;
  positions: Position[];
  performance: PerformanceMetrics;
  created_at: string;
  updated_at: string;
}

export interface Position {
  position_id: string;
  portfolio_id: string;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  cost_basis: number;
  opened_at: string;
  updated_at: string;
}

export interface PerformanceMetrics {
  total_return: number;
  total_return_percent: number;
  daily_return: number;
  daily_return_percent: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
}

export interface CreatePortfolioRequest {
  name: string;
  description?: string;
  initial_balance: number;
}

// ============================================================================
// TRADING TYPES
// ============================================================================

export interface TradingSignal {
  signal_id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  price: number;
  timestamp: string;
  reasoning: string;
  indicators: Record<string, number>;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  target_price?: number;
  stop_loss?: number;
}

export interface ExecuteTradeRequest {
  portfolio_id: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  order_type: 'MARKET' | 'LIMIT';
  limit_price?: number;
}

export interface ExecuteTradeResponse {
  trade_id: string;
  status: 'EXECUTED' | 'PENDING' | 'FAILED';
  executed_price?: number;
  executed_quantity?: number;
  fees: number;
  message: string;
}

export interface TradingSession {
  session_id: string;
  user_id: string;
  start_time: string;
  end_time?: string;
  status: 'ACTIVE' | 'PAUSED' | 'CLOSED';
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: number;
  strategies_used: string[];
}

// ============================================================================
// ANALYTICS TYPES
// ============================================================================

export interface MarketAnalytics {
  symbol: string;
  timestamp: string;
  price: number;
  volume: number;
  volatility: number;
  trend: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  support_levels: number[];
  resistance_levels: number[];
  technical_indicators: TechnicalIndicators;
}

export interface TechnicalIndicators {
  rsi?: number;
  macd?: {
    macd: number;
    signal: number;
    histogram: number;
  };
  moving_averages?: {
    sma_20?: number;
    sma_50?: number;
    sma_200?: number;
    ema_12?: number;
    ema_26?: number;
  };
  bollinger_bands?: {
    upper: number;
    middle: number;
    lower: number;
  };
}

export interface AILayerPrediction {
  layer: number;
  layer_name: string;
  prediction: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasoning: string;
  timestamp: string;
}

export interface ComprehensiveAnalysis {
  symbol: string;
  timestamp: string;
  market_analytics: MarketAnalytics;
  ai_predictions: AILayerPrediction[];
  final_recommendation: {
    action: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
    reasoning: string;
    risk_assessment: string;
  };
}

// ============================================================================
// ADMIN TYPES
// ============================================================================

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  timestamp: string;
  components: {
    brain_controller: ComponentHealth;
    trading_engine: ComponentHealth;
    ai_engines: Record<string, ComponentHealth>;
    database: ComponentHealth;
    market_data: ComponentHealth;
  };
  metrics: SystemMetrics;
}

export interface ComponentHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  uptime_seconds: number;
  last_check: string;
  error_count: number;
  warning_count: number;
  message?: string;
}

export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_users: number;
  active_sessions: number;
  requests_per_minute: number;
  average_response_time: number;
}

export interface BrainState {
  state_id: string;
  timestamp: string;
  confidence_level: number;
  active_strategies: string[];
  learning_progress: number;
  market_regime: 'TRENDING' | 'RANGING' | 'VOLATILE' | 'STABLE';
  performance_score: number;
  recent_decisions: any[];
}

// ============================================================================
// MARKET DATA TYPES
// ============================================================================

export interface Candlestick {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketDataRequest {
  symbol: string;
  interval: '1m' | '5m' | '15m' | '1h' | '4h' | '1d';
  limit?: number;
  start_time?: string;
  end_time?: string;
}

export interface MarketDataResponse {
  symbol: string;
  interval: string;
  data: Candlestick[];
  count: number;
}

// ============================================================================
// NOTIFICATION TYPES
// ============================================================================

export interface Notification {
  notification_id: string;
  user_id: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
}

// ============================================================================
// WEBSOCKET TYPES
// ============================================================================

export interface WebSocketMessage<T = any> {
  type: string;
  payload: T;
  timestamp: string;
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  change_24h: number;
  change_percent_24h: number;
  volume_24h: number;
  timestamp: string;
}

export interface SignalUpdate {
  signal: TradingSignal;
  applicable_portfolios: string[];
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}
