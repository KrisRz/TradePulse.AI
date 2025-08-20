import type { Meta, StoryObj } from '@storybook/preact';
import SystemStatusDashboard from '../../components/admin/system/SystemStatusDashboard';

const meta: Meta<typeof SystemStatusDashboard> = {
  title: 'Admin/SystemStatusDashboard',
  component: SystemStatusDashboard,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: `
# SystemStatus Component

Real-time system monitoring dashboard for TradePulse.AI infrastructure, providing comprehensive health monitoring and performance metrics.

## Features
- **Live System Monitoring**: Real-time status of all critical services
- **Performance Metrics**: CPU, memory, network, and database performance
- **Service Health**: Individual service status with uptime tracking
- **Alert Management**: Critical alerts and warning notifications
- **Resource Usage**: Server resource utilization and capacity planning
- **WebSocket Status**: Live connection monitoring for real-time features
- **AI Model Health**: ML model performance and inference status
- **Database Metrics**: Connection pools, query performance, and storage

## Status Indicators
- **🟢 Healthy**: Service operating normally
- **🟡 Warning**: Service degraded but functional
- **🔴 Critical**: Service down or severely impacted
- **⚪ Unknown**: Status unavailable or checking

## Monitored Services
- **Trading Engine**: Order execution and position management
- **AI Models**: LSTM prediction models and inference pipeline
- **Data Pipeline**: Market data collection and processing
- **WebSocket**: Real-time data streaming connections
- **Database**: PostgreSQL and Redis performance
- **External APIs**: Binance API and market data providers

## Use Cases
- System administration and DevOps monitoring
- Performance optimization and capacity planning
- Incident response and troubleshooting
- SLA monitoring and compliance reporting
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {},
};

export default meta;
type Story = StoryObj<typeof SystemStatus>;

export const Default: Story = {
  parameters: {
    docs: {
      description: {
        story: 'Default SystemStatus dashboard showing healthy system state with all services operational.'
      }
    }
  }
};

export const HealthySystem: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus displaying optimal performance with all systems green and operating within normal parameters.'
      }
    }
  }
};

export const WarningState: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus showing warning conditions with some services experiencing degraded performance but still functional.'
      }
    }
  }
};

export const CriticalAlerts: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus during critical incidents with multiple services down or severely impacted.'
      }
    }
  }
};

export const HighLoad: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus under high load conditions showing resource utilization at capacity.'
      }
    }
  }
};

export const MaintenanceMode: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus during scheduled maintenance with services temporarily unavailable.'
      }
    }
  }
};

export const PerformanceMetrics: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SystemStatus focused on detailed performance metrics and historical data visualization.'
      }
    }
  }
};

export const MobileView: Story = {
  parameters: {
    viewport: {
      defaultViewport: 'mobile1'
    },
    docs: {
      description: {
        story: 'SystemStatus optimized for mobile monitoring with essential metrics highlighted.'
      }
    }
  }
};

export const AccessibilityTest: Story = {
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
        story: 'SystemStatus with accessibility testing for screen readers and keyboard navigation.'
      }
    }
  }
}; 