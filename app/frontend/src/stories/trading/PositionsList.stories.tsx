import type { Meta, StoryObj } from '@storybook/preact';
import PositionsList from './PositionsList';

// Mock position data for stories
const mockPositions = [
  {
    id: '1',
    symbol: 'BTCUSDT',
    side: 'LONG' as const,
    size: 0.15,
    entryPrice: 64500,
    currentPrice: 65200,
    unrealizedPnl: 105,
    unrealizedPnlPercent: 1.09,
    margin: 1612.5,
    leverage: 4,
    liquidationPrice: 59987.5,
    stopLossPrice: 63000,
    takeProfitPrice: 67000,
    openTime: new Date('2024-01-15T10:30:00Z'),
    fees: 12.5,
    status: 'OPEN' as const
  },
  {
    id: '2',
    symbol: 'ETHUSDT',
    side: 'SHORT' as const,
    size: 2.5,
    entryPrice: 3200,
    currentPrice: 3150,
    unrealizedPnl: 125,
    unrealizedPnlPercent: 1.56,
    margin: 2000,
    leverage: 4,
    liquidationPrice: 3456,
    stopLossPrice: 3250,
    takeProfitPrice: 3000,
    openTime: new Date('2024-01-15T14:20:00Z'),
    fees: 8.0,
    status: 'OPEN' as const
  },
  {
    id: '3',
    symbol: 'BTCUSDT',
    side: 'LONG' as const,
    size: 0.08,
    entryPrice: 66000,
    currentPrice: 65200,
    unrealizedPnl: -64,
    unrealizedPnlPercent: -1.21,
    margin: 1320,
    leverage: 4,
    liquidationPrice: 61425,
    openTime: new Date('2024-01-15T16:45:00Z'),
    fees: 10.5,
    status: 'OPEN' as const
  }
];

const meta: Meta<typeof PositionsList> = {
  title: 'Trading/PositionsList',
  component: PositionsList,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
# PositionsList Component

Comprehensive positions management interface displaying active trading positions with real-time P&L tracking and risk management tools.

## Features
- **Real-time P&L**: Live profit/loss updates with percentage calculations
- **Position Management**: Close positions, update stop-loss and take-profit
- **Risk Monitoring**: Liquidation price warnings and margin usage
- **Visual Indicators**: Color-coded P&L and position sides
- **Responsive Design**: Optimized for desktop and mobile
- **Interactive Controls**: Click-to-edit stop-loss and take-profit levels

## Position States
- **Profitable**: Green indicators for positions in profit
- **Loss**: Red indicators for positions at loss
- **Warning**: Yellow indicators for positions near liquidation
- **Critical**: Flashing red for positions in danger zone

## Use Cases
- Portfolio monitoring dashboard
- Risk management interface
- Position tracking for day traders
- Performance analysis tool
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    userId: {
      control: 'text',
      description: 'User ID to filter positions (optional)',
      table: {
        type: { summary: 'string' },
        defaultValue: { summary: 'undefined' }
      }
    },
    showHeader: {
      control: 'boolean',
      description: 'Show the positions list header',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    maxHeight: {
      control: 'text',
      description: 'Maximum height of the positions list container',
      table: {
        type: { summary: 'string' },
        defaultValue: { summary: '400px' }
      }
    },
    onPositionClick: {
      action: 'position-clicked',
      description: 'Callback when a position is clicked',
      table: {
        type: { summary: '(position: Position) => void' }
      }
    },
    onClosePosition: {
      action: 'position-closed',
      description: 'Callback when closing a position',
      table: {
        type: { summary: '(positionId: string) => void' }
      }
    },
    onUpdateStopLoss: {
      action: 'stop-loss-updated',
      description: 'Callback when updating stop-loss',
      table: {
        type: { summary: '(positionId: string, stopLoss: number) => void' }
      }
    },
    onUpdateTakeProfit: {
      action: 'take-profit-updated',
      description: 'Callback when updating take-profit',
      table: {
        type: { summary: '(positionId: string, takeProfit: number) => void' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof PositionsList>;

export const Default: Story = {
  args: {
    userId: 'user123',
    showHeader: true,
    maxHeight: '400px'
  },
  parameters: {
    docs: {
      description: {
        story: 'Default PositionsList showing mixed profitable and losing positions.'
      }
    }
  }
};

export const ProfitablePositions: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList showing only profitable positions with green P&L indicators.'
      }
    }
  }
};

export const LosingPositions: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList showing positions at loss with red warning indicators.'
      }
    }
  }
};

export const EmptyState: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList empty state when user has no open positions.'
      }
    }
  }
};

export const NoHeader: Story = {
  args: {
    ...Default.args,
    showHeader: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList without header for compact integration.'
      }
    }
  }
};

export const CompactHeight: Story = {
  args: {
    ...Default.args,
    maxHeight: '200px',
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList with compact height showing scrollable content.'
      }
    }
  }
};

export const LargePositions: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList with large position sizes and high leverage.'
      }
    }
  }
};

export const HighRiskPositions: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList showing high-risk positions near liquidation.'
      }
    }
  }
};

// Mobile viewport stories
export const Mobile: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1',
    },
    docs: {
      description: {
        story: 'PositionsList optimized for mobile devices with touch-friendly controls.'
      }
    }
  }
};

export const MobileLandscape: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile2',
    },
    docs: {
      description: {
        story: 'PositionsList in mobile landscape orientation.'
      }
    }
  }
};

export const Tablet: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    viewport: {
      defaultViewport: 'tablet',
    },
    docs: {
      description: {
        story: 'PositionsList optimized for tablet devices.'
      }
    }
  }
};

// Dark mode variants
export const DarkMode: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    backgrounds: {
      default: 'dark',
    },
    docs: {
      description: {
        story: 'PositionsList with dark theme for night trading.'
      }
    }
  },
  decorators: [
    (Story) => (
      <div className="dark">
        <div className="bg-gray-900 min-h-screen p-6">
          <Story />
        </div>
      </div>
    ),
  ],
};

export const DarkModeCompact: Story = {
  args: {
    ...Default.args,
    maxHeight: '250px',
    showHeader: false,
  },
  parameters: {
    backgrounds: {
      default: 'dark',
    },
    docs: {
      description: {
        story: 'Compact dark mode PositionsList for dashboard integration.'
      }
    }
  },
  decorators: [
    (Story) => (
      <div className="dark">
        <div className="bg-gray-900 min-h-screen p-6">
          <Story />
        </div>
      </div>
    ),
  ],
};

// Loading state
export const LoadingState: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList in loading state while fetching positions.'
      }
    }
  }
};

// Error state
export const ErrorState: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'PositionsList error state when failing to load positions.'
      }
    }
  }
};

// Accessibility testing
export const AccessibilityTest: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    a11y: {
      config: {
        rules: [
          {
            id: 'color-contrast',
            enabled: true,
          },
          {
            id: 'keyboard',
            enabled: true,
          },
          {
            id: 'label',
            enabled: true,
          },
        ],
      },
    },
    docs: {
      description: {
        story: 'PositionsList with accessibility testing enabled for WCAG compliance.'
      }
    }
  }
};

// Interactive demonstration
export const InteractiveDemo: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'Interactive PositionsList demonstrating position management actions. Click positions to view details, update stop-loss/take-profit, or close positions.'
      }
    }
  }
}; 