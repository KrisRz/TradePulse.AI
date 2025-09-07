// Portfolio Types - matching backend models

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

export interface Position {
  id: string;
  portfolio_id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entry_price: number;
  current_price: number;
  market_value: number;
  pnl: number;
  pnl_percentage: number;
  stop_loss?: number;
  take_profit?: number;
  status: 'open' | 'closing' | 'closed';
  created_at: string;
  updated_at: string;
}

export interface Trade {
  id: string;
  portfolio_id: string;
  position_id?: string;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit' | 'stop_market' | 'stop_limit';
  size: number;
  price: number;
  filled_size: number;
  filled_price: number;
  commission: number;
  pnl?: number;
  pnl_percentage?: number;
  signal_id?: string;
  strategy?: string;
  confidence?: number;
  status: 'pending' | 'filled' | 'cancelled' | 'failed';
  executed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PortfolioSummary {
  portfolio: Portfolio;
  daily_pnl: number;
  daily_pnl_percentage: number;
  weekly_pnl: number;
  weekly_pnl_percentage: number;
  monthly_pnl: number;
  monthly_pnl_percentage: number;
  total_trades_today: number;
  open_positions_count: number;
  best_performing_position?: Position;
  worst_performing_position?: Position;
}

export interface PerformanceMetrics {
  total_return: number;
  total_return_percentage: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_percentage: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins: number;
  consecutive_losses: number;
  trades_per_day: number;
  holding_period_avg: number; // in minutes
}

export interface PortfolioPnLPoint {
  timestamp: string;
  balance: number;
  pnl: number;
  pnl_percentage: number;
  trades_count: number;
}

// Request/Response types for API
export interface CreatePortfolioRequest {
  name: string;
  initial_balance: number;
}

export interface UpdatePortfolioRequest {
  name?: string;
  stop_loss_percentage?: number;
  take_profit_percentage?: number;
  max_position_size?: number;
}

export interface TradeRequest {
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit';
  size: number;
  price?: number;
  stop_loss?: number;
  take_profit?: number;
  strategy?: string;
  confidence?: number;
}

// Frontend-specific portfolio types for components
export interface PortfolioStats {
  total_value?: number;
  total_pnl?: number;
  total_pnl_percentage?: number;
  daily_pnl?: number;
  daily_pnl_percentage?: number;
  win_rate_today?: number;
  total_trades?: number;
  closed_positions?: number;
  available_balance?: number;
  active_positions?: number;
  total_realized_pnl?: number;
  total_portfolios?: number;
  active_users?: number;
  avg_portfolio_value?: number;
}

export interface PortfolioData {
  overview?: Record<string, any>;
  positions?: Record<string, any>[];
  performance?: Record<string, any>;
  analytics?: Record<string, any>;
  portfolios?: Record<string, any>[];
  stats?: PortfolioStats;
  lastUpdated?: string;
  total_portfolios?: number;
  total_value?: number;
  total_pnl?: number;
  daily_pnl?: number;
  active_positions?: number;
  closed_positions?: number;
}

// Trading Intelligence specific types
export interface TradingSignal {
  id: string;
  symbol: string;
  action: 'buy' | 'sell';
  confidence: number;
  timestamp: string;
  price: number;
  reason: string;
}

export interface SignalData {
  signals: TradingSignal[];
  summary: {
    total_signals: number;
    buy_signals: number;
    sell_signals: number;
    avg_confidence: number;
  };
  last_updated: string;
}

// Market Intelligence specific types
export interface MarketCondition {
  condition: string;
  value: number;
  status: 'bullish' | 'bearish' | 'neutral';
  trend: 'up' | 'down' | 'sideways';
}

export interface MarketData {
  conditions: MarketCondition[];
  sentiment: {
    overall: 'bullish' | 'bearish' | 'neutral';
    score: number;
  };
  volatility: number;
  volume: number;
  last_updated: string;
}

// Risk Management specific types
export interface RiskMetrics {
  var_95: number;
  var_99: number;
  expected_shortfall: number;
  beta: number;
  correlation_matrix: Record<string, Record<string, number>>;
  drawdown: number;
  max_drawdown: number;
}

export interface RiskData {
  metrics: RiskMetrics;
  alerts: Array<{
    level: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    timestamp: string;
  }>;
  exposure: Record<string, number>;
}

// Portfolio Optimization specific types
export interface OptimizationResult {
  recommended_allocation: Record<string, number>;
  expected_return: number;
  expected_risk: number;
  sharpe_ratio: number;
  efficient_frontier: Array<{
    return: number;
    risk: number;
  }>;
}

export interface OptimizationData {
  current_allocation: Record<string, number>;
  optimization_result: OptimizationResult;
  rebalancing_suggestions: Array<{
    action: 'buy' | 'sell' | 'hold';
    symbol: string;
    amount: number;
    reason: string;
  }>;
} 