import type { StorybookConfig } from '@storybook/preact-vite';

const config: StorybookConfig = {
  stories: [
    '../src/**/*.stories.@(js|jsx|ts|tsx|mdx)',
    '../src/**/*.story.@(js|jsx|ts|tsx|mdx)',
  ],
  
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
    '@storybook/addon-docs',
    '@storybook/addon-controls',
    '@storybook/addon-viewport',
    '@storybook/addon-backgrounds',
    '@storybook/addon-measure',
    '@storybook/addon-outline',
    '@storybook/addon-a11y',
  ],
  
  framework: {
    name: '@storybook/preact-vite',
    options: {},
  },
  
  typescript: {
    check: false,
  },
  
  docs: {
    autodocs: 'tag',
    defaultName: 'Documentation',
  },
  
  core: {
    disableTelemetry: true,
  },
  
  viteFinal: async (config) => {
    // Customize Vite config for Storybook
    config.define = {
      ...config.define,
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    };
    
    // Handle path resolution for project modules
    config.resolve = {
      ...config.resolve,
      alias: {
        ...config.resolve?.alias,
        '@': '/src',
        '@/types': '/src/types',
        '@/components': '/src/components',
        '@/lib': '/src/lib',
        '@/contexts': '/src/contexts',
      },
    };
    
    return config;
  },
  
  features: {
    buildStoriesJson: true,
    storyStoreV7: true,
  },
  
  staticDirs: ['../public'],
};

export default config; 