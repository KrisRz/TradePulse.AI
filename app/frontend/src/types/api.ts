// API Client Types

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  status: number;
}

// Standardized API Response Types (matching FastAPI backend)
export interface StandardApiResponse<T> {
  success?: boolean;
  data?: T;
  error?: string;
  message?: string;
  status?: number;
  timestamp?: string;
}

// Pagination Response
export interface PaginatedApiResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  has_next: boolean;
  has_prev: boolean;
  total_pages?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ValidationError {
  field: string;
  message: string;
  code?: string;
}

// Authentication API Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// User Types
export interface User {
  id: string;
  email: string;
  username: string;
  role: 'user' | 'admin';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  preferences?: UserPreferences;
  subscription?: UserSubscription;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    discord: boolean;
    telegram: boolean;
  };
  trading: {
    default_position_size: number;
    risk_tolerance: 'low' | 'medium' | 'high';
    auto_trading_enabled: boolean;
  };
}

export interface UserSubscription {
  plan: 'free' | 'premium' | 'pro';
  status: 'active' | 'cancelled' | 'expired';
  started_at: string;
  expires_at?: string;
  features: string[];
}

// System Status Types
export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  services: {
    database: ServiceStatus;
    websocket: ServiceStatus;
    ml_models: ServiceStatus;
    trading_engine: ServiceStatus;
    notification_service: ServiceStatus;
  };
  metrics: {
    total_users: number;
    active_portfolios: number;
    signals_generated_today: number;
    trades_executed_today: number;
    ai_confidence_avg: number;
  };
  last_updated: string;
}

export interface ServiceStatus {
  status: 'healthy' | 'degraded' | 'down';
  response_time_ms: number;
  error_rate: number;
  last_check: string;
  details?: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'signal_update' | 'price_update' | 'trade_update' | 'portfolio_update' | 'system_status';
  data: any;
  timestamp: string;
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  volume: number;
  change_24h: number;
  change_percentage_24h: number;
  timestamp: string;
}

// Notification Types
export interface Notification {
  id: string;
  user_id: string;
  type: 'signal' | 'trade' | 'portfolio' | 'system' | 'announcement';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  read: boolean;
  data?: Record<string, any>;
  created_at: string;
  expires_at?: string;
}

export interface CreateNotificationRequest {
  type: Notification['type'];
  title: string;
  message: string;
  priority?: Notification['priority'];
  user_ids?: string[];
  data?: Record<string, any>;
}

// Admin Types
export interface AdminStats {
  users: {
    total: number;
    active_today: number;
    new_this_week: number;
    retention_rate: number;
  };
  portfolios: {
    total: number;
    profitable: number;
    average_balance: number;
    total_pnl: number;
  };
  trading: {
    signals_generated: number;
    trades_executed: number;
    success_rate: number;
    total_volume: number;
  };
  system: {
    uptime_percentage: number;
    avg_response_time: number;
    error_rate: number;
    active_connections: number;
  };
}

export interface UserManagement {
  users: User[];
  total_count: number;
  filters: {
    role?: 'user' | 'admin';
    status?: 'active' | 'inactive';
    created_after?: string;
  };
}

// Analytics Types
export interface PerformanceComparison {
  ai_performance: {
    total_trades: number;
    winning_trades: number;
    win_rate: number;
    total_pnl: number;
    total_pnl_percentage: number;
    sharpe_ratio: number;
    max_drawdown: number;
  };
  random_performance: {
    total_trades: number;
    winning_trades: number;
    win_rate: number;
    total_pnl: number;
    total_pnl_percentage: number;
    sharpe_ratio: number;
    max_drawdown: number;
  };
  statistical_significance: {
    p_value: number;
    confidence_interval: number;
    is_significant: boolean;
  };
  period: {
    from: string;
    to: string;
    days: number;
  };
}

// Request/Response utilities
export type RequestConfig = {
  timeout?: number;
  retries?: number;
  cache?: boolean;
  headers?: Record<string, string>;
};

export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// ============================================================================
// AUTHENTICATION API TYPES
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface User {
  id: string;
  email: string;
  username: string;
  role: 'user' | 'admin';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  preferences?: UserPreferences;
  subscription?: UserSubscription;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    discord: boolean;
    telegram: boolean;
  };
  trading: {
    default_position_size: number;
    risk_tolerance: 'low' | 'medium' | 'high';
    auto_trading_enabled: boolean;
  };
}

export interface UserSubscription {
  plan: 'free' | 'premium' | 'pro';
  status: 'active' | 'cancelled' | 'expired';
  started_at: string;
  expires_at?: string;
  features: string[];
}

// ============================================================================
// PORTFOLIO API TYPES
// ============================================================================

