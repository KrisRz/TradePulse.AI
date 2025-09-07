# TradePulse.AI Frontend-Backend Integration Plan

## 🎯 Overview
This document outlines the complete frontend structure and all API endpoints required for the TradePulse.AI admin dashboard integration.

**Frontend:** Astro + Preact + TypeScript (localhost:4321)  
**Backend:** FastAPI + Python (localhost:9002)  
**Database:** DynamoDB Local (localhost:8000)  
**Real Data:** Live Binance API + Professional Portfolio Service

## 📁 Frontend Structure

### Core Framework
- **Astro v5.13.5** - Main framework with SSR support
- **Preact** - Interactive components
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Vite** - Build tool and dev server

### Directory Structure
```
app/frontend/
├── src/
│   ├── components/
│   │   ├── admin/                    # Admin dashboard components
│   │   │   ├── analytics/           # Analytics dashboards
│   │   │   │   ├── AdvancedAnalyticsDashboard.tsx
│   │   │   │   ├── AIModelsDashboard.tsx
│   │   │   │   └── AnalyticsAdmin.tsx
│   │   │   ├── communication/       # Communication center
│   │   │   │   └── CommunicationCenter.tsx
│   │   │   ├── dashboard/           # Dashboard components
│   │   │   │   ├── PortfolioDashboard.tsx
│   │   │   │   ├── PortfolioOverview.tsx
│   │   │   │   └── QuickStats.tsx
│   │   │   ├── notifications/       # Notification system
│   │   │   │   └── NotificationSystemAdmin.tsx
│   │   │   ├── portfolio/           # Portfolio management
│   │   │   │   ├── market/
│   │   │   │   │   └── MarketIntelligence.tsx
│   │   │   │   ├── optimization/
│   │   │   │   │   └── PortfolioOptimization.tsx
│   │   │   │   ├── risk/
│   │   │   │   │   └── RiskManagement.tsx
│   │   │   │   ├── trading/
│   │   │   │   │   ├── RealTradingAdmin.tsx
│   │   │   │   │   └── TradingIntelligence.tsx
│   │   │   │   └── VirtualPortfolioAdmin.tsx
│   │   │   ├── signals/             # Signal management
│   │   │   │   └── SignalLogsAdmin.tsx
│   │   │   ├── system/              # System control
│   │   │   │   ├── SystemControlAdmin.tsx
│   │   │   │   └── SystemStatusDashboard.tsx
│   │   │   └── users/               # User management
│   │   │       └── UserManagementAdmin.tsx
│   │   ├── shared/                  # Shared components
│   │   │   ├── analytics/           # Analytics components
│   │   │   │   ├── ClosedPositionsAnalytics.tsx
│   │   │   │   ├── MetricsGrid.tsx
│   │   │   │   ├── PerformanceComparison.tsx
│   │   │   │   ├── PnLChart.tsx
│   │   │   │   ├── SignalAnalytics.tsx
│   │   │   │   ├── TradingHeatmap.tsx
│   │   │   │   └── WinRateAnalysis.tsx
│   │   │   ├── auth/                # Authentication
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── LogoutButton.tsx
│   │   │   │   ├── ProtectedRoute.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   └── SessionManager.tsx
│   │   │   ├── charts/              # Chart components
│   │   │   │   └── TradingViewChart.tsx
│   │   │   ├── realtime/            # Real-time components
│   │   │   │   └── LivePriceDisplay.tsx
│   │   │   ├── trading/             # Trading components
│   │   │   │   ├── MarketInfo.tsx
│   │   │   │   ├── OpenPositionsManager.tsx
│   │   │   │   ├── PositionsList.tsx
│   │   │   │   ├── TradeHistory.tsx
│   │   │   │   └── WalletManagement.tsx
│   │   │   └── ui/                  # UI components
│   │   └── user/                    # User dashboard
│   │       ├── analytics/
│   │       ├── dashboard/
│   │       ├── portfolio/
│   │       └── signals/
│   ├── pages/                       # Astro pages
│   │   ├── admin/
│   │   │   └── dashboard.astro
│   │   ├── auth/
│   │   │   ├── login.astro
│   │   │   ├── register.astro
│   │   │   └── signup.astro
│   │   ├── user_dashboard/
│   │   │   ├── analytics.astro
│   │   │   ├── index.astro
│   │   │   ├── portfolio.astro
│   │   │   ├── signals.astro
│   │   │   └── trading.astro
│   │   ├── analytics.astro
│   │   ├── dashboard.astro
│   │   ├── demo.astro
│   │   ├── index.astro
│   │   ├── portfolio.astro
│   │   └── signals.astro
│   ├── lib/                         # Core libraries
│   │   ├── api-client.ts           # Professional API client
│   │   ├── auth-store.ts           # Authentication store
│   │   ├── config.ts               # Configuration
│   │   ├── jwt-manager.ts          # JWT management
│   │   ├── logger.ts               # Logging
│   │   └── theme-config.ts         # Theme configuration
│   ├── hooks/                       # Custom hooks
│   │   └── admin-hooks.ts          # Admin-specific hooks
│   ├── contexts/                    # React contexts
│   │   ├── AuthContext.tsx
│   │   └── ThemeContext.tsx
│   ├── config/                      # Configuration
│   │   └── environments.ts         # Environment configs
│   ├── types/                       # TypeScript types
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── common.ts
│   │   ├── index.ts
│   │   ├── portfolio.ts
│   │   └── signals.ts
│   └── styles/
│       └── globals.css
├── public/                          # Static assets
├── astro.config.mjs                # Astro configuration
├── tailwind.config.mjs             # Tailwind configuration
├── tsconfig.json                   # TypeScript configuration
└── package.json                    # Dependencies
```

