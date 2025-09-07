import { useState } from 'preact/hooks';
import { ComponentType } from 'react';
import { TrendingUp, Activity, RefreshCw, Wifi, WifiOff, BarChart3, Minus, AlertTriangle } from 'lucide-preact';

// Dynamic import for recharts to handle compatibility issues
interface RechartsComponentsType {
  BarChart3?: ComponentType<Record<string, unknown>>;
  Line?: ComponentType<Record<string, unknown>>;
  XAxis?: ComponentType<Record<string, unknown>>;
  YAxis?: ComponentType<Record<string, unknown>>;
  CartesianGrid?: ComponentType<Record<string, unknown>>;
  Tooltip?: ComponentType<Record<string, unknown>>;
  ResponsiveContainer?: ComponentType<Record<string, unknown>>;
  AreaChart?: ComponentType<Record<string, unknown>>;
  Area?: ComponentType<Record<string, unknown>>;
  BarChart?: ComponentType<Record<string, unknown>>;
  Bar?: ComponentType<Record<string, unknown>>;
  ComposedChart?: ComponentType<Record<string, unknown>>;
}

const RechartsComponents: RechartsComponentsType | null = null;
let chartsLoaded = false;

interface PriceData {
  time: string;
  price: number;
  volume: number;
  timestamp: number;
  high?: number;
  low?: number;
  open?: number;
  close?: number;
  change?: number;
}

interface LiveBitcoinChartProps {
  className?: string;
  height?: number;
  showVolume?: boolean;
  updateInterval?: number;
  chartType?: 'line' | 'candlestick' | 'area';
}

// Fallback Simple Chart Component
function SimplePriceChart({ data, height, priceChange }: { data: PriceData[], height: number, priceChange: number }) {
  // Prevent division by zero and NaN values
  if (data.length === 0) {
    return (
      <div className="relative bg-gray-50 dark:bg-gray-900 rounded-lg p-4 flex items-center justify-center" style={{ height: `${height}px` }}>
        <span className="text-gray-500 dark:text-gray-400">No data available</span>
      </div>
    );
  }

  const maxPrice = Math.max(...data.map(d => d.price));
  const minPrice = Math.min(...data.map(d => d.price));
  const priceRange = maxPrice - minPrice;
  
  const getY = (price: number) => {
    if (priceRange === 0) return height / 2;
    return height - ((price - minPrice) / priceRange) * (height - 40) - 20;
  };

  // Safe coordinate calculation for SVG (no percentages in points)
  const getXCoord = (index: number, width: number = 400) => {
    if (data.length <= 1) return index === 0 ? 0 : width;
    return (index / (data.length - 1)) * width;
  };

  const svgWidth = 400;
  const points = data.map((d, i) => `${getXCoord(i, svgWidth)},${getY(d.price)}`).join(' ');
  
  const color = priceChange > 0 ? '#10b981' : priceChange < 0 ? '#ef4444' : '#f7931a';

  return (
    <div className="relative bg-gray-50 dark:bg-gray-900 rounded-lg p-4" style={{ height: `${height}px` }}>
      <svg width="100%" height="100%" className="absolute inset-0">
        <defs>
          <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: color, stopOpacity: 0.3 }} />
            <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.05 }} />
          </linearGradient>
        </defs>
        
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        
        {/* Price area */}
        <polygon
          points={`0,${height} ${points} ${svgWidth},${height}`}
          fill="url(#priceGradient)"
        />
        
        {/* Price line */}
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Data points */}
        {data.map((d, i) => (
          <circle
            key={i}
            cx={getXCoord(i, svgWidth)}
            cy={getY(d.price)}
            r="2"
            fill={color}
            opacity="0.8"
          />
        ))}
      </svg>
      
      {/* Price labels */}
      <div className="absolute top-2 left-2 text-xs text-gray-500">
        ${maxPrice.toFixed(2)}
      </div>
      <div className="absolute bottom-2 left-2 text-xs text-gray-500">
        ${minPrice.toFixed(2)}
      </div>
      <div className="absolute bottom-2 right-2 text-xs text-gray-500">
        {data.length} points
      </div>
    </div>
  );
}

