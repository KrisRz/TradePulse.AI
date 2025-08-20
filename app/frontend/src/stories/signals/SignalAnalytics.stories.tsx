import type { Meta, StoryObj } from '@storybook/preact';
import SignalAnalytics from './SignalAnalytics';

const meta: Meta<typeof SignalAnalytics> = {
  title: 'Signals/SignalAnalytics',
  component: SignalAnalytics,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: `
# SignalAnalytics Component

Comprehensive analytics dashboard for AI trading signal performance analysis and optimization.

## Features
- **Signal Performance Tracking**: Monitor success rates and accuracy across timeframes
- **Strategy Comparison**: Compare different AI strategies and their effectiveness
- **Interactive Charts**: Dynamic visualizations of signal performance metrics
- **Time Analysis**: Performance breakdown by hour, day, week, and market conditions
- **Confidence Analysis**: Correlation between AI confidence levels and success rates
- **Market Regime Analysis**: Signal performance across different market conditions
- **Export Capabilities**: Download charts and data for reporting and analysis
- **Real-time Updates**: Live performance tracking with auto-refresh capabilities

## Analytics Views
- **Strategy Performance**: AI Breakout, Reversal, Momentum, and Trend strategies
- **Time-based Analysis**: Performance patterns across different time periods
- **Confidence Correlation**: How confidence scores relate to actual outcomes
- **Market Condition Impact**: Bull vs bear vs sideways market performance
- **Risk-Reward Analysis**: Risk-adjusted performance metrics and ratios

## Key Metrics
- **Success Rate**: Percentage of profitable signals over time period
- **Average P&L**: Mean profit/loss per signal execution
- **Sharpe Ratio**: Risk-adjusted performance measurement
- **Maximum Drawdown**: Largest consecutive loss period
- **Win/Loss Ratio**: Average win vs average loss comparison
- **Signal Frequency**: Number of signals generated per time period
- **Execution Speed**: Time between signal generation and execution
- **Slippage Analysis**: Difference between expected and actual execution prices

## Chart Types
- **Performance Over Time**: Line charts showing cumulative performance
- **Strategy Comparison**: Bar charts comparing different AI strategies
- **Confidence Distribution**: Histograms of confidence score distributions
- **Time Heatmaps**: Performance by hour/day patterns
- **Risk-Return Scatter**: Risk vs return scatter plots
- **Drawdown Analysis**: Underwater equity curves

## Use Cases
- AI model performance evaluation
- Strategy optimization and fine-tuning
- Risk management and exposure analysis
- Client reporting and transparency
- Regulatory compliance documentation
- Research and development insights
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    timeRange: {
      control: 'select',
      options: ['7d', '30d', '90d', '1y', 'all'],
      description: 'Time period for signal analysis',
      table: {
        type: { summary: '7d | 30d | 90d | 1y | all' },
        defaultValue: { summary: '30d' }
      }
    },
    showCharts: {
      control: 'boolean',
      description: 'Display interactive charts',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    showDetails: {
      control: 'boolean',
      description: 'Show detailed analytics breakdown',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    onTimeRangeChange: {
      action: 'time-range-changed',
      description: 'Callback when time range is modified',
      table: {
        type: { summary: '(range: string) => void' }
      }
    },
    onExport: {
      action: 'data-exported',
      description: 'Callback when data export is requested',
      table: {
        type: { summary: '() => void' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof SignalAnalytics>;

export const Default: Story = {
  args: {
    timeRange: '30d',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Default SignalAnalytics dashboard showing 30-day performance overview with charts and detailed metrics.'
      }
    }
  }
};

export const WeeklyAnalysis: Story = {
  args: {
    timeRange: '7d',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Weekly signal analysis focused on short-term performance patterns and recent activity.'
      }
    }
  }
};

export const QuarterlyOverview: Story = {
  args: {
    timeRange: '90d',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Quarterly signal analytics providing comprehensive 3-month performance evaluation.'
      }
    }
  }
};

export const YearlyReport: Story = {
  args: {
    timeRange: '1y',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Annual signal analytics report showing long-term AI performance trends and seasonal patterns.'
      }
    }
  }
};

export const ChartsOnly: Story = {
  args: {
    timeRange: '30d',
    showCharts: true,
    showDetails: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Chart-focused view emphasizing visual analytics without detailed breakdowns.'
      }
    }
  }
};

export const DetailedMetrics: Story = {
  args: {
    timeRange: '90d',
    showCharts: false,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Detailed metrics view focusing on numerical analysis and statistical breakdowns.'
      }
    }
  }
};

export const HighPerformance: Story = {
  args: {
    timeRange: '30d',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'SignalAnalytics during high-performance period with excellent AI accuracy and profitability.'
      }
    }
  }
};

export const StrategyComparison: Story = {
  args: {
    timeRange: '90d',
    showCharts: true,
    showDetails: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Strategy comparison view highlighting performance differences between AI approaches.'
      }
    }
  }
};

export const MobileView: Story = {
  args: {
    timeRange: '7d',
    showCharts: true,
    showDetails: false
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'SignalAnalytics optimized for mobile with simplified layout and essential charts.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  args: {
    timeRange: '30d',
    showCharts: true,
    showDetails: true
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
        story: 'SignalAnalytics with accessibility testing for screen readers and keyboard navigation.'
      }
    }
  }
}; 