export interface PortfolioOverviewResponse {
  DEBUG?: string;
  total_portfolios: number;
  total_value: number;
  initial_balance: number;
  total_pnl: number;
  total_pnl_percentage: number;
  cash_balance: number;
  active_positions: number;
  closed_positions: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  win_rate_today: number;
  total_realized_pnl: number;
  avg_portfolio_size: number;
  portfolios: Portfolio[];
  last_updated: string;
}

export interface PortfolioPositionsResponse {
  positions: Position[];
  summary?: {
    total_open: number;
    total_closed: number;
    total_pnl: number;
  };
}

export interface Position {
  id: string;
  position_id?: string;
  portfolio_id: string;
  symbol: string;
  side: 'long' | 'short';
  type?: string;
  position_type?: string;
  size: number;
  quantity?: number;
  entry_price: number;
  current_price: number;
  market_value?: number;
  pnl: number;
  pnl_percentage: number;
  unrealized_pnl?: number;
  unrealized_pnl_percentage?: number;
  confidence?: number;
  entry_time: string;
  exit_time?: string;
  hold_duration?: string;
  stop_loss?: number;
  take_profit?: number;
  status: 'open' | 'closing' | 'closed';
  created_at?: string;
  updated_at?: string;
  fees?: number;
  liquidation_price?: number;
}

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  balance: number;
  initial_balance: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  current_drawdown: number;
  positions: Position[];
  created_at: string;
  updated_at: string;
}

// ============================================================================
// TRADING API TYPES
// ============================================================================

export interface TradingSignal {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  timestamp: string;
  price: number;
  reason?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  timeframe?: string;
  strategy?: string;
  signal_type?: string;
}

export interface TradingSignalsResponse {
  signals: TradingSignal[];
  summary?: {
    total_signals: number;
    buy_signals: number;
    sell_signals: number;
    hold_signals: number;
    avg_confidence: number;
  };
  last_updated: string;
}

export interface MarketPriceResponse {
  symbol: string;
  price: number;
  volume: number;
  change_24h: number;
  change_percentage_24h: number;
  timestamp: string;
  high?: number;
  low?: number;
  open?: number;
  close?: number;
}

export interface BrainStatusResponse {
  enabled: boolean;
  status: string;
  last_analysis: string;
  total_analyses: number;
  positions_opened: number;
  positions_closed: number;
  current_mode: string;
  available_modes: string[];
}

// ============================================================================
// ANALYTICS API TYPES
// ============================================================================

export interface BacktestingResultsResponse {
  strategies: BacktestingStrategy[];
  historical_performance: HistoricalPerformancePoint[];
  drawdown_analysis: HistoricalPerformancePoint[];
}

export interface BacktestingStrategy {
  name: string;
  description: string;
  performance: {
    total_return: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
  };
  risk_metrics: {
    var_95: number;
    cvar_95: number;
    volatility: number;
    calmar_ratio: number;
  };
  status: string;
  last_tested: string;
}

export interface HistoricalPerformancePoint {
  date: string;
  enhanced_ensemble: number;
  elastic_net: number;
  random_forest: number;
}

export interface AIVsRandomAnalysisResponse {
  comparison_summary: {
    total_runs: number;
    ai_wins: number;
    ai_win_rate: number;
    average_ai_advantage: number;
    statistical_significance: boolean;
    p_value: number;
  };
  individual_runs: IndividualRun[];
}

export interface IndividualRun {
  run_id: string;
  ai_return: number;
  random_return: number;
  ai_win: boolean;
  winner: 'AI' | 'Random';
  timestamp: string;
  duration_seconds: number;
}

export interface AnalyticsOverviewResponse {
  backtesting_summary: {
    total_strategies_tested: number;
    best_performing_strategy: string;
    best_strategy_return: number;
    avg_sharpe_ratio: number;
    total_trades_analyzed: number;
    win_rate: number;
    max_drawdown: number;
    last_backtest: string;
  };
  ai_vs_random: {
    comparison_runs: number;
    ai_wins: number;
    ai_win_rate: number;
    average_ai_advantage: number;
    statistical_significance: boolean;
    p_value: number;
    last_comparison: string;
  };
  model_performance: {
    enhanced_ensemble_r2: number;
    elastic_net_weight: number;
    random_forest_weight: number;
    model_accuracy_mape: number;
    models_in_production: number;
    last_optimization: string;
  };
  live_performance: {
    current_portfolio_value: number;
    daily_return: number;
    ytd_return: number;
    active_positions: number;
    total_predictions_today: number;
    prediction_accuracy: number;
  };
}

// ============================================================================
// SYSTEM API TYPES
// ============================================================================

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  services: ServiceHealth[];
  metrics: {
    total_users: number;
    active_portfolios: number;
    signals_generated_today: number;
    trades_executed_today: number;
    ai_confidence_avg: number;
  };
  last_updated: string;
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'unknown';
  message: string;
  lastCheck: string;
  responseTime?: number;
  details?: ServiceHealthDetails;
}