// Enhanced Chart Component with Error Boundary
function EnhancedChart({ data, height, showVolume, chartType, priceChange }: { 
  data: PriceData[], 
  height: number, 
  showVolume: boolean, 
  chartType: string,
  priceChange: number 
}) {
  const [chartError, setChartError] = useState(false);
  const [recharts, setRecharts] = useState<any>(null);

  useEffect(() => {
    // Try to load recharts dynamically
    const loadRecharts = async () => {
      try {
        const rechartsModule = await import('recharts');
        setRecharts(rechartsModule);
        chartsLoaded = true;
      } catch (error) {
        console.warn('Failed to load recharts, using fallback chart:', error);
        setChartError(true);
      }
    };

    if (!chartsLoaded && !chartError) {
      loadRecharts();
    }
  }, []);

  // Use fallback chart if recharts failed to load or there's an error
  if (chartError || !recharts) {
    return <SimplePriceChart data={data} height={height} priceChange={priceChange} />;
  }

  // Use recharts if available
  try {
    const { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar, Area, Line } = recharts;
    
    const formatCompactPrice = (price: number) => {
      if (price >= 1000000) return `$${(price / 1000000).toFixed(2)}M`;
      if (price >= 1000) return `$${(price / 1000).toFixed(1)}K`;
      return `$${price.toFixed(0)}`;
    };

    const formatPrice = (price: number) => {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(price);
    };

    const formatVolume = (volume: number) => {
      if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
      if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
      return volume.toString();
    };

    const getChartColor = () => {
      if (priceChange > 0) return '#10b981'; // green
      if (priceChange < 0) return '#ef4444'; // red
      return '#f7931a'; // bitcoin orange
    };

    const getGradientId = () => {
      return priceChange > 0 ? 'colorGreen' : priceChange < 0 ? 'colorRed' : 'colorOrange';
    };

    return (
      <div style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <defs>
              <linearGradient id="colorGreen" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
              </linearGradient>
              <linearGradient id="colorRed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05}/>
              </linearGradient>
              <linearGradient id="colorOrange" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f7931a" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#f7931a" stopOpacity={0.05}/>
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
            <XAxis 
              dataKey="time" 
              stroke="#6B7280"
              fontSize={11}
              interval="preserveStartEnd"
              tick={{ fill: '#6B7280' }}
            />
            <YAxis 
              yAxisId="price"
              stroke="#6B7280"
              fontSize={11}
              tickFormatter={formatCompactPrice}
              domain={['dataMin - 50', 'dataMax + 50']}
              tick={{ fill: '#6B7280' }}
            />
            {showVolume && (
              <YAxis 
                yAxisId="volume"
                orientation="right"
                stroke="#6B7280"
                fontSize={10}
                tickFormatter={formatVolume}
                tick={{ fill: '#6B7280' }}
                domain={[0, 'dataMax']}
              />
            )}
            
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                border: '1px solid #374151',
                borderRadius: '12px',
                color: '#F9FAFB',
                boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)'
              }}
              formatter={(value: number, name: string) => {
                if (name === 'price') return [formatPrice(value), 'BTC Price'];
                if (name === 'volume') return [formatVolume(value), 'Volume'];
                return [value, name];
              }}
              labelFormatter={(time: string) => `Time: ${time}`}
            />

            {/* Volume bars at bottom */}
            {showVolume && (
              <Bar 
                dataKey="volume" 
                fill="#374151" 
                opacity={0.3}
                yAxisId="volume"
              />
            )}

            {/* Price area chart */}
            {chartType === 'area' && (
              <Area
                type="monotone"
                dataKey="price"
                stroke={getChartColor()}
                strokeWidth={3}
                fill={`url(#${getGradientId()})`}
                connectNulls={false}
                yAxisId="price"
              />
            )}

            {/* Price line chart */}
            {chartType === 'line' && (
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke={getChartColor()}
                strokeWidth={3}
                dot={false}
                connectNulls={false}
                yAxisId="price"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    );
  } catch (error) {
    console.warn('Recharts rendering error, falling back to simple chart:', error);
    return <SimplePriceChart data={data} height={height} priceChange={priceChange} />;
  }
}

