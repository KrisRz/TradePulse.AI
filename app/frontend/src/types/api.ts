// API Client Types

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  status: number;
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