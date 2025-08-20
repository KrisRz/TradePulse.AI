import { useState, useEffect } from 'preact/hooks';
import { AlertTriangle, RefreshCw, Settings, Eye, EyeOff, TrendingUp, TrendingDown } from 'lucide-preact';

interface TradingViewChartProps {
  symbol?: string;
  interval?: string;
  theme?: 'light' | 'dark';
  locale?: string;
  height?: number;
  width?: string;
  className?: string;
  showVolume?: boolean;
  showSettings?: boolean;
  autosize?: boolean;
}

// Simple Bitcoin price display component
function BitcoinPriceDisplay({ height = 100 }: { height?: number }) {
  const [price, setPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const response = await fetch('/api/live/bitcoin-price');
        if (response.ok) {
          const data = await response.json();
          console.log('🔍 API Response:', data); // Debug log
          
          // Fix: Check for the correct data structure
          if (data.success && data.data && typeof data.data.price === 'number') {
            setPrice(data.data.price);
            setPriceChange(data.data.change_percent || 0);
            setError(null);
            console.log('✅ Price updated:', data.data.price); // Debug log
          } else if (data.price && typeof data.price === 'number') {
            // Fallback for direct price object
            setPrice(data.price);
            setPriceChange(data.change_percent || 0);
            setError(null);
            console.log('✅ Price updated (fallback):', data.price);
          } else {
            console.error('❌ Invalid data structure:', data); // Debug log
            throw new Error('Invalid data format');
          }
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      } catch (err) {
        setError('Failed to load Bitcoin price');
        console.error('Price fetch error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatChange = (change: number) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}%`;
  };

  if (isLoading) {
    return (
      <div 
        className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center flex items-center justify-center"
        style={{ height: `${height}px` }}
      >
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
        <p className="text-gray-600 dark:text-gray-400">Loading Bitcoin price...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center flex items-center justify-center"
        style={{ height: `${height}px` }}
      >
        <AlertTriangle className="w-6 h-6 text-red-500 mr-3" />
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div 
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
      style={{ height: `${height}px` }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-xs">₿</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900 dark:text-white">Bitcoin (BTC)</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">BINANCE:BTCUSDT</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {price ? formatPrice(price) : 'Loading...'}
          </div>
          <div className={`text-sm font-medium ${priceChange >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {formatChange(priceChange)}
          </div>
        </div>
      </div>
    </div>
  );
}

// Professional TradingView Chart Component (Preact-compatible)
function ProfessionalTradingViewChart({ 
  symbol = "BINANCE:BTCUSDT",
  interval = "60",
  theme = "dark",
  height = 400 
}: {
  symbol?: string;
  interval?: string;
  theme?: string;
  height?: number;
}) {
  const [chartError, setChartError] = useState<string | null>(null);

  useEffect(() => {
    // Create TradingView widget script
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      try {
        // @ts-ignore - TradingView global object
        if (window.TradingView) {
          // @ts-ignore
          new window.TradingView.widget({
            "width": "100%",
            "height": height,
            "symbol": symbol,
            "interval": interval,
            "timezone": "Etc/UTC",
            "theme": theme === 'dark' ? 'dark' : 'light',
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_chart",
            "studies": [
              "RSI@tv-basicstudies",
              "MACD@tv-basicstudies"
            ]
          });
        }
      } catch (err) {
        console.error('TradingView widget error:', err);
        setChartError('Failed to load TradingView chart');
      }
    };
    script.onerror = () => {
      setChartError('Failed to load TradingView script');
    };

    document.head.appendChild(script);

    return () => {
      // Cleanup
      if (document.head.contains(script)) {
        document.head.removeChild(script);
      }
    };
  }, [symbol, interval, theme, height]);

  if (chartError) {
    return (
      <div 
        className="bg-gray-50 dark:bg-gray-900 rounded-lg p-8 text-center flex flex-col items-center justify-center"
        style={{ height: `${height}px` }}
      >
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-600 dark:text-red-400 mb-2">{chartError}</p>
        <p className="text-sm text-gray-500">Please check your connection</p>
      </div>
    );
  }

  return (
    <div 
      id="tradingview_chart" 
      className="w-full rounded-lg overflow-hidden"
      style={{ height: `${height}px` }}
    />
  );
}

export default function TradingViewChart({
  symbol = "BINANCE:BTCUSDT",
  interval = "60",
  theme = "dark",
  locale = "en",
  height = 400,
  width = "100%",
  className = "",
  showVolume = true,
  showSettings = true,
  autosize = true
}: TradingViewChartProps) {
  const [showControls, setShowControls] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(theme);
  const [currentInterval, setCurrentInterval] = useState(interval);

  const intervals = [
    { value: "1", label: "1m" },
    { value: "5", label: "5m" },
    { value: "15", label: "15m" },
    { value: "30", label: "30m" },
    { value: "60", label: "1h" },
    { value: "240", label: "4h" },
    { value: "1D", label: "1D" },
    { value: "1W", label: "1W" },
    { value: "1M", label: "1M" }
  ];

  const themes = [
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" }
  ];

  return (
    <div className={`tradingview-chart-container ${className}`}>
      {/* Price Display */}
      <div className="mb-4">
        <BitcoinPriceDisplay height={80} />
      </div>

      {/* Controls Bar */}
      {showControls && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-t-lg p-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Interval Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Interval:</span>
              <select
                value={currentInterval}
                onChange={(e) => setCurrentInterval(e.currentTarget.value)}
                className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {intervals.map((interval) => (
                  <option key={interval.value} value={interval.value}>
                    {interval.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Theme Selector */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme:</span>
              <select
                value={currentTheme}
                onChange={(e) => setCurrentTheme(e.currentTarget.value)}
                className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {themes.map((theme) => (
                  <option key={theme.value} value={theme.value}>
                    {theme.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => window.location.reload()}
            className="flex items-center px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </button>
        </div>
      )}

      {/* Professional TradingView Chart */}
      <div className="relative">
        <ProfessionalTradingViewChart
          symbol={symbol}
          interval={currentInterval}
          theme={currentTheme}
          height={height}
        />

        {/* Settings Toggle */}
        {showSettings && (
          <button
            onClick={() => setShowControls(!showControls)}
            className="absolute top-2 right-2 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors z-20"
            title={showControls ? "Hide Settings" : "Show Settings"}
          >
            {showControls ? <EyeOff className="w-4 h-4" /> : <Settings className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Chart Info */}
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
        <span className="font-medium">BINANCE:BTCUSDT</span> • 
        <span className="ml-1">Real-time Bitcoin price data</span>
      </div>
    </div>
  );
} 