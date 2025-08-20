# Chart Components

## Overview
Reusable chart components for data visualization used across Admin Dashboard, Virtual Portfolio, and Analytics tabs. Handles live market data, trading performance, and portfolio charts.

## Components

### LiveBitcoinChart.tsx
- **Purpose**: Real-time Bitcoin price chart display
- **Features**:
  - Live price updates from Binance API
  - Interactive price charts
  - Real-time market data visualization
  - Price trend indicators
- **Used in**: 
  - Admin Dashboard → Real Trading Tab
  - Virtual Portfolio → Market Intelligence
  - Analytics Dashboard

## Usage
```typescript
import { LiveBitcoinChart } from '../charts';
```

## Data Sources
- Live Binance API data
- Real-time market prices
- Historical price data
- Trading volume information

## Future Components
- PerformanceChart - Portfolio performance visualization
- PortfolioChart - Portfolio allocation charts
- TradingChart - Advanced trading charts