## 🔗 Complete Frontend-Backend API Connections

### 1. System Management APIs
```typescript
// System Status & Health
GET /api/health                           // System health check
GET /api/system/status                    // Detailed system status
GET /api/system/settings                  // System configuration
GET /api/system/cache-stats               // Cache performance metrics

// System Control
POST /api/system/restart                  // Restart services
POST /api/system/maintenance             // Maintenance mode toggle
PUT /api/system/settings                 // Update system settings
```

### 2. Portfolio Management APIs
```typescript
// Virtual Portfolio
GET /api/portfolio/virtual/overview       // Portfolio overview stats
GET /api/portfolio/virtual/positions      // Open positions
GET /api/portfolio/virtual/closed-positions // Closed positions history
GET /api/portfolio/virtual/history        // Full portfolio history
GET /api/portfolio/summary/{portfolioId?} // Portfolio summary
GET /api/portfolio/quick-stats            // Quick stats dashboard

// Risk Management
GET /api/portfolio/risk-analysis?timeframe={period} // Risk analysis
GET /api/portfolio/optimization-analysis?mode={mode} // Portfolio optimization
```

### 3. Trading Engine APIs
```typescript
// Trading Brain/Engine
GET /api/trading/brain/status             // AI brain status
POST /api/trading/brain/toggle            // Enable/disable brain
GET /api/trading/modes/status             // Trading mode status

// Market Data
GET /api/trading/market-price/{symbol}    // Live market prices
GET /api/real_trading/live/bitcoin-price  // Bitcoin price specifically
GET /api/signals/live/bitcoin-price       // Alternative bitcoin price endpoint
GET /api/trading/signals/latest           // Latest trading signals
GET /api/signals/market-intelligence      // Market intelligence data
GET /api/signals/orderbook/{symbol}       // Order book data
GET /api/signals/market-sentiment         // Market sentiment analysis

// Real Trading
GET /api/real-trading/positions/open      // Open real positions
GET /api/real_trading/status/connections  // Connection status
GET /api/real-trading/wallet/balances     // Wallet balances
GET /api/real-trading/wallet/transactions // Transaction history
GET /api/trading/withdrawal-limits        // Withdrawal limits
GET /api/trading/trades/history?limit={n} // Trade history
```

### 4. Analytics & Reporting APIs
```typescript
// Performance Analytics
GET /api/analytics/performance-comparison?timeRange={period} // Performance comparison
GET /api/analytics/metrics?timeRange={period}               // Metrics grid data
GET /api/analytics/pnl-data?timeRange={period}             // P&L chart data
GET /api/analytics/trading/heatmap                          // Trading heatmap
GET /api/analytics/signals/metrics                          // Signal analytics
GET /api/analytics/strategies/win-rates                     // Strategy win rates

// Advanced Analytics Dashboard
GET /api/user-analytics/dashboard?days={period}             // User analytics dashboard
GET /api/user-analytics/real-time-stats                     // Real-time user stats
```

### 5. AI Models Management APIs
```typescript
// Model Status & Control
GET /api/enterprise-admin/models/status   // AI model status
POST /api/enterprise-admin/models/retrain // Retrain models
GET /api/enterprise-admin/models/performance // Model performance metrics
```

### 6. User Management APIs
```typescript
// User CRUD Operations
GET /api/admin/users?{filters}            // List users with filters
GET /api/admin/users/{userId}             // Get specific user
PUT /api/admin/users/{userId}             // Update user
DELETE /api/admin/users/{userId}          // Delete user
POST /api/admin/users/{userId}/status     // Update user status
POST /api/admin/users/{userId}/role       // Update user role
POST /api/admin/users/{userId}/reset-password // Reset password

// Invitation System
GET /api/user-management/invitations      // List invitations
POST /api/user-management/invitations     // Send invitation
POST /api/user-management/invitations/{id}/resend // Resend invitation
DELETE /api/user-management/invitations/{id} // Cancel invitation
```

### 7. Communication & Notifications APIs
```typescript
// Communication Center
GET /api/admin/communications/messages/sent        // Sent messages
GET /api/admin/communications/announcements        // Announcements
GET /api/admin/communications/analytics/overview   // Communication analytics
POST /api/communication/messages/send              // Send message

// Notification System
GET /api/admin/notifications/settings              // Notification settings
GET /api/admin/notifications/channels              // Notification channels
GET /api/admin/notifications/logs                  // Notification logs
POST /api/admin/notifications/test                 // Test notifications
```

