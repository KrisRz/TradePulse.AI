import type { Meta, StoryObj } from '@storybook/preact';
import TradingHeatmap from './TradingHeatmap';

const meta: Meta<typeof TradingHeatmap> = {
  title: 'Analytics/TradingHeatmap',
  component: TradingHeatmap,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
# TradingHeatmap Component

Interactive heatmap visualization showing trading patterns, performance metrics, and time-based analysis.

## Features
- **Time-based Heatmaps**: Visualize trading activity by hour, day, week, or month
- **Performance Heatmaps**: Show P&L distribution across different time periods
- **Market Condition Analysis**: Trading performance across different market regimes
- **Interactive Tooltips**: Detailed information on hover with specific metrics
- **Color Gradients**: Intuitive color coding for quick pattern recognition
- **Zoom and Pan**: Interactive navigation for detailed analysis
- **Multiple Views**: Switch between different heatmap types and metrics
- **Export Options**: Save heatmaps as images or export underlying data

## Heatmap Types
- **Hourly Activity**: Trading frequency and performance by hour of day
- **Daily Performance**: Daily P&L and win rate visualization
- **Weekly Patterns**: Weekly trading patterns and seasonal effects
- **Monthly Overview**: Monthly performance aggregation
- **Market Regime**: Performance across bull/bear/sideways markets
- **Volatility Bands**: Trading success across different volatility levels

## Color Schemes
- **Profit/Loss**: Green (profit) to red (loss) gradient
- **Activity Level**: Blue intensity based on trading frequency  
- **Win Rate**: Yellow (low) to green (high) success rate
- **Volatility**: Cool (low) to warm (high) volatility levels

## Metrics Displayed
- **P&L**: Profit and loss amounts
- **Win Rate**: Percentage of successful trades
- **Trade Count**: Number of trades executed
- **Average Trade**: Mean profit/loss per trade
- **Sharpe Ratio**: Risk-adjusted performance
- **Maximum Drawdown**: Largest losses during period

## Use Cases
- Pattern recognition in trading behavior
- Performance optimization across time periods
- Market timing analysis and strategy refinement
- Risk management and exposure analysis
- Client reporting and strategy validation
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    heatmapType: {
      control: 'select',
      options: ['hourly', 'daily', 'weekly', 'monthly', 'regime'],
      description: 'Type of heatmap visualization',
      table: {
        type: { summary: 'hourly | daily | weekly | monthly | regime' },
        defaultValue: { summary: 'daily' }
      }
    },
    metric: {
      control: 'select',
      options: ['pnl', 'winrate', 'trades', 'sharpe'],
      description: 'Metric to display in heatmap',
      table: {
        type: { summary: 'pnl | winrate | trades | sharpe' },
        defaultValue: { summary: 'pnl' }
      }
    },
    timeRange: {
      control: 'select',
      options: ['30d', '90d', '1y', 'all'],
      description: 'Time period for analysis',
      table: {
        type: { summary: '30d | 90d | 1y | all' },
        defaultValue: { summary: '90d' }
      }
    },
    showTooltips: {
      control: 'boolean',
      description: 'Show interactive tooltips',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    colorScheme: {
      control: 'select',
      options: ['profit', 'activity', 'winrate', 'volatility'],
      description: 'Color scheme for heatmap',
      table: {
        type: { summary: 'profit | activity | winrate | volatility' },
        defaultValue: { summary: 'profit' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof TradingHeatmap>;

export const Default: Story = {
  args: {
    heatmapType: 'daily',
    metric: 'pnl',
    timeRange: '90d',
    showTooltips: true,
    colorScheme: 'profit'
  },
  parameters: {
    docs: {
      description: {
        story: 'Default trading heatmap showing daily P&L patterns over 90 days.'
      }
    }
  }
};

export const HourlyActivity: Story = {
  args: {
    heatmapType: 'hourly',
    metric: 'trades',
    timeRange: '30d',
    showTooltips: true,
    colorScheme: 'activity'
  },
  parameters: {
    docs: {
      description: {
        story: 'Hourly trading activity heatmap showing optimal trading times and frequency patterns.'
      }
    }
  }
};

export const WeeklyWinRate: Story = {
  args: {
    heatmapType: 'weekly',
    metric: 'winrate',
    timeRange: '1y',
    showTooltips: true,
    colorScheme: 'winrate'
  },
  parameters: {
    docs: {
      description: {
        story: 'Weekly win rate heatmap revealing seasonal patterns and performance trends.'
      }
    }
  }
};

export const MonthlyPerformance: Story = {
  args: {
    heatmapType: 'monthly',
    metric: 'pnl',
    timeRange: 'all',
    showTooltips: true,
    colorScheme: 'profit'
  },
  parameters: {
    docs: {
      description: {
        story: 'Monthly performance heatmap showing long-term trading results and seasonal effects.'
      }
    }
  }
};

export const MarketRegimeAnalysis: Story = {
  args: {
    heatmapType: 'regime',
    metric: 'sharpe',
    timeRange: '1y',
    showTooltips: true,
    colorScheme: 'volatility'
  },
  parameters: {
    docs: {
      description: {
        story: 'Market regime heatmap showing risk-adjusted performance across different market conditions.'
      }
    }
  }
};

export const HighActivity: Story = {
  args: {
    heatmapType: 'daily',
    metric: 'trades',
    timeRange: '30d',
    showTooltips: true,
    colorScheme: 'activity'
  },
  parameters: {
    docs: {
      description: {
        story: 'Trading heatmap during high-activity period with intense color saturation.'
      }
    }
  }
};

export const LowVolatility: Story = {
  args: {
    heatmapType: 'weekly',
    metric: 'pnl',
    timeRange: '90d',
    showTooltips: true,
    colorScheme: 'profit'
  },
  parameters: {
    docs: {
      description: {
        story: 'Trading heatmap during low volatility market conditions with muted patterns.'
      }
    }
  }
};

export const MobileView: Story = {
  args: {
    heatmapType: 'daily',
    metric: 'pnl',
    timeRange: '30d',
    showTooltips: false,
    colorScheme: 'profit'
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'TradingHeatmap optimized for mobile with simplified tooltips and responsive design.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  args: {
    heatmapType: 'daily',
    metric: 'pnl',
    timeRange: '90d',
    showTooltips: true,
    colorScheme: 'profit'
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
        ],
      },
    },
    docs: {
      description: {
        story: 'TradingHeatmap with accessibility testing for color-blind users and keyboard navigation.'
      }
    }
  }
}; 