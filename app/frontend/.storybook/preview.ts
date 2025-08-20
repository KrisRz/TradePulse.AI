import type { Preview } from '@storybook/preact';
import { themes } from '@storybook/theming';
import '../src/styles/globals.css';

// Mock implementations for Storybook
const mockAuthStore = {
  user: {
    id: '1',
    email: 'demo@tradepulse.ai',
    role: 'user',
    isAuthenticated: true
  },
  login: () => Promise.resolve(),
  logout: () => Promise.resolve(),
  register: () => Promise.resolve(),
  isLoading: false,
  error: null
};

const mockThemeStore = {
  theme: 'light',
  setTheme: (theme: string) => console.log('Set theme:', theme),
  toggleTheme: () => console.log('Toggle theme')
};

// Global decorators
const withAuth = (Story: any) => {
  // Mock AuthContext provider
  return Story();
};

const withTheme = (Story: any, context: any) => {
  const theme = context.globals.theme || 'light';
  
  // Apply theme class to body
  document.body.className = theme === 'dark' ? 'dark' : '';
  
  return Story();
};

const withTradingContext = (Story: any) => {
  // Mock trading context with sample data
  return Story();
};

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
      expanded: true,
    },
    
    docs: {
      theme: themes.light,
      toc: true,
    },
    
    backgrounds: {
      default: 'light',
      values: [
        {
          name: 'light',
          value: '#ffffff',
        },
        {
          name: 'dark',
          value: '#111827',
        },
        {
          name: 'trading-dark',
          value: '#0f172a',
        },
      ],
    },
    
    viewport: {
      viewports: {
        mobile: {
          name: 'Mobile',
          styles: {
            width: '375px',
            height: '667px',
          },
        },
        tablet: {
          name: 'Tablet',
          styles: {
            width: '768px',
            height: '1024px',
          },
        },
        desktop: {
          name: 'Desktop',
          styles: {
            width: '1280px',
            height: '720px',
          },
        },
        largeDesktop: {
          name: 'Large Desktop',
          styles: {
            width: '1920px',
            height: '1080px',
          },
        },
      },
    },
    
    // Layout options
    layout: 'centered',
    
    // Options panel
    options: {
      storySort: {
        order: [
          'Introduction',
          'Design System',
          ['Colors', 'Typography', 'Spacing', 'Icons'],
          'Components',
          ['UI', 'Layout', 'Forms', 'Charts', 'Trading', 'Dashboard', 'Auth', 'Analytics', 'Signals', 'Admin'],
          'Pages',
          'Mobile',
          'Examples',
        ],
      },
    },
  },
  
  globalTypes: {
    theme: {
      description: 'Global theme for components',
      defaultValue: 'light',
      toolbar: {
        title: 'Theme',
        icon: 'paintbrush',
        items: [
          { value: 'light', title: 'Light', icon: 'sun' },
          { value: 'dark', title: 'Dark', icon: 'moon' },
        ],
        dynamicTitle: true,
      },
    },
    
    tradingMode: {
      description: 'Trading interface mode',
      defaultValue: 'demo',
      toolbar: {
        title: 'Trading Mode',
        icon: 'database',
        items: [
          { value: 'demo', title: 'Demo Mode' },
          { value: 'live', title: 'Live Trading' },
          { value: 'backtest', title: 'Backtesting' },
        ],
        dynamicTitle: true,
      },
    },
    
    portfolioValue: {
      description: 'Portfolio value for demos',
      defaultValue: '10000',
      toolbar: {
        title: 'Portfolio',
        icon: 'dollar',
        items: [
          { value: '1000', title: '$1,000' },
          { value: '10000', title: '$10,000' },
          { value: '50000', title: '$50,000' },
          { value: '100000', title: '$100,000' },
        ],
        dynamicTitle: true,
      },
    },
  },
  
  decorators: [
    withAuth,
    withTheme,
    withTradingContext,
    
    // Add responsive wrapper
    (Story, context) => {
      const viewport = context.globals.viewport;
      const isMobile = viewport === 'mobile';
      
      return (
        <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 ${isMobile ? 'p-2' : 'p-4'}`}>
          <div className={`${isMobile ? 'max-w-full' : 'max-w-7xl mx-auto'}`}>
            <Story />
          </div>
        </div>
      );
    },
  ],
  
  args: {
    // Default args for all stories
  },
  
  argTypes: {
    // Global arg types
    className: {
      control: 'text',
      description: 'CSS classes to apply',
      table: {
        type: { summary: 'string' },
        defaultValue: { summary: '""' },
      },
    },
    
    disabled: {
      control: 'boolean',
      description: 'Whether the component is disabled',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'false' },
      },
    },
    
    loading: {
      control: 'boolean',
      description: 'Whether the component is in loading state',
      table: {
        type: { summary: 'boolean' },
        defaultValue: { summary: 'false' },
      },
    },
  },
};

export default preview; 