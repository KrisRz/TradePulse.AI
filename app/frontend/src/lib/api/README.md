# TradePulse.AI API Client

Professional, type-safe API client for TradePulse.AI frontend.

## Features

- ✅ **Environment-aware**: Automatically detects local vs AWS production
- ✅ **TypeScript**: Full type safety for all endpoints
- ✅ **Error handling**: Comprehensive error handling with retry logic
- ✅ **Auto-retry**: Automatic retry on network failures and 5xx errors
- ✅ **Auth management**: Automatic JWT token injection
- ✅ **Request interceptors**: Built-in request/response interceptors
- ✅ **Timeout handling**: Configurable timeouts with abort controllers

## Usage

### Authentication

```typescript
import { api } from '@/lib/api';

// Login
const response = await api.auth.login('admin@tradepulse.ai', 'admin0000');
if (response.success) {
  console.log('Logged in:', response.data.user);
  console.log('Token:', response.data.access_token);
}

// Register
const register = await api.auth.register('user@example.com', 'password123', 'username');

// Get current user
const user = await api.auth.getCurrentUser();

// Logout
api.auth.logout();

// Check if authenticated
if (api.auth.isAuthenticated()) {
  console.log('User is logged in');
}
```

### Portfolio Management

```typescript
import { api } from '@/lib/api';

// Get all portfolios
const portfolios = await api.portfolio.getAll();
if (portfolios.success) {
  console.log('My portfolios:', portfolios.data);
}

// Get specific portfolio
const portfolio = await api.portfolio.getById('portfolio_123');

// Create new portfolio
const newPortfolio = await api.portfolio.create({
  name: 'My Trading Portfolio',
  description: 'Day trading strategies',
  initial_balance: 10000
});

// Get portfolio positions
const positions = await api.portfolio.getPositions('portfolio_123');

// Get performance metrics
const performance = await api.portfolio.getPerformance('portfolio_123');
```

### Trading

```typescript
import { api } from '@/lib/api';

// Get current signals
const signals = await api.trading.getSignals({
  min_confidence: 0.7
});

// Get signal for specific symbol
const signal = await api.trading.getSignalBySymbol('BTCUSDT');

// Execute trade
const trade = await api.trading.executeTrade({
  portfolio_id: 'portfolio_123',
  symbol: 'BTCUSDT',
  action: 'BUY',
  quantity: 0.1,
  order_type: 'MARKET'
});

// Get trading history
const history = await api.trading.getTradeHistory({
  portfolio_id: 'portfolio_123',
  limit: 50
});

// Start trading session
const session = await api.trading.startSession({
  strategy: 'day_trading'
});
```

### Analytics & AI

```typescript
import { api } from '@/lib/api';

// Get comprehensive analysis
const analysis = await api.analytics.getComprehensiveAnalysis('BTCUSDT');
if (analysis.success) {
  console.log('AI Predictions:', analysis.data.ai_predictions);
  console.log('Recommendation:', analysis.data.final_recommendation);
}

// Get market data (candlesticks)
const marketData = await api.analytics.getMarketData({
  symbol: 'BTCUSDT',
  interval: '1h',
  limit: 100
});

// Get real-time price
const price = await api.analytics.getCurrentPrice('BTCUSDT');

// Get multiple prices
const prices = await api.analytics.getMultiplePrices(['BTCUSDT', 'ETHUSDT', 'BNBUSDT']);
```

### Admin Operations

```typescript
import { api } from '@/lib/api';

// Get system health
const health = await api.admin.getSystemHealth();
if (health.success) {
  console.log('Status:', health.data.status);
  console.log('Components:', health.data.components);
}

// Get brain controller state
const brainState = await api.admin.getBrainState();

// Get all users (admin only)
const users = await api.admin.getAllUsers();

// Get system metrics
const metrics = await api.admin.getSystemMetrics({
  start_time: '2025-09-01T00:00:00Z',
  end_time: '2025-09-29T23:59:59Z'
});

// Trigger brain warmup
await api.admin.triggerBrainWarmup();

// Restart trading engine
await api.admin.restartTradingEngine();
```

## Error Handling

All API calls return `ApiResponse<T>` with consistent error handling:

```typescript
const response = await api.portfolio.getAll();

if (response.success) {
  // Success - data is available
  console.log(response.data);
} else {
  // Error - handle gracefully
  console.error('Error code:', response.error.code);
  console.error('Error message:', response.error.message);
  console.error('Error details:', response.error.details);
}
```

## Direct API Client Usage

For custom endpoints not covered by the typed API:

```typescript
import { apiClient } from '@/lib/api';

// GET request
const response = await apiClient.get('/api/v1/custom/endpoint');

// POST request
const response = await apiClient.post('/api/v1/custom/endpoint', {
  data: 'value'
});

// With custom options
const response = await apiClient.get('/api/v1/endpoint', {
  timeout: 10000,
  retries: 5,
  skipAuth: false
});
```

## Environment Configuration

The API client automatically detects the environment:

- **Local development**: `http://localhost:9002`
- **AWS production**: `https://api.tradepulseai.co.uk`

Configuration is managed in `@/config/environments.ts`.

## TypeScript Types

All API types are exported from `@/lib/api/types`:

```typescript
import type {
  UserProfile,
  Portfolio,
  Position,
  TradingSignal,
  MarketAnalytics,
  SystemHealth
} from '@/lib/api/types';
```

## Architecture

```
src/lib/
├── api-client.ts         # Core HTTP client with retry logic
├── api/
│   ├── index.ts         # Main exports
│   ├── types.ts         # TypeScript type definitions
│   ├── auth.ts          # Authentication endpoints
│   ├── portfolio.ts     # Portfolio management
│   ├── trading.ts       # Trading operations
│   ├── analytics.ts     # Market analytics & AI
│   └── admin.ts         # Admin operations
└── auth-store.ts        # Auth state management (uses API client)
```

## Best Practices

1. **Always check `response.success`** before accessing `response.data`
2. **Handle errors gracefully** - display user-friendly messages
3. **Use TypeScript types** for compile-time safety
4. **Leverage auto-retry** for transient network failures
5. **Monitor performance** - API client logs request/response times

## DevOps Interview Highlights

This implementation demonstrates:
- ✅ Clean architecture with separation of concerns
- ✅ Environment-aware configuration
- ✅ Comprehensive error handling
- ✅ Type safety with TypeScript
- ✅ Retry logic and resilience
- ✅ Professional code organization
- ✅ Production-ready implementation
