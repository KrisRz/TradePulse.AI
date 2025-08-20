/**
 * Common Types
 * Shared TypeScript types across the application
 */

// Generic API Response
export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
  message?: string;
  status?: number;
  success?: boolean;
}

// User Types
export interface User {
  id: string;
  email: string;
  name?: string;
  role: 'admin' | 'user';
  is_admin: boolean;
  created_at: string;
  last_login?: string;
  status: 'active' | 'inactive' | 'suspended';
}

// Trading Position
export interface Position {
  id: string;
  symbol: string;
  side: 'buy' | 'sell' | 'long' | 'short';
  type?: string;
  position_type?: string;
  quantity: number;
  size?: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  unrealized_pnl?: number;
  unrealized_pnl_percentage?: number;
  confidence: number;
  entry_time: string;
  exit_time?: string;
  hold_duration: string;
  stop_loss?: number;
  take_profit?: number;
  status: 'open' | 'closed' | 'pending';
}

// Portfolio Statistics
export interface PortfolioStats {
  total_value: number;
  available_balance: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  total_return: number;
  total_return_percentage: number;
  win_rate: number;
  win_rate_today: number;
  total_trades: number;
  active_positions: number;
  execution_rate: number;
  total_signals_generated: number;
  signals_executed: number;
}

// Trading Signal
export interface TradingSignal {
  id: string;
  symbol: string;
  signal_type: 'buy' | 'sell' | 'hold';
  confidence: number;
  price: number;
  timestamp: string;
  source: string;
  layer?: string;
  reasoning?: string;
  executed: boolean;
}

// System Status
export interface SystemStatus {
  status: 'healthy' | 'warning' | 'error';
  uptime: number;
  last_check: string;
  services: {
    api: 'online' | 'offline';
    database: 'online' | 'offline';
    ai_models: 'online' | 'offline';
    market_data: 'online' | 'offline';
  };
  performance: {
    cpu_usage: number;
    memory_usage: number;
    response_time: number;
  };
}

// Notification
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}

// Chart Data Point
export interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

// Form Field Types
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'checkbox' | 'textarea';
  value: string | number | boolean;
  required?: boolean;
  placeholder?: string;
  options?: Array<{ label: string; value: string | number }>;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
}

// Component Props
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
  'data-testid'?: string;
}

// Loading State
export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
  lastFetch?: string;
}

// Pagination
export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

// Sort Configuration
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

// Filter Configuration
export interface FilterConfig {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'startsWith' | 'endsWith';
  value: string | number | boolean;
}

// Theme Configuration
export interface ThemeConfig {
  mode: 'light' | 'dark' | 'system';
  primaryColor: string;
  accentColor: string;
}

// Environment Configuration
export interface EnvironmentConfig {
  isDevelopment: boolean;
  isProduction: boolean;
  apiUrl: string;
  version: string;
}

export default {
  ApiResponse,
  User,
  Position,
  PortfolioStats,
  TradingSignal,
  SystemStatus,
  Notification,
  ChartDataPoint,
  FormField,
  BaseComponentProps,
  LoadingState,
  Pagination,
  SortConfig,
  FilterConfig,
  ThemeConfig,
  EnvironmentConfig,
};