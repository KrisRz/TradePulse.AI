import type { Meta, StoryObj } from '@storybook/preact';
import LiveSignalStatus from './LiveSignalStatus';

const meta: Meta<typeof LiveSignalStatus> = {
  title: 'Signals/LiveSignalStatus',
  component: LiveSignalStatus,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
# LiveSignalStatus Component

Real-time AI trading signal status indicator showing current model health, confidence levels, and signal generation activity.

## Features
- **Real-time Status**: Live AI model health and operational status
- **Confidence Monitoring**: Current AI confidence levels with visual indicators
- **Signal Activity**: Recent signal generation activity and frequency
- **Model Health**: Individual LSTM model status (1h, 4h, 24h timeframes)
- **Connection Status**: WebSocket and data feed connectivity monitoring
- **Alert System**: Visual and audio alerts for critical status changes
- **Performance Metrics**: Real-time accuracy and success rate tracking
- **Latency Monitoring**: Signal generation and execution timing

## Status Indicators
- **🟢 Operational**: All systems running normally
- **🟡 Warning**: Minor issues or degraded performance
- **🔴 Critical**: Major issues requiring attention
- **⚪ Unknown**: Status unavailable or checking
- **🔄 Processing**: Currently generating or processing signals

## AI Model Status
- **LSTM 1h**: Short-term price prediction model
- **LSTM 4h**: Medium-term trend analysis model  
- **LSTM 24h**: Long-term market direction model
- **Ensemble**: Combined model consensus and weighting
- **Market Regime**: Current market condition classifier

## Signal Generation States
- **Active**: Currently generating signals based on market conditions
- **Standby**: Monitoring market but no signals generated
- **Paused**: Signal generation temporarily suspended
- **Error**: Issues with signal generation pipeline
- **Offline**: AI models not responding or unavailable

## Connection Monitoring
- **WebSocket**: Real-time data feed connection status
- **Market Data**: Price and volume data stream health
- **Database**: Signal storage and retrieval system status
- **API Gateway**: External service connectivity
- **Model Inference**: AI prediction service availability

## Use Cases
- Real-time system monitoring dashboard
- Trading desk status displays
- Mobile app status indicators
- Admin panel system health overview
- Client-facing transparency widgets
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    showDetails: {
      control: 'boolean',
      description: 'Show detailed status breakdown',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' }
      }
    },
    showMetrics: {
      control: 'boolean',
      description: 'Display performance metrics',
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
        defaultValue: { summary: '5' }
      }
    },
    compactMode: {
      control: 'boolean',
      description: 'Use compact display mode',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'false' }
      }
    },
    onStatusChange: {
      action: 'status-changed',
      description: 'Callback when system status changes',
      table: {
        type: { summary: '(status: SystemStatus) => void' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof LiveSignalStatus>;

export const Default: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 5,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Default LiveSignalStatus showing comprehensive AI system health and signal generation status.'
      }
    }
  }
};

export const Operational: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 5,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'LiveSignalStatus displaying healthy operational state with all systems green.'
      }
    }
  }
};

export const Warning: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 3,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'LiveSignalStatus showing warning conditions with some system degradation.'
      }
    }
  }
};

export const Critical: Story = {
  args: {
    showDetails: true,
    showMetrics: false,
    refreshInterval: 2,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'LiveSignalStatus displaying critical alerts with system issues requiring immediate attention.'
      }
    }
  }
};

export const CompactMode: Story = {
  args: {
    showDetails: false,
    showMetrics: false,
    refreshInterval: 10,
    compactMode: true
  },
  parameters: {
    docs: {
      description: {
        story: 'Compact LiveSignalStatus for space-constrained layouts with essential status only.'
      }
    }
  }
};

export const DetailedView: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 5,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Detailed LiveSignalStatus view with comprehensive metrics and individual model status.'
      }
    }
  }
};

export const HighFrequency: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 1,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'LiveSignalStatus with high-frequency updates for active trading periods.'
      }
    }
  }
};

export const OfflineMode: Story = {
  args: {
    showDetails: true,
    showMetrics: false,
    refreshInterval: 30,
    compactMode: false
  },
  parameters: {
    docs: {
      description: {
        story: 'LiveSignalStatus showing offline or disconnected state with limited functionality.'
      }
    }
  }
};

export const MobileView: Story = {
  args: {
    showDetails: false,
    showMetrics: true,
    refreshInterval: 10,
    compactMode: true
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'LiveSignalStatus optimized for mobile with compact layout and essential information.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
  args: {
    showDetails: true,
    showMetrics: true,
    refreshInterval: 5,
    compactMode: false
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
        story: 'LiveSignalStatus with accessibility testing for screen readers and status announcements.'
      }
    }
  }
}; 