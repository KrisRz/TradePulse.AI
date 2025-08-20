/**
 * Components Barrel Export
 * Centralized exports for all components
 */

// Admin Components
export * from './admin';

// Auth Components
export { default as LoginForm } from './auth/LoginForm';
export { default as RegisterForm } from './auth/RegisterForm';
export { default as LogoutButton } from './auth/LogoutButton';
export { default as ProtectedRoute } from './auth/ProtectedRoute';
export { default as SessionManager } from './auth/SessionManager';

// Analytics Components
export { default as MetricsGrid } from './analytics/MetricsGrid';
export { default as PerformanceComparison } from './analytics/PerformanceComparison';
export { default as PnLChart } from './analytics/PnLChart';
export { default as TradingHeatmap } from './analytics/TradingHeatmap';
export { default as WinRateAnalysis } from './analytics/WinRateAnalysis';

// Chart Components
export { default as AIPerformanceChart } from './charts/AIPerformanceChart';
export { default as DrawdownChart } from './charts/DrawdownChart';
export { default as SimpleBitcoinChart } from './charts/SimpleBitcoinChart';
export { default as TradingViewChart } from './charts/TradingViewChart';

// Dashboard Components
export { default as PortfolioOverview } from './dashboard/PortfolioOverview';
export { default as QuickStats } from './dashboard/QuickStats';

// Layout Components
export { default as AppLayout } from './layout/AppLayout';
export { default as MobileLayout } from './layout/MobileLayout';

// Mobile Components
export { default as MobileOptimized } from './mobile/MobileOptimized';

// Notification Components
export { default as NotificationSystem } from './notifications/NotificationSystem';

// Provider Components
export { default as AuthProviderWrapper } from './providers/AuthProviderWrapper';

// Realtime Components
export { default as AIConfidenceIndicator } from './realtime/AIConfidenceIndicator';
export { default as LivePriceDisplay } from './realtime/LivePriceDisplay';
export { default as TradingStatusIndicator } from './realtime/TradingStatusIndicator';

// Signal Components
export { default as ConfidenceScore } from './signals/ConfidenceScore';
export { default as LiveSignalStatus } from './signals/LiveSignalStatus';
export { default as SignalAnalytics } from './signals/SignalAnalytics';
export { default as SignalCard } from './signals/SignalCard';
export { default as SignalFeed } from './signals/SignalFeed';
export { default as SignalFilters } from './signals/SignalFilters';

// Trading Components
export { default as MarketInfo } from './trading/MarketInfo';
export { default as OrderForm } from './trading/OrderForm';
export { default as PositionsList } from './trading/PositionsList';
export { default as RiskManagement } from './trading/RiskManagement';
export { default as TradeHistory } from './trading/TradeHistory';
export { default as TradingChart } from './trading/TradingChart';

// UI Components
export { default as AccessibleButton } from './ui/AccessibleButton';
export { default as DarkModeToggle } from './ui/DarkModeToggle';
export { default as LiveRegion } from './ui/LiveRegion';
export { default as LoadingSpinner } from './ui/LoadingSpinner';
export { default as SkipLinks } from './ui/SkipLinks';
export { default as ThemeAwareCard } from './ui/ThemeAwareCard';