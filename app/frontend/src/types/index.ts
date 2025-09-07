// Central types export
export * from './auth';
export * from './portfolio';
export * from './api';
// Note: signals types are included in api.ts to avoid conflicts

// Re-export commonly used API types for convenience
export type {
  // Auth types
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  User,
  UserPreferences,
  UserSubscription,

  // Portfolio types
  PortfolioOverviewResponse,
  PortfolioPositionsResponse,
  Position,
  Portfolio,

  // Trading types
  TradingSignal,
  TradingSignalsResponse,
  MarketPriceResponse,
  BrainStatusResponse,

  // Analytics types
  BacktestingResultsResponse,
  BacktestingStrategy,
  AIVsRandomAnalysisResponse,
  IndividualRun,
  AnalyticsOverviewResponse,

  // System types
  HealthResponse,
  ServiceHealth,
  SystemStatusResponse,
  SystemSettingsResponse,
  CacheStatsResponse,

  // Enterprise types
  EnterpriseSignalResponse,
  EnterpriseSignal,
  SignalLayer,

  // User Management types
  UsersListResponse,
  UserManagementUser,
  InvitationResponse,

  // Notification types
  NotificationResponse,
  NotificationSettingsResponse,

  // Real-time trading types
  LiveBitcoinPriceResponse,
  ConnectionStatusResponse,
  TradingModeStatusResponse,

  // Metrics types
  MetricsResponse,

  // Generic API types
  StandardApiResponse,
  PaginatedApiResponse,
  ApiResponse,
} from './api'; 