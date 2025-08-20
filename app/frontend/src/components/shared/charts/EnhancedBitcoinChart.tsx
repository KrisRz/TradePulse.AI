import { useState, useEffect } from 'preact/hooks';
import { TrendingUp, TrendingDown, Activity, Wifi, WifiOff, RefreshCw, BarChart3, Zap } from 'lucide-preact';

interface BitcoinData {
  time: string;
  price: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  change: number;
  change_percent: number;
  timestamp: number;
}

interface EnhancedBitcoinChartProps {
  className?: string;
  height?: number;
  updateInterval?: number;
  showVolume?: boolean;
  showStats?: boolean;
}

export default function EnhancedBitcoinChart({ 
  className = '',
  height = 400,
  updateInterval = 3000, // 3 seconds for live updates
  showVolume = true,
  showStats = true
}: EnhancedBitcoinChartProps) {
  const [bitcoinData, setBitcoinData] = useState<BitcoinData[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [changePercent, setChangePercent] = useState<number>(0);
  const [volume24h, setVolume24h] = useState<number>(0);
  const [high24h, setHigh24h] = useState<number>(0);
  const [low24h, setLow24h] = useState<number>(0);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const fetchBitcoinData = async () => {
    try {
      const response = await fetch('/api/live/bitcoin-price');
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.success && result.data) {
          const data = result.data;
          
          const newDataPoint: BitcoinData = {
            time: new Date().toLocaleTimeString('en-US', { 
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            }),
            price: data.price,
            volume: data.volume,
            high: data.high,
            low: data.low,
            open: data.open,
            change: data.change,
            change_percent: data.change_percent,
            timestamp: Date.now()
          };

          setBitcoinData(prev => {
            const updated = [...prev, newDataPoint];
            return updated.slice(-50); // Keep last 50 data points for smoother chart
          });

          setCurrentPrice(data.price);
          setPriceChange(data.change);
          setChangePercent(data.change_percent);
          setVolume24h(data.volume);
          setHigh24h(data.high);
          setLow24h(data.low);
          setConnected(true);
          setError(null);
          setLoading(false);
          setLastUpdate(new Date().toLocaleTimeString());
        }
      }
    } catch (err) {
      setError('Failed to fetch Bitcoin data');
      setConnected(false);
      console.error('Bitcoin data fetch error:', err);
    }
  };

  useEffect(() => {
    fetchBitcoinData();
    const interval = setInterval(fetchBitcoinData, updateInterval);
    return () => clearInterval(interval);
  }, [updateInterval]);

  // Helper functions
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(2)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(2)}K`;
    return volume.toFixed(2);
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  // Chart rendering
  const renderChart = () => {
    if (bitcoinData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>Loading price data...</p>
          </div>
        </div>
      );
    }

    const prices = bitcoinData.map(d => d.price);
    const maxPrice = Math.max(...prices);
    const minPrice = Math.min(...prices);
    const priceRange = maxPrice - minPrice;
    
    const chartHeight = height - 120; // Leave space for stats
    const chartWidth = 100; // percentage

    const getY = (price: number) => {
      if (priceRange === 0) return chartHeight / 2;
      return ((maxPrice - price) / priceRange) * chartHeight;
    };

    const getX = (index: number) => {
      if (bitcoinData.length <= 1) return index === 0 ? 0 : 100;
      return (index / (bitcoinData.length - 1)) * chartWidth;
    };

    const pathData = bitcoinData.map((d, i) => 
      `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.price)}`
    ).join(' ');

    const areaData = `M 0 ${chartHeight} L ${pathData.replace('M', '').trim()} L ${chartWidth} ${chartHeight} Z`;

    const isPositive = changePercent >= 0;
    const strokeColor = isPositive ? '#10b981' : '#ef4444';
    const fillColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    return (
      <div className="relative">
        <svg width="100%" height={chartHeight} className="overflow-visible">
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          
          {/* Price area */}
          <path
            d={areaData}
            fill={fillColor}
            stroke="none"
          />
          
          {/* Price line */}
          <path
            d={pathData}
            fill="none"
            stroke={strokeColor}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          
          {/* Price points */}
          {bitcoinData.map((d, i) => (
            <circle
              key={i}
              cx={getX(i)}
              cy={getY(d.price)}
              r="3"
              fill={strokeColor}
              opacity="0.8"
            />
          ))}
          
          {/* Current price indicator */}
          {bitcoinData.length > 0 && (
            <g>
              <circle
                cx={getX(bitcoinData.length - 1)}
                cy={getY(currentPrice)}
                r="6"
                fill={strokeColor}
                stroke="white"
                strokeWidth="2"
              />
              <circle
                cx={getX(bitcoinData.length - 1)}
                cy={getY(currentPrice)}
                r="10"
                fill={strokeColor}
                opacity="0.3"
                className="animate-ping"
              />
            </g>
          )}
        </svg>
        
        {/* Price labels */}
        <div className="absolute top-2 left-2 text-xs font-mono text-gray-600 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 px-2 py-1 rounded backdrop-blur-sm">
          High: {formatPrice(maxPrice)}
        </div>
        <div className="absolute bottom-2 left-2 text-xs font-mono text-gray-600 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 px-2 py-1 rounded backdrop-blur-sm">
          Low: {formatPrice(minPrice)}
        </div>
        <div className="absolute bottom-2 right-2 text-xs font-mono text-gray-600 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 px-2 py-1 rounded backdrop-blur-sm">
          {bitcoinData.length} points
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-blue-500" />
            <p className="text-gray-600 dark:text-gray-400">Loading Bitcoin data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center mr-3">
            <span className="text-white font-bold text-sm">₿</span>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Bitcoin (BTC/USDT)</h3>
            <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
              {connected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500 mr-1" />
                  <span>Live • Last update: {lastUpdate}</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-500 mr-1" />
                  <span>Disconnected</span>
                </>
              )}
            </div>
          </div>
        </div>
        
        {/* Real-time price display */}
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatPrice(currentPrice)}
          </div>
          <div className={`flex items-center justify-end text-sm font-medium ${
            changePercent >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {changePercent >= 0 ? (
              <TrendingUp className="h-4 w-4 mr-1" />
            ) : (
              <TrendingDown className="h-4 w-4 mr-1" />
            )}
            {formatPercent(changePercent)} ({formatPrice(priceChange)})
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="mb-6">
        {renderChart()}
      </div>

      {/* Statistics */}
      {showStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">24h High</div>
            <div className="text-sm font-semibold text-green-600">{formatPrice(high24h)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">24h Low</div>
            <div className="text-sm font-semibold text-red-600">{formatPrice(low24h)}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">24h Volume</div>
            <div className="text-sm font-semibold text-gray-900 dark:text-white">{formatVolume(volume24h)} BTC</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Price Change</div>
            <div className={`text-sm font-semibold ${changePercent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPrice(priceChange)}
            </div>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center text-red-700 dark:text-red-400">
            <Activity className="h-4 w-4 mr-2" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
} 