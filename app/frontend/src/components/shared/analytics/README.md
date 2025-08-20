# Analytics Components

## Overview
Components for the **Admin Dashboard Analytics tab** that handle trading performance analytics, backtesting results, AI vs Random analysis, and historical performance data.

## Components

### AnalyticsAdmin.tsx
- **Purpose**: Main analytics dashboard component
- **Features**: 
  - Trading performance metrics
  - Backtesting results display
  - AI vs Random analysis
  - Historical performance charts
- **Used in**: Admin Dashboard → Analytics Tab

### ClosedPositionsAnalytics.tsx
- **Purpose**: Detailed analytics for closed trading positions
- **Features**:
  - Position performance analysis
  - P&L breakdown
  - Win/loss statistics
  - Performance metrics
- **Used in**: Real Trading Admin, Analytics Dashboard

## Usage
```typescript
import { AnalyticsAdmin, ClosedPositionsAnalytics } from '../analytics';
```

## Data Sources
- Real DynamoDB analytics data
- Live trading performance metrics
- AI model performance data
- Historical backtesting results
