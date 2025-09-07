// Shared Components Barrel Exports

// Analytics
export { default as SignalAnalytics } from './analytics/SignalAnalytics.tsx';
export { default as WinRateAnalysis } from './analytics/WinRateAnalysis.tsx';
export { default as TradingHeatmap } from './analytics/TradingHeatmap.tsx';
export { default as PerformanceComparison } from './analytics/PerformanceComparison.tsx';
export { default as MetricsGrid } from './analytics/MetricsGrid.tsx';
export { default as PnLChart } from './analytics/PnLChart.tsx';
export { default as ClosedPositionsAnalytics } from './analytics/ClosedPositionsAnalytics.tsx';

// Authentication
export { default as LoginForm } from './auth/LoginForm.tsx';
export { default as RegisterForm } from './auth/RegisterForm.tsx';
export { default as LogoutButton } from './auth/LogoutButton.tsx';
export { default as ProtectedRoute } from './auth/ProtectedRoute.tsx';
export { default as SessionManager } from './auth/SessionManager.tsx';

// Charts - ALL REMOVED FOR CLEAN START

// Real-time
export { default as LivePriceDisplay } from './realtime/LivePriceDisplay.tsx';
export { default as SignalFeed } from './realtime/SignalFeed.tsx';
export { default as SignalCard } from './realtime/SignalCard.tsx';
export { default as LiveSignalStatus } from './realtime/LiveSignalStatus.tsx';
export { default as AIConfidenceIndicator } from './realtime/AIConfidenceIndicator.tsx';
export { default as ConfidenceScore } from './realtime/ConfidenceScore.tsx';
export { default as TradingStatusIndicator } from './realtime/TradingStatusIndicator.tsx';
export { default as SignalFilters } from './realtime/SignalFilters.tsx';

// Trading
export { default as OrderForm } from './trading/OrderForm.tsx';
export { default as PositionsList } from './trading/PositionsList.tsx';
export { default as TradeHistory } from './trading/TradeHistory.tsx';
export { default as OpenPositionsManager } from './trading/OpenPositionsManager.tsx';
export { default as MarketInfo } from './trading/MarketInfo.tsx';
export { default as WalletManagement } from './trading/WalletManagement.tsx';

// UI Components
export { default as LoadingSpinner } from './ui/LoadingSpinner.tsx';
export { default as NotificationSystem } from './ui/NotificationSystem.tsx';
export { default as DarkModeToggle } from './ui/DarkModeToggle.tsx';
export { default as ThemeAwareCard } from './ui/ThemeAwareCard.tsx';
export { default as AccessibleButton } from './ui/AccessibleButton.tsx';
export { default as LiveRegion } from './ui/LiveRegion.tsx';
export { default as SkipLinks } from './ui/SkipLinks.tsx';