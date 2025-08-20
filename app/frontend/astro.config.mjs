import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import tailwind from '@astrojs/tailwind';
// import node from '@astrojs/node'; // Removed for static build
import { VitePWA } from 'vite-plugin-pwa';

// https://astro.build/config
export default defineConfig({
  site: 'https://tradepulse.ai',
  integrations: [
    preact({
      compat: true,
      include: ['**/*.{tsx,jsx}'],
    }),
    tailwind({
      applyBaseStyles: false,
    }),
  ],
  output: 'static',
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:9002',
          changeOrigin: true,
          secure: false,
          ws: false,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('Proxy error:', err);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log('Proxying request:', req.method, req.url, '→', proxyReq.path);
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log('Proxy response:', proxyRes.statusCode, req.url);
            });
          }
        }
      }
    },
    define: {
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    },
    optimizeDeps: {
      include: ['preact', '@preact/signals', 'preact/hooks'],
      exclude: ['@playwright/test', 'playwright-core', 'playwright']
    },
    resolve: {
      alias: {
        'react': 'preact/compat',
        'react-dom': 'preact/compat',
      },
    },
    build: {
      // Performance optimizations
      rollupOptions: {
        external: [
          '@playwright/test',
          'playwright-core', 
          'playwright',
          'chromium-bidi',
          'fsevents'
        ],
        output: {
          manualChunks: {
            vendor: ['preact', '@preact/signals'],
            auth: ['src/contexts/AuthContext.tsx', 'src/components/auth'],
          },
        },
      },
      chunkSizeWarningLimit: 1000,
    },
    plugins: [
      VitePWA({
        registerType: 'autoUpdate',
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff,woff2}'],
          // Increase cache limit for large background images
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
          // Don't cache extremely large images in service worker
          globIgnores: [
            '**/images/backgrounds/coin.png',
            '**/images/backgrounds/poundslogin.png',
          ],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/api\./,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24, // 24 hours
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com/,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'google-fonts-stylesheets',
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com/,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-webfonts',
                expiration: {
                  maxEntries: 30,
                  maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
                },
              },
            },
            // Cache large background images with runtime strategy
            {
              urlPattern: /\/images\/backgrounds\//,
              handler: 'CacheFirst',
              options: {
                cacheName: 'background-images',
                expiration: {
                  maxEntries: 20,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
          ],
        },
        includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
        manifest: {
          name: 'TradePulse.AI - AI-Powered Crypto Trading',
          short_name: 'TradePulse.AI',
          description: 'AI-powered crypto day trading platform with real-time signals and virtual portfolio management.',
          theme_color: '#3b82f6',
          background_color: '#ffffff',
          display: 'standalone',
          orientation: 'portrait-primary',
          scope: '/',
          start_url: '/',
          icons: [
            {
              src: '/icons/icon-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'maskable any'
            },
            {
              src: '/icons/icon-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable any'
            }
          ],
          shortcuts: [
            {
              name: 'Dashboard',
              short_name: 'Dashboard',
              description: 'View portfolio and trading dashboard',
              url: '/dashboard',
              icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }]
            },
            {
              name: 'Signals',
              short_name: 'Signals',
              description: 'View AI trading signals',
              url: '/dashboard/signals',
              icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }]
            }
          ]
        },
        devOptions: {
          enabled: true,
          type: 'module',
        },
      }),
    ],
  },
  server: {
    port: 4321,
    host: '0.0.0.0',
    hmr: {
      port: 4321,
    },
  },
  build: {
    assets: 'assets',
    inlineStylesheets: 'auto',
    split: true,
    exclude: [
      'src/test/**/*',
      '**/*.test.ts',
      '**/*.test.tsx', 
      '**/*.spec.ts',
      '**/*.spec.tsx',
      'playwright-report/**/*',
      'test-results/**/*'
    ]
  },
}); 