export function LiveBitcoinChart({ 
  className = '',
  height = 400,
  showVolume = true,
  updateInterval = 2000, // 2 seconds for live trading
  chartType = 'area'
}: LiveBitcoinChartProps) {
  const [priceData, setPriceData] = useState<PriceData[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [previousPrice, setPreviousPrice] = useState<number>(0);
  // Enhanced price direction tracking with stronger visual effects
  const [priceDirection, setPriceDirection] = useState<'up' | 'down' | 'neutral'>('neutral');
  const [lastPriceFlash, setLastPriceFlash] = useState<'green' | 'red' | null>(null);
  const [priceVelocity, setPriceVelocity] = useState<number>(0);

  // Calculate price velocity for stronger visual effects
  const calculatePriceVelocity = (currentPrice: number, previousPrice: number) => {
    const change = Math.abs(currentPrice - previousPrice);
    const velocity = change / previousPrice * 10000; // Amplify for visibility
    return Math.min(velocity, 10); // Cap at 10 for reasonable animation
  };

  // Enhanced price direction with flash effect
  const updatePriceDirection = (newPrice: number, oldPrice: number) => {
    const velocity = calculatePriceVelocity(newPrice, oldPrice);
    setPriceVelocity(velocity);
    
    if (newPrice > oldPrice) {
      setPriceDirection('up');
      setLastPriceFlash('green');
      // Optional: Play sound for significant moves
      if (velocity > 2) {
        console.log('🔊 Significant price increase detected');
      }
    } else if (newPrice < oldPrice) {
      setPriceDirection('down');
      setLastPriceFlash('red');
      if (velocity > 2) {
        console.log('🔊 Significant price decrease detected');
      }
    } else {
      setPriceDirection('neutral');
    }
    
    // Clear flash effect after animation
    setTimeout(() => setLastPriceFlash(null), 500);
  };

  // Fetch live DollarSign data with enhanced error handling
  const fetchBitcoinPrice = async () => {
    try {
      // Use direct backend API endpoint with authentication
      const token = localStorage.getItem('auth_token') || 'enterprise_admin_token';
      let response = await fetch('http://localhost:9002/api/trading/market-price/BTCUSDT', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const bitcoinData = await response.json();
        // API response format: {"symbol":"BTCUSDT","price":116668.78,"timestamp":"2025-08-22T19:52:31.279652"}
        const price = bitcoinData.price;
        const change = previousPrice > 0 ? ((price - previousPrice) / previousPrice) * 100 : 0;
        const volume = 1000; // Default volume for display
        const high = price * 1.001;
        const low = price * 0.999;
        const open = price;
          
        // Determine price direction for animations
        if (price > previousPrice) {
          setPriceDirection('up');
        } else if (price < previousPrice) {
          setPriceDirection('down');
        } else {
          setPriceDirection('neutral');
        }
        setPreviousPrice(currentPrice);
          
        const newDataPoint: PriceData = {
            time: new Date().toLocaleTimeString('en-US', { 
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            }),
            price,
            volume,
            timestamp: Date.now(),
            high,
            low,
            open,
            close: price,
            change
        };

        setPriceData(prev => {
          const updated = [...prev, newDataPoint];
          return updated.slice(-60); // Keep last 60 data points for 2-minute window
        });

        setCurrentPrice(price);
        setPriceChange(change);
        setConnected(true);
        setError(null);
        setLoading(false);
        setLastUpdate(new Date().toLocaleTimeString());
        return;
      }
      
      // Fallback to Binance API for live data (direct call as backup)
      response = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT');
      if (!response.ok) {
        throw new Error('Failed to fetch price data');
      }
      
      const data = await response.json();
      const price = parseFloat(data.lastPrice);
      const volume = parseFloat(data.volume);
      const change = parseFloat(data.priceChangePercent);
      const high = parseFloat(data.highPrice);
      const low = parseFloat(data.lowPrice);
      const open = parseFloat(data.openPrice);
      
      // Determine price direction
      if (price > previousPrice) {
        setPriceDirection('up');
      } else if (price < previousPrice) {
        setPriceDirection('down');
      } else {
        setPriceDirection('neutral');
      }
      setPreviousPrice(currentPrice);
      
      const newDataPoint: PriceData = {
        time: new Date().toLocaleTimeString('en-US', { 
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        price,
        volume,
        timestamp: Date.now(),
        high,
        low,
        open,
        close: price,
        change
      };

      setPriceData(prev => {
        const updated = [...prev, newDataPoint];
        return updated.slice(-60); // Keep last 60 data points
      });

      setCurrentPrice(price);
      setPriceChange(change);
      setConnected(true);
      setError(null);
      setLoading(false);
      setLastUpdate(new Date().toLocaleTimeString());
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch price');
      setConnected(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchBitcoinPrice();
    
    // Set up interval for regular updates (faster for day trading)
    const interval = setInterval(fetchBitcoinPrice, updateInterval);
    
    return () => clearInterval(interval);
  }, [updateInterval]);

  // Format price with proper currency formatting
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(2)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(2)}K`;
    return volume.toFixed(2);
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-center" style={{ height: `${height}px` }}>
          <div className="text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-blue-500" />
            <p className="text-gray-600 dark:text-gray-400">Loading DollarSign data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Enhanced Header with Real-time Price */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-orange-600 rounded-full flex items-center justify-center mr-3 shadow-lg">
            <span className="text-white font-bold text-lg">₿</span>
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">DollarSign Live Chart</h3>
            <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
              {connected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500 mr-1" />
                  <span className="font-medium">Live</span>
                  <span className="mx-2">•</span>
                  <span>Updated: {lastUpdate}</span>
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
        
        {/* Enhanced Real-time Price Display with Stronger Animation */}
        <div className="text-right">
          <div className={`text-3xl font-bold transition-all duration-500 relative ${
            priceDirection === 'up' ? 'text-green-600' : 
            priceDirection === 'down' ? 'text-red-600' : 
            'text-gray-900 dark:text-white'
          } ${lastPriceFlash ? 'animate-pulse' : ''}`}>
            {/* Flash background effect */}
            {lastPriceFlash && (
              <div className={`absolute inset-0 rounded-lg ${
                lastPriceFlash === 'green' ? 'bg-green-400/20' : 'bg-red-400/20'
              } animate-ping`} />
            )}
            {formatPrice(currentPrice)}
            
            {/* Movement indicator */}
            {priceDirection !== 'neutral' && (
              <span className={`absolute -top-2 -right-2 text-xs ${
                priceDirection === 'up' ? 'text-green-500' : 'text-red-500'
              }`}>
                {priceDirection === 'up' ? '▲' : '▼'}
              </span>
            )}
          </div>
          
          <div className={`flex items-center justify-end text-lg font-semibold transition-all duration-300 ${
            priceChange >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {priceChange >= 0 ? (
              <TrendingUp className={`h-5 w-5 mr-1 ${priceDirection === 'up' ? 'animate-bounce' : ''}`} />
            ) : (
              <TrendingDown className={`h-5 w-5 mr-1 ${priceDirection === 'down' ? 'animate-bounce' : ''}`} />
            )}
            {formatPercent(priceChange)}
          </div>
          
          {/* Live indicator */}
          <div className="flex items-center justify-end mt-1 text-xs text-gray-500">
            <div className={`w-2 h-2 rounded-full mr-1 ${
              connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span>{connected ? 'LIVE' : 'OFFLINE'}</span>
          </div>
        </div>
      </div>

      {/* Enhanced Chart */}
      <div className="mb-6">
        <EnhancedChart 
          data={priceData} 
          height={height - 120} 
          showVolume={showVolume} 
          chartType={chartType}
          priceChange={priceChange}
        />
      </div>

      {/* Trading Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">Data Points</div>
          <div className="text-lg font-bold text-blue-600">{priceData.length}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">Update Rate</div>
          <div className="text-lg font-bold text-green-600">{updateInterval / 1000}s</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">Status</div>
          <div className={`text-lg font-bold ${connected ? 'text-green-600' : 'text-red-600'}`}>
            {connected ? 'Live' : 'Offline'}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">Chart Type</div>
          <div className="text-lg font-bold text-purple-600 capitalize">{chartType}</div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center text-red-700 dark:text-red-400">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span className="font-medium">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default LiveBitcoinChart; 