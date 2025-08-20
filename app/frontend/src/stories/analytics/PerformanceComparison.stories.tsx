import type { Meta, StoryObj } from '@storybook/preact';
import PerformanceComparison from './PerformanceComparison';

const meta: Meta<typeof PerformanceComparison> = {
  title: 'Analytics/PerformanceComparison',
  component: PerformanceComparison,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
# PerformanceComparison Component

Advanced analytics component comparing AI trading performance against various benchmarks and strategies.

## Features
- **AI vs Human Trading**: Compare AI performance against manual trading strategies
- **Benchmark Comparison**: Performance against market indices and traditional strategies
- **Multi-timeframe Analysis**: Compare performance across different time periods
- **Risk-adjusted Metrics**: Sharpe ratio, Sortino ratio, and risk-adjusted returns
- **Drawdown Analysis**: Maximum drawdown and recovery time comparisons
- **Win Rate Statistics**: Success rate analysis across different market conditions
- **Interactive Charts**: Dynamic visualization with zoom and filter capabilities
- **Export Functionality**: Export comparison data and charts for reporting

## Comparison Metrics
- **Total Return**: Absolute performance over time period
- **Sharpe Ratio**: Risk-adjusted returns calculation
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Average Trade**: Mean profit/loss per trade
- **Best/Worst Trade**: Extreme performance outliers
- **Volatility**: Standard deviation of returns
- **Calmar Ratio**: Annual return vs maximum drawdown

## Benchmark Strategies
- **Buy & Hold**: Simple cryptocurrency holding strategy
- **DCA Strategy**: Dollar-cost averaging approach
- **Random Trading**: Random buy/sell decisions for baseline
- **Technical Analysis**: Traditional TA-based trading
- **Index Following**: Crypto index tracking performance

## Use Cases
- Performance evaluation and reporting
- Strategy validation and optimization
- Investment decision making
- Client reporting and transparency
- Regulatory compliance documentation
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    timeRange: {
      control: 'select',
      options: ['7d', '30d', '90d', '1y', 'all'],
      description: 'Time period for performance comparison',
      table: {
        type: { summary: '7d | 30d | 90d | 1y | all' },
        defaultValue: { summary: '30d' }
      }
    },
    showBenchmarks: {
      control: 'boolean',
      description: 'Show benchmark comparisons',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    showRiskMetrics: {
      control: 'boolean',
      description: 'Display risk-adjusted metrics',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof PerformanceComparison>;

export const Default: Story = {
  args: {
    timeRange: '30d',
    showBenchmarks: true,
    showRiskMetrics: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Default PerformanceComparison showing 30-day AI vs benchmark performance with risk metrics.'
      }
    }
  }
};

export const WeeklyComparison: Story = {
  args: {
    timeRange: '7d',
    showBenchmarks: true,
    showRiskMetrics: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Weekly performance comparison focused on short-term trading results.'
      }
    }
  }
};

export const QuarterlyAnalysis: Story = {
  args: {
    timeRange: '90d',
    showBenchmarks: true,
    showRiskMetrics: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Quarterly performance analysis with comprehensive benchmark and risk metric comparisons.'
      }
    }
  }
};

export const YearlyOverview: Story = {
  args: {
    timeRange: '1y',
    showBenchmarks: true,
    showRiskMetrics: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Annual performance overview showing long-term AI trading effectiveness.'
      }
    }
  }
};

export const BenchmarkFocused: Story = {
  args: {
    timeRange: '30d',
    showBenchmarks: true,
    showRiskMetrics: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Performance comparison focused on benchmark analysis without risk metrics overlay.'
      }
    }
  }
};

export const RiskAnalysis: Story = {
  args: {
    timeRange: '90d',
    showBenchmarks: false,
    showRiskMetrics: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Risk-focused analysis showing drawdown, volatility, and risk-adjusted performance metrics.'
      }
    }
  }
};

export const OutperformingAI: Story = {
  args: {
    timeRange: '30d',
    showBenchmarks: true,
    showRiskMetrics: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Performance comparison showing AI significantly outperforming benchmarks.'
      }
    }
  }
};

export const MobileView: Story = {
  args: {
    timeRange: '30d',
    showBenchmarks: true,
    showRiskMetrics: true
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'PerformanceComparison optimized for mobile viewing with responsive chart design.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  args: {
    timeRange: '30d',
    showBenchmarks: true,
    showRiskMetrics: true
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
        story: 'PerformanceComparison with accessibility testing for color contrast and keyboard navigation.'
      }
    }
  }
}; 