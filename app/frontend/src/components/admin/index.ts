/**
 * Admin Components Barrel Export
 * Components for admin users only - full system access
 */

// Main Admin Components
export { default as VirtualPortfolioAdmin } from './VirtualPortfolioAdmin';
export { default as UserManagementAdmin } from './UserManagementAdmin';
export { default as RealTradingAdmin } from './RealTradingAdmin';
export { default as NotificationSystemAdmin } from './NotificationSystemAdmin';
export { default as SignalLogsAdmin } from './SignalLogsAdmin';
export { default as CommunicationCenter } from './CommunicationCenter';
export { default as AdvancedAnalyticsDashboard } from './AdvancedAnalyticsDashboard';
export { default as AIModelsDashboard } from './AIModelsDashboard';

// Admin System Components
export { default as SystemStatusDashboard } from './system/SystemStatusDashboard';
export { default as SystemControlAdmin } from './system/SystemControlAdmin';

// Admin Dashboard Components
export { default as PortfolioDashboard } from './dashboard/PortfolioDashboard';
export { default as PortfolioOverview } from './dashboard/PortfolioOverview';
export { default as QuickStats } from './dashboard/QuickStats';

// Admin Portfolio Sub-components
export { default as MarketIntelligence } from './portfolio/MarketIntelligence';
export { default as PortfolioOptimization } from './portfolio/PortfolioOptimization';
export { default as RiskManagement } from './portfolio/RiskManagement';
export { default as TradingIntelligence } from './portfolio/TradingIntelligence';
export { default as RealTradingAdmin } from './RealTradingAdmin';
export { default as SignalLogsAdmin } from './SignalLogsAdmin';
export { default as SystemControlAdmin } from './SystemControlAdmin';
// Note: Some components may not exist - only export existing ones

// Portfolio Sub-components (already exported above)
export { default as TradingIntelligence } from './portfolio/TradingIntelligence';
export { default as RiskManagement } from './portfolio/RiskManagement';
export { default as MarketIntelligence } from './portfolio/MarketIntelligence';
export { default as PortfolioOptimization } from './portfolio/PortfolioOptimization';
// ClosedPositionsAnalytics moved to ../shared/analytics folder
export { ClosedPositionsAnalytics } from '../shared/analytics';
// LiveBitcoinChart moved to ../shared/charts folder
export { LiveBitcoinChart } from '../shared/charts';
// Trading components moved to ../shared/trading folder
export { OpenPositionsManager, WalletManagement } from '../shared/trading';

// Additional Components (only existing ones)
// export { default as AIModelsDashboard } from './AIModelsDashboard'; // May not exist
// export { default as EnhancedBitcoinChart } from './EnhancedBitcoinChart'; // May not exist