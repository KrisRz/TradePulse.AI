import type { Meta, StoryObj } from '@storybook/preact';
import OrderForm from './OrderForm';

// More on how to set up stories at: https://storybook.js.org/docs/preact/writing-stories/introduction
const meta: Meta<typeof OrderForm> = {
  title: 'Trading/OrderForm',
  component: OrderForm,
  parameters: {
    // Optional parameter to center the component in the Canvas. More info: https://storybook.js.org/docs/preact/configure/story-layout
    layout: 'centered',
    docs: {
      description: {
        component: `
# OrderForm Component

Professional dual-sided order form for cryptocurrency trading with real-time validation and risk management.

## Features
- **Dual-sided interface**: BUY and SELL modes
- **Multiple order types**: Market, Limit, Stop, Stop-Limit
- **Real-time validation**: Balance checks, price validation
- **Quick amount buttons**: 25%, 50%, 75%, 100% of balance
- **Cost calculation**: Real-time cost and fee estimation
- **Risk management**: Built-in balance and risk checks
- **Accessibility**: Full keyboard navigation and screen reader support

## Use Cases
- Manual trading execution
- Order placement with risk controls
- Portfolio management interface
- Trading education and simulation
        `
      }
    }
  },
  // This component will have an automatically generated Autodocs entry: https://storybook.js.org/docs/preact/writing-docs/autodocs
  tags: ['autodocs'],
  // More on argTypes: https://storybook.js.org/docs/preact/api/argtypes
  argTypes: {
    symbol: {
      control: 'text',
      description: 'Trading pair symbol (e.g., BTCUSDT, ETHUSDT)',
      table: {
        type: { summary: 'string' },
        defaultValue: { summary: 'BTCUSDT' }
      }
    },
    initialSide: {
      control: 'radio',
      options: ['BUY', 'SELL'],
      description: 'Initial order side selection',
      table: {
        type: { summary: 'BUY | SELL' },
        defaultValue: { summary: 'BUY' }
      }
    },
    maxBalance: {
      control: 'number',
      description: 'Maximum available balance in USDT',
      table: {
        type: { summary: 'number' },
        defaultValue: { summary: '10000' }
      }
    },
    currentPrice: {
      control: 'number',
      description: 'Current market price for the trading pair',
      table: {
        type: { summary: 'number' },
        defaultValue: { summary: '65000' }
      }
    },
    disabled: {
      control: 'boolean',
      description: 'Disable the entire form',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'false' }
      }
    },
    onSubmit: {
      action: 'order-submitted',
      description: 'Callback function called when order is submitted',
      table: {
        type: { summary: '(order: OrderFormData) => void' }
      }
    },
    onCancel: {
      action: 'order-cancelled',
      description: 'Callback function called when order is cancelled',
      table: {
        type: { summary: '() => void' }
      }
    }
  },
};

export default meta;
type Story = StoryObj<typeof OrderForm>;

// More on writing stories with args: https://storybook.js.org/docs/preact/writing-stories/args
export const Default: Story = {
  args: {
    symbol: 'BTCUSDT',
    initialSide: 'BUY',
    maxBalance: 10000,
    currentPrice: 65000,
    disabled: false
  },
  parameters: {
    docs: {
      description: {
        story: 'Default OrderForm with standard configuration for DollarSign trading.'
      }
    }
  }
};

export const SellOrder: Story = {
  args: {
    ...Default.args,
    initialSide: 'SELL',
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm configured for selling DollarSign with red styling for SELL side.'
      }
    }
  }
};

export const HighValueTrading: Story = {
  args: {
    ...Default.args,
    maxBalance: 100000,
    currentPrice: 67500,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm for high-value trading with $100,000 balance and premium DollarSign price.'
      }
    }
  }
};

export const LowBalance: Story = {
  args: {
    ...Default.args,
    maxBalance: 500,
    currentPrice: 65000,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm with low balance ($500) showing validation warnings for insufficient funds.'
      }
    }
  }
};

export const AltcoinTrading: Story = {
  args: {
    ...Default.args,
    symbol: 'ETHUSDT',
    currentPrice: 3200,
    maxBalance: 15000,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm configured for Ethereum trading with different price levels.'
      }
    }
  }
};

export const DisabledState: Story = {
  args: {
    ...Default.args,
    disabled: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm in disabled state, useful for maintenance mode or when trading is paused.'
      }
    }
  }
};

export const BearMarket: Story = {
  args: {
    ...Default.args,
    currentPrice: 35000,
    initialSide: 'SELL',
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm during bear market conditions with lower DollarSign price and sell-focused interface.'
      }
    }
  }
};

export const MinimalBalance: Story = {
  args: {
    ...Default.args,
    maxBalance: 100,
    currentPrice: 65000,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm with minimal balance showing fraction trading capabilities.'
      }
    }
  }
};

// Mobile-specific stories
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
        story: 'OrderForm optimized for mobile devices with touch-friendly interface.'
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
        story: 'OrderForm in mobile landscape orientation.'
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
        story: 'OrderForm optimized for tablet devices.'
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
        story: 'OrderForm with dark theme for night trading sessions.'
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

export const DarkModeSell: Story = {
  args: {
    ...SellOrder.args,
  },
  parameters: {
    backgrounds: {
      default: 'dark',
    },
    docs: {
      description: {
        story: 'Dark mode OrderForm with SELL configuration.'
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

// Error state demonstrations
export const ValidationErrors: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm demonstrating various validation error states. Try submitting without entering a quantity.'
      }
    }
  },
  play: async () => {
    // This would demonstrate interaction testing
    // Note: Requires @storybook/addon-interactions
  }
};

// Loading state
export const LoadingState: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    docs: {
      description: {
        story: 'OrderForm in loading state during order submission.'
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
            id: 'label',
            enabled: true,
          },
          {
            id: 'keyboard-focus',
            enabled: true,
          },
        ],
      },
    },
    docs: {
      description: {
        story: 'OrderForm with accessibility testing enabled. Check the Accessibility panel for WCAG compliance.'
      }
    }
  }
}; 