### 8. Dashboard Overview APIs
```typescript
// Quick Stats & Overview
GET /api/user/dashboard/overview          // User dashboard overview
GET /api/admin/system/status              // Admin system status overview
```

### 9. Authentication & Security
```typescript
// All requests use Authorization header:
headers: {
  'Authorization': 'Bearer enterprise_admin_token', // Development token
  'Content-Type': 'application/json'
}
```

### 10. WebSocket Connections
```typescript
// Real-time Updates
WebSocket: ws://localhost:9002/ws/{endpoint} // Real-time data streams
```

## 📊 Data Flow Architecture

### 3-Layer Data Architecture
```
Frontend (localhost:4321)
    ↓ HTTP calls
Backend API Routes (localhost:9002)
    ↓ Data access
┌─────────────────────────────────────┐
│ 1. Professional Portfolio Service   │ ← In-memory + DynamoDB
│ 2. Database Service                 │ ← DynamoDB wrapper  
│ 3. Direct DynamoDB Client          │ ← Raw DynamoDB calls
└─────────────────────────────────────┘
    ↓ Storage
DynamoDB Local (localhost:8000)
```

### Data Sources by Endpoint Type

#### Portfolio Data Flow
- **Professional Portfolio Service** - Main source (in-memory)
- **Synchronization** with DynamoDB Local in background
- **Live prices** from Binance API

#### Analytics Data Flow
- **Direct scanning** of DynamoDB Local tables
- **Raw data** without caching
- **Real-time calculations** in API

#### Trading Data Flow
- **Positions** - Professional Portfolio (memory)
- **History** - DynamoDB Local
- **Prices** - Binance API (live)

## 🛠 Technical Implementation

### API Client Configuration
```typescript
// lib/api-client.ts
export class TradePulseApiClient {
  private baseURL = 'http://localhost:9002';
  private token = 'enterprise_admin_token'; // Development
  
  // Professional retry logic with exponential backoff
  // Connection pooling and timeout management
  // Type-safe request/response handling
}
```

### Admin Hooks
```typescript
// hooks/admin-hooks.ts
export function useAdminData(endpoint: string) {
  // Real data fetching with enterprise_admin_token
  // Error handling and retry logic
  // Loading states and data caching
}

export function useSystemStatus() {
  return useAdminData('/api/admin/system/status');
}

export function useAnalyticsOverview() {
  return useAdminData('/api/analytics/overview');
}
```

### Environment Configuration
```typescript
// config/environments.ts
export const getEnvironmentConfig = () => ({
  api: {
    base: 'http://localhost:9002',
    websocket: 'ws://localhost:9002',
    timeout: 30000
  },
  database: {
    type: 'dynamodb_local',
    endpoint: 'http://localhost:8000'
  }
});
```

## 🔐 Authentication & Security

### Development Authentication
- **Token:** `enterprise_admin_token`
- **Storage:** localStorage
- **Validation:** Backend JWT verification
- **Fallback:** Development bypass for admin operations

### Production Authentication
- **JWT tokens** with refresh mechanism
- **Role-based access control**
- **Session management**
- **Secure token storage**

## 📱 Component Architecture

### Admin Dashboard Components
- **SystemStatusDashboard** - Real-time system monitoring
- **AnalyticsAdmin** - Comprehensive analytics with live data
- **VirtualPortfolioAdmin** - Portfolio management interface
- **UserManagementAdmin** - User administration
- **CommunicationCenter** - Message and notification management
- **TradingIntelligence** - Live trading operations

### Shared Components
- **LivePriceDisplay** - Real-time price updates
- **TradingViewChart** - Advanced charting
- **PositionsList** - Position management
- **MetricsGrid** - Performance metrics
- **WalletManagement** - Wallet operations

## 🚀 Development Workflow

### Frontend Development Server
```bash
cd /Applications/Projects/TradePulse.AI/app/frontend
npm run dev
# Runs on http://localhost:4321
```

### Backend Requirements
- **Backend server** running on localhost:9002
- **DynamoDB Local** running on localhost:8000
- **Live Binance API** connection for real data
- **Professional Portfolio Service** initialized

### Key Features
- **Hot reloading** for development
- **TypeScript** type checking
- **Real-time data** updates
- **Professional UI/UX** with Tailwind CSS
- **Mobile responsive** design
- **PWA capabilities** for production

## 📋 Implementation Status

### ✅ Completed
- **Frontend structure** - All components created
- **API endpoints** - 257 endpoints across 27 files
- **Data flow** - Professional Portfolio Service integration
- **Authentication** - Development token system
- **Real data** - No mocks, live Binance integration

### 🎯 Ready for Integration
- **Frontend:** Running on localhost:4321
- **Backend:** All API endpoints implemented
- **Database:** DynamoDB Local integration
- **Data:** Real-time professional trading data

### 🔄 Next Steps
1. Start backend server on port 9002
2. Ensure DynamoDB Local is running
3. Test API connectivity
4. Verify real data flow
5. Deploy to production AWS infrastructure

---

**Note:** This frontend is designed for professional trading operations with real data only. No mock data or fallbacks are used in production deployment.
