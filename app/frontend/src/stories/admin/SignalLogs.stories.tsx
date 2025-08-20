import type { Meta, StoryObj } from '@storybook/preact';
import { SignalLogs } from './SignalLogs';

const meta: Meta<typeof SignalLogs> = {
  title: 'Admin/SignalLogs',
  component: SignalLogs,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: `
# SignalLogs Component

Comprehensive admin interface for monitoring and analyzing AI trading signals with detailed breakdown and analytics.

## Features
- **Signal History**: Complete log of all AI-generated trading signals
- **Advanced Filtering**: Filter by type, confidence, date range, and symbol
- **AI Breakdown**: Detailed analysis of each signal's AI decision process
- **Performance Analytics**: Signal success rates, P&L tracking, and accuracy metrics
- **Export Functionality**: Download signal data for external analysis
- **Real-time Updates**: Live signal monitoring with auto-refresh
- **Search & Sort**: Find specific signals with comprehensive search

## AI Signal Breakdown
Each signal includes detailed information about:
- **Market Regime**: Current market conditions and trend strength
- **LSTM Predictions**: Multi-timeframe AI model consensus
- **Reversal Detection**: Technical pattern and volume analysis
- **Smart Filters**: RSI, volume, and disagreement filters
- **Confidence Scoring**: How final confidence score is calculated
- **Adaptive Hold Time**: Recommended position holding duration

## Use Cases
- System administration and monitoring
- Signal performance analysis
- AI model debugging and optimization
- Compliance and audit reporting
        `
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {},
};

export default meta;
type Story = StoryObj<typeof SignalLogs>;

export const Default: Story = {
  parameters: {
    docs: {
      description: {
        story: 'Default SignalLogs interface showing recent AI trading signals with comprehensive analytics and filtering capabilities.'
      }
    }
  }
};

export const HighActivityPeriod: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SignalLogs during a high-activity trading period with multiple signals and enhanced analytics display.'
      }
    }
  }
};

export const FilteredView: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SignalLogs with active filters applied, demonstrating the filtering and search capabilities.'
      }
    }
  }
};

export const DetailedSignalView: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SignalLogs with a signal selected, showing the detailed AI breakdown and decision process analysis.'
      }
    }
  }
};

export const PerformanceAnalytics: Story = {
  parameters: {
    docs: {
      description: {
        story: 'SignalLogs focused on the analytics dashboard showing signal performance metrics and success rates.'
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
        story: 'SignalLogs optimized for mobile devices with responsive design and touch-friendly interface.'
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
        story: 'SignalLogs with accessibility testing enabled for WCAG 2.1 AA compliance verification.'
      }
    }
  }
}; 