export interface ServiceHealthDetails {
  uptime?: number;
  version?: string;
  connections?: number;
  memory_usage?: number;
  cpu_usage?: number;
  error_count?: number;
  last_error?: string;
  config_status?: 'valid' | 'invalid' | 'unknown';
}

export interface SystemStatusResponse {
  maintenance_mode: boolean;
  uptime_seconds: number;
  memory_usage: number;
  cpu_usage: number;
  disk_usage: number;
  active_connections: number;
  cache_size_mb: number;
  background_jobs: number;
}

export interface SystemSettingsResponse {
  trading_enabled: boolean;
  api_rate_limit: number;
  max_positions: number;
  risk_limit_percent: number;
  notification_cooldown: number;
  auto_backup_enabled: boolean;
  debug_mode: boolean;
  log_level: string;
}

export interface CacheStatsResponse {
  redis_cache: {
    size_mb: number;
    hit_rate: number;
    keys_count: number;
    memory_usage: number;
  };
  application_cache: {
    size_mb: number;
    entries: number;
    last_cleared: string;
  };
  database_cache: {
    query_cache_size: number;
    buffer_pool_size: number;
    cache_hit_ratio: number;
  };
}

// ============================================================================
// ENTERPRISE API TYPES
// ============================================================================

export interface EnterpriseSignalResponse {
  signals: EnterpriseSignal[];
  summary: {
    total_signals: number;
    high_confidence_signals: number;
    medium_confidence_signals: number;
    low_confidence_signals: number;
    avg_confidence: number;
  };
  timestamp: string;
}

export interface EnterpriseSignal {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  timestamp: string;
  price: number;
  layers: {
    layer_1_regime: SignalLayer;
    layer_2_lstm: SignalLayer;
    layer_3_reversal: SignalLayer;
    layer_4_filters: SignalLayer;
    layer_5_confidence: SignalLayer;
    layer_6_timing: SignalLayer;
  };
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  risk_reward_ratio?: number;
}

export interface SignalLayer {
  decision: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasoning: string;
  metrics: Record<string, any>;
}

// ============================================================================
// USER MANAGEMENT API TYPES
// ============================================================================

export interface UsersListResponse extends PaginatedApiResponse<UserManagementUser> {
  filters?: {
    role?: string;
    status?: string;
    search?: string;
  };
}

export interface UserManagementUser {
  id: string;
  email: string;
  username: string;
  role: 'user' | 'admin';
  status: 'active' | 'inactive' | 'suspended' | 'banned';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string;
  subscription_plan?: string;
  portfolio_value?: number;
}

export interface InvitationResponse {
  id: string;
  email: string;
  role: string;
  status: 'sent' | 'opened' | 'clicked' | 'registered' | 'expired' | 'cancelled';
  invited_by: string;
  created_at: string;
  sent_at: string;
  expires_at: string;
  custom_message?: string;
  tracking_data: {
    sent_count: number;
    opened_count: number;
    clicked_count: number;
    registered_count: number;
  };
}

// ============================================================================
// NOTIFICATION API TYPES
// ============================================================================

export interface NotificationResponse {
  id: string;
  user_id: string;
  type: 'signal' | 'trade' | 'portfolio' | 'system' | 'announcement';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  read: boolean;
  data?: Record<string, any>;
  created_at: string;
  expires_at?: string;
}

export interface NotificationSettingsResponse {
  email_enabled: boolean;
  push_enabled: boolean;
  discord_enabled: boolean;
  telegram_enabled: boolean;
  signal_notifications: boolean;
  trade_notifications: boolean;
  portfolio_notifications: boolean;
  system_notifications: boolean;
}

// ============================================================================
// REAL-TIME TRADING API TYPES
// ============================================================================

export interface LiveBitcoinPriceResponse {
  price: number;
  symbol: string;
  timestamp: string;
  volume: number;
  change_24h: number;
  change_percentage_24h: number;
}

export interface ConnectionStatusResponse {
  websocket_connected: boolean;
  binance_connected: boolean;
  database_connected: boolean;
  brain_connected: boolean;
  last_heartbeat: string;
  uptime_seconds: number;
}

export interface TradingModeStatusResponse {
  current_mode: string;
  available_modes: string[];
  mode_description: string;
  auto_trading_enabled: boolean;
  strict_live_stream: boolean;
}

// ============================================================================
// METRICS API TYPES
// ============================================================================

export interface MetricsResponse {
  timeRange: string;
  portfolio_metrics: {
    total_value: number;
    daily_pnl: number;
    daily_pnl_percentage: number;
    win_rate: number;
    total_trades: number;
    active_positions: number;
  };
  risk_metrics: {
    sharpe_ratio: number;
    max_drawdown: number;
    volatility: number;
    beta: number;
  };
  system_metrics: {
    uptime_percentage: number;
    response_time_avg: number;
    error_rate: number;
    active_connections: number;
  };
  timestamp: string;
} 