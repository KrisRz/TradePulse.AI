# Trading Components

## Overview
Components for trading operations and position management used in Admin Dashboard Real Trading tab and Virtual Portfolio. Handles positions, orders, wallet operations, and trading controls.

## Components

### OpenPositionsManager.tsx
- **Purpose**: Manage and display open trading positions
- **Features**:
  - Real-time position monitoring
  - Position management controls
  - P&L tracking
  - Risk management tools
- **Used in**: 
  - Admin Dashboard → Real Trading Tab
  - Virtual Portfolio management

### WalletManagement.tsx
- **Purpose**: Wallet operations and balance management
- **Features**:
  - Wallet balance display
  - Transaction history
  - Deposit/withdrawal operations
  - Multi-currency support
- **Used in**: 
  - Admin Dashboard → Real Trading Tab
  - Wallet management interfaces

## Usage
```typescript
import { OpenPositionsManager, WalletManagement } from '../trading';
```

## Data Sources
- Real trading positions data
- Live wallet balances
- Transaction history
- Trading account information

## Future Components
- OrderForm - Trading order placement
- PositionsList - Position listing component
- TradingControls - Trading control panel
