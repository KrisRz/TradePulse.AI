/**
 * Analytics Components
 * 
 * Components for the Admin Dashboard Analytics tab
 * Handles trading performance analytics, backtesting results,
 * AI vs Random analysis, and historical performance data
 */

export { default as AnalyticsAdmin } from './AnalyticsAdmin';
export { default as ClosedPositionsAnalytics } from './ClosedPositionsAnalytics';
export { default as MetricsGrid } from './MetricsGrid';
export { default as PerformanceComparison } from './PerformanceComparison';
export { default as PnLChart } from './PnLChart';
export { default as TradingHeatmap } from './TradingHeatmap';
export { default as WinRateAnalysis } from './WinRateAnalysis';
export { default as SignalAnalytics } from './SignalAnalytics';

// Re-export types if needed
export type { 
  AnalyticsOverview,
  BacktestingResults,
  HistoricalPerformance 
} from './AnalyticsAdmin';
