import { useEffect, useRef, useState } from 'preact/hooks';

interface TradingChartProps {
  symbol?: string;
  interval?: string;
  theme?: 'light' | 'dark';
  className?: string;
  showToolbar?: boolean;
  showSignalOverlay?: boolean;
  height?: number;
  autosize?: boolean;
}

export function TradingChart({
  symbol = 'BTCUSDT',
  interval = '1',
  theme = 'dark',
  className = '',
  showToolbar = true,
  showSignalOverlay = true,
  height = 600,
  autosize = true
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert internal symbol to TradingView format
  const getTradingViewSymbol = (symbol: string) => {
    if (symbol === 'BTCUSDT') return 'BINANCE:BTCUSDT';
    if (symbol === 'ETHUSDT') return 'BINANCE:ETHUSDT';
    return `BINANCE:${symbol}`;
  };

  const loadTradingViewScript = () => {
    return new Promise((resolve, reject) => {
      if (window.TradingView) {
        resolve(window.TradingView);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/tv.js';
      script.async = true;
      script.onload = () => {
        if (window.TradingView) {
          resolve(window.TradingView);
        } else {
          reject(new Error('TradingView failed to load'));
        }
      };
      script.onerror = () => reject(new Error('Failed to load TradingView script'));
      document.head.appendChild(script);
    });
  };

  const initChart = async () => {
    if (!containerRef.current) return;

    try {
      setError(null);
      const TradingView = await loadTradingViewScript();
      
      chartRef.current = new TradingView.widget({
        width: autosize ? '100%' : 980,
        height: height,
        symbol: getTradingViewSymbol(symbol),
        interval: interval,
        timezone: 'Etc/UTC',
        theme: theme,
        style: '1',
        locale: 'en',
        toolbar_bg: theme === 'dark' ? '#1f2937' : '#ffffff',
        enable_publishing: false,
        allow_symbol_change: true,
        container_id: containerRef.current.id,
        autosize: autosize,
        studies: [
          'RSI@tv-basicstudies',
          'MACD@tv-basicstudies',
          'BB@tv-basicstudies',
          'Volume@tv-basicstudies'
        ],
        studies_overrides: {
          'volume.volume.color.0': theme === 'dark' ? '#ef4444' : '#dc2626',
          'volume.volume.color.1': theme === 'dark' ? '#22c55e' : '#16a34a',
          'RSI.RSI.color': theme === 'dark' ? '#a78bfa' : '#8b5cf6',
          'MACD.MACD.color': theme === 'dark' ? '#3b82f6' : '#2563eb',
          'MACD.signal.color': theme === 'dark' ? '#f59e0b' : '#d97706',
          'BB.upper.color': theme === 'dark' ? '#64748b' : '#475569',
          'BB.lower.color': theme === 'dark' ? '#64748b' : '#475569',
          'BB.basis.color': theme === 'dark' ? '#94a3b8' : '#64748b'
        },
        overrides: {
          'paneProperties.background': theme === 'dark' ? '#111827' : '#ffffff',
          'paneProperties.backgroundGradientStartColor': theme === 'dark' ? '#111827' : '#ffffff',
          'paneProperties.backgroundGradientEndColor': theme === 'dark' ? '#111827' : '#ffffff',
          'paneProperties.backgroundType': 'solid',
          'paneProperties.vertGridProperties.color': theme === 'dark' ? '#374151' : '#e5e7eb',
          'paneProperties.horzGridProperties.color': theme === 'dark' ? '#374151' : '#e5e7eb',
          'symbolWatermarkProperties.transparency': 90,
          'scalesProperties.textColor': theme === 'dark' ? '#d1d5db' : '#374151',
          'scalesProperties.backgroundColor': theme === 'dark' ? '#1f2937' : '#f9fafb',
          'mainSeriesProperties.candleStyle.upColor': '#22c55e',
          'mainSeriesProperties.candleStyle.downColor': '#ef4444',
          'mainSeriesProperties.candleStyle.drawWick': true,
          'mainSeriesProperties.candleStyle.drawBorder': true,
          'mainSeriesProperties.candleStyle.borderColor': theme === 'dark' ? '#374151' : '#d1d5db',
          'mainSeriesProperties.candleStyle.borderUpColor': '#22c55e',
          'mainSeriesProperties.candleStyle.borderDownColor': '#ef4444',
          'mainSeriesProperties.candleStyle.wickUpColor': '#22c55e',
          'mainSeriesProperties.candleStyle.wickDownColor': '#ef4444'
        },
        disabled_features: showToolbar ? [] : [
          'header_widget',
          'left_toolbar',
          'context_menus',
          'control_bar',
          'timeframes_toolbar'
        ],
        enabled_features: [
          'study_templates',
          'side_toolbar_in_fullscreen_mode',
          'hide_last_na_study_output'
        ]
      });

      // Wait for chart to load
      chartRef.current.onChartReady(() => {
        setIsLoaded(true);
        
        // Add AI signal overlay if enabled
        if (showSignalOverlay) {
          addSignalOverlay();
        }
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chart');
    }
  };

  const addSignalOverlay = () => {
    if (!chartRef.current) return;

    try {
      // Mock AI signals for demonstration
      const mockSignals = [
        { time: Math.floor(Date.now() / 1000) - 1800, type: 'BUY', price: 43567.89, confidence: 0.87 },
        { time: Math.floor(Date.now() / 1000) - 900, type: 'SELL', price: 43621.45, confidence: 0.73 },
        { time: Math.floor(Date.now() / 1000) - 300, type: 'BUY', price: 43589.12, confidence: 0.92 }
      ];

      chartRef.current.chart().createShape(
        { time: mockSignals[0].time, value: mockSignals[0].price },
        {
          shape: 'arrow_up',
          lock: true,
          disableSelection: true,
          disableSave: true,
          disableUndo: true,
          color: '#22c55e',
          text: `AI BUY\n${(mockSignals[0].confidence * 100).toFixed(0)}%`,
          textColor: '#ffffff',
          fontSize: 10
        }
      );

      chartRef.current.chart().createShape(
        { time: mockSignals[1].time, value: mockSignals[1].price },
        {
          shape: 'arrow_down',
          lock: true,
          disableSelection: true,
          disableSave: true,
          disableUndo: true,
          color: '#ef4444',
          text: `AI SELL\n${(mockSignals[1].confidence * 100).toFixed(0)}%`,
          textColor: '#ffffff',
          fontSize: 10
        }
      );

    } catch (err) {
      console.warn('Failed to add signal overlay:', err);
    }
  };

  const changeTimeframe = (newInterval: string) => {
    if (chartRef.current) {
      chartRef.current.chart().setResolution(newInterval);
    }
  };

  const changeSymbol = (newSymbol: string) => {
    if (chartRef.current) {
      chartRef.current.chart().setSymbol(getTradingViewSymbol(newSymbol));
    }
  };

  useEffect(() => {
    const containerId = `tradingview-chart-${Math.random().toString(36).substr(2, 9)}`;
    if (containerRef.current) {
      containerRef.current.id = containerId;
    }
    
    initChart();
    
    return () => {
      if (chartRef.current) {
        try {
          chartRef.current.remove();
        } catch (err) {
          console.warn('Failed to remove chart:', err);
        }
      }
    };
  }, []);

  // Re-initialize chart when theme changes
  useEffect(() => {
    if (isLoaded && chartRef.current) {
      chartRef.current.remove();
      setIsLoaded(false);
      initChart();
    }
  }, [theme]);

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-500 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Chart Loading Error
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error}
          </p>
          <button
            onClick={initChart}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* Chart Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {symbol} Chart
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">Timeframe:</span>
              <select
                value={interval}
                onChange={(e) => changeTimeframe(e.target.value)}
                className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded 
                           bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="1">1m</option>
                <option value="5">5m</option>
                <option value="15">15m</option>
                <option value="30">30m</option>
                <option value="60">1h</option>
                <option value="240">4h</option>
                <option value="1D">1D</option>
              </select>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {showSignalOverlay && (
              <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>AI Signals</span>
              </div>
            )}
            {!isLoaded && (
              <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                <span>Loading...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative">
        <div
          ref={containerRef}
          className="w-full"
          style={{ height: `${height}px` }}
        />
        
        {!isLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-900">
            <div className="text-center">
              <div className="w-8 h-8 mx-auto mb-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
              <p className="text-gray-600 dark:text-gray-400">Loading TradingView Chart...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Extend Window interface to include TradingView
declare global {
  interface Window {
    TradingView: any;
  }
} 