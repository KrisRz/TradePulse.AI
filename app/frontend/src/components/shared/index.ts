/**
 * Shared Components Barrel Export
 * Components used by both admin and user interfaces
 */

// Authentication Components
export { default as LoginForm } from './auth/LoginForm';
export { default as LogoutButton } from './auth/LogoutButton';
export { default as ProtectedRoute } from './auth/ProtectedRoute';
export { default as RegisterForm } from './auth/RegisterForm';
export { default as SessionManager } from './auth/SessionManager';

// UI Components
export { default as AccessibleButton } from './ui/AccessibleButton';
export { default as DarkModeToggle } from './ui/DarkModeToggle';
export { default as LiveRegion } from './ui/LiveRegion';
export { default as LoadingSpinner } from './ui/LoadingSpinner';
export { default as SkipLinks } from './ui/SkipLinks';
export { default as ThemeAwareCard } from './ui/ThemeAwareCard';

// Chart Components
export { default as LiveBitcoinChart } from './charts/LiveBitcoinChart';

// Real-time Components
export { default as AIConfidenceIndicator } from './realtime/AIConfidenceIndicator';
export { default as LivePriceDisplay } from './realtime/LivePriceDisplay';
export { default as TradingStatusIndicator } from './realtime/TradingStatusIndicator';
export { ConfidenceScore } from './realtime/ConfidenceScore';
export { default as LiveSignalStatus } from './realtime/LiveSignalStatus';
export { default as SignalCard } from './realtime/SignalCard';
export { default as SignalFeed } from './realtime/SignalFeed';
export { default as SignalFilters } from './realtime/SignalFilters';

// Analytics Components (shared between admin and user)
export { default as AnalyticsAdmin } from './analytics/AnalyticsAdmin';
export { default as ClosedPositionsAnalytics } from './analytics/ClosedPositionsAnalytics';

// Trading Components (shared between admin and user)
export { default as OpenPositionsManager } from './trading/OpenPositionsManager';
export { default as WalletManagement } from './trading/WalletManagement';
