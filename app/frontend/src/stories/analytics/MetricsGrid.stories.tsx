import type { Meta, StoryObj } from '@storybook/preact';
import MetricsGrid from './MetricsGrid';

const meta: Meta<typeof MetricsGrid> = {
  title: 'Analytics/MetricsGrid',
  component: MetricsGrid,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
# MetricsGrid Component

Comprehensive dashboard displaying key performance indicators (KPIs) for AI trading system monitoring.

## Features
- **Real-time Metrics**: Live updates of critical trading performance indicators
- **Grid Layout**: Organized display of multiple KPI cards in responsive grid
- **Visual Indicators**: Color-coded metrics with trend arrows and status icons
- **Interactive Cards**: Click to drill down into detailed metric analysis
- **Customizable View**: Show/hide specific metrics based on user preferences
- **Export Functionality**: Export metrics data for reporting and analysis
- **Threshold Alerts**: Visual warnings when metrics exceed defined limits
- **Historical Comparison**: Compare current metrics with historical periods

## Key Metrics Displayed
- **Portfolio Value**: Current total portfolio value and daily change
- **P&L Today**: Profit/loss for current trading day
- **Win Rate**: Success rate of completed trades
- **Active Positions**: Number of currently open trading positions
- **Daily Trades**: Number of trades executed today
- **AI Confidence**: Average confidence score of recent signals
- **Risk Exposure**: Current risk level and position sizing
- **Sharpe Ratio**: Risk-adjusted performance metric

## Advanced Metrics
- **Maximum Drawdown**: Largest portfolio decline from peak
- **Calmar Ratio**: Annual return vs maximum drawdown
- **Sortino Ratio**: Downside risk-adjusted returns
- **Beta**: Correlation with market movements
- **Alpha**: Risk-adjusted outperformance vs benchmark
- **Volatility**: Standard deviation of returns
- **VaR (Value at Risk)**: Potential loss at confidence level
- **Expected Shortfall**: Average loss beyond VaR threshold

## Status Indicators
- **🟢 Excellent**: Metric performing above targets
- **🟡 Good**: Metric within acceptable range
- **🟠 Warning**: Metric approaching risk thresholds
- **🔴 Critical**: Metric exceeding safety limits

## Use Cases
- Real-time portfolio monitoring
- Performance evaluation and reporting
- Risk management and compliance
- Strategy optimization and analysis
- Client dashboard and transparency
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    timeRange: {
      control: 'select',
      options: ['1d', '7d', '30d', '90d', '1y'],
      description: 'Time period for metrics calculation',
      table: {
        type: { summary: '1d | 7d | 30d | 90d | 1y' },
        defaultValue: { summary: '1d' }
      }
    },
    showAdvanced: {
      control: 'boolean',
      description: 'Show advanced risk and performance metrics',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'false' }
      }
    },
    showAlerts: {
      control: 'boolean',
      description: 'Show alert indicators for threshold breaches',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    refreshInterval: {
      control: 'number',
      description: 'Auto-refresh interval in seconds',
      table: {
        type: { summary: 'number' },
        defaultValue: { summary: '30' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof MetricsGrid>;

export const Default: Story = {
  args: {
    timeRange: '1d',
    showAdvanced: false,
    showAlerts: true,
    refreshInterval: 30
  },
  parameters: {
    docs: {
      description: {
        story: 'Default MetricsGrid showing essential trading KPIs for current day performance.'
      }
    }
  }
};

export const BasicMetrics: Story = {
  args: {
    timeRange: '1d',
    showAdvanced: false,
    showAlerts: false,
    refreshInterval: 60
  },
  parameters: {
    docs: {
      description: {
        story: 'Basic metrics grid without advanced indicators, ideal for overview dashboards.'
      }
    }
  }
};

export const AdvancedMetrics: Story = {
  args: {
    timeRange: '30d',
    showAdvanced: true,
    showAlerts: true,
    refreshInterval: 30
  },
  parameters: {
    docs: {
      description: {
        story: 'Advanced metrics grid with comprehensive risk and performance indicators.'
      }
    }
  }
};

export const WeeklyOverview: Story = {
  args: {
    timeRange: '7d',
    showAdvanced: false,
    showAlerts: true,
    refreshInterval: 60
  },
  parameters: {
    docs: {
      description: {
        story: 'Weekly performance overview with key metrics and trend indicators.'
      }
    }
  }
};

export const MonthlyAnalysis: Story = {
  args: {
    timeRange: '30d',
    showAdvanced: true,
    showAlerts: true,
    refreshInterval: 300
  },
  parameters: {
    docs: {
      description: {
        story: 'Monthly analysis view with comprehensive metrics and risk assessment.'
      }
    }
  }
};

export const AlertsActive: Story = {
  args: {
    timeRange: '1d',
    showAdvanced: false,
    showAlerts: true,
    refreshInterval: 15
  },
  parameters: {
    docs: {
      description: {
        story: 'MetricsGrid showing active alerts and warning states for various KPIs.'
      }
    }
  }
};

export const HighPerformance: Story = {
  args: {
    timeRange: '7d',
    showAdvanced: true,
    showAlerts: true,
    refreshInterval: 30
  },
  parameters: {
    docs: {
      description: {
        story: 'MetricsGrid during high-performance period with all metrics in green zones.'
      }
    }
  }
};

export const RiskManagement: Story = {
  args: {
    timeRange: '30d',
    showAdvanced: true,
    showAlerts: true,
    refreshInterval: 30
  },
  parameters: {
    docs: {
      description: {
        story: 'Risk-focused metrics view emphasizing drawdown, VaR, and exposure limits.'
      }
    }
  }
};

export const MobileView: Story = {
  args: {
    timeRange: '1d',
    showAdvanced: false,
    showAlerts: true,
    refreshInterval: 60
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'MetricsGrid optimized for mobile with simplified layout and essential metrics.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  args: {
    timeRange: '1d',
    showAdvanced: false,
    showAlerts: true,
    refreshInterval: 30
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
        story: 'MetricsGrid with accessibility testing for screen readers and keyboard navigation.'
      }
    }
  }
}; 