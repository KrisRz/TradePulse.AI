import { useState, useEffect, useRef } from 'preact/hooks';
import { 
  LineChart, TrendingUp, TrendingDown, BarChart3, Activity, RefreshCw,
  Maximize2, Settings, Volume2, Target, Clock, Zap, AlertTriangle
} from 'lucide-preact';

interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartProps {
  width?: number;
  height?: number;
}

export default function LiveBitcoinChart({ width = 800, height = 400 }: ChartProps) {
  const [candleData, setCandleData] = useState<CandleData[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0);
  const [timeframe, setTimeframe] = useState('1m');
  const [volume, setVolume] = useState<number>(0);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showMA, setShowMA] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [error, setError] = useState<string | null>(null);
  
  const chartRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Timeframe options
  const timeframes = [
    { id: '1m', label: '1m', interval: 2000 },
    { id: '5m', label: '5m', interval: 5000 },
    { id: '15m', label: '15m', interval: 15000 },
    { id: '1h', label: '1h', interval: 60000 },
    { id: '4h', label: '4h', interval: 240000 },
    { id: '1d', label: '1D', interval: 1440000 }
  ];

  // Load initial real data
  useEffect(() => {
    loadRealCandleData();
    loadRealMarketData();
  }, [timeframe]);

  // Real-time updates
  useEffect(() => {
    const currentTimeframe = timeframes.find(tf => tf.id === timeframe);
    const interval = setInterval(() => {
      loadRealMarketData();
    }, currentTimeframe?.interval || 2000);

    return () => clearInterval(interval);
  }, [timeframe]);

  // Draw chart when data changes
  useEffect(() => {
    if (candleData.length > 0 && chartRef.current) {
      drawChart();
    }
  }, [candleData, showVolume, showMA]);

  const loadRealCandleData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`http://localhost:9001/api/real-trading/live/candlestick/${timeframe}?limit=50`, {
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load candlestick data: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.data.candles) {
        const formattedCandles = data.data.candles.map((candle: any) => ({
          timestamp: candle.open_time,
          open: candle.open_price,
          high: candle.high_price,
          low: candle.low_price,
          close: candle.close_price,
          volume: candle.volume
        }));
        
        setCandleData(formattedCandles);
        setConnectionStatus('connected');
        console.log(`✅ Loaded ${formattedCandles.length} real candles for ${timeframe}`);
      }
      
    } catch (error) {
      console.error('❌ Failed to load real candlestick data:', error);
      setError(`Failed to load candlestick data: ${error}`);
      setConnectionStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

  const loadRealMarketData = async () => {
    try {
      const response = await fetch('http://localhost:9001/api/real-trading/live/market-data', {
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load market data: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.data) {
        const marketData = data.data;
        
        if (marketData.current_price) {
          setCurrentPrice(marketData.current_price);
        }
        
        if (marketData.price_change_24h) {
          setPriceChange(marketData.price_change_24h);
        }
        
        if (marketData.price_change_percent_24h) {
          setPriceChangePercent(marketData.price_change_percent_24h);
        }
        
        if (marketData.volume_24h) {
          setVolume(marketData.volume_24h);
        }
        
        setLastUpdate(new Date());
        setConnectionStatus('connected');
        console.log(`🔴 Live price update: $${marketData.current_price?.toLocaleString()}`);
      }
      
    } catch (error) {
      console.error('❌ Failed to load real market data:', error);
      setConnectionStatus('error');
    }
  };

  const drawChart = () => {
    const canvas = chartRef.current;
    if (!canvas || candleData.length === 0) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas size
    canvas.width = width;
    canvas.height = height;
    
    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);
    
    // Chart dimensions
    const padding = 60;
    const chartWidth = width - (padding * 2);
    const chartHeight = showVolume ? height * 0.7 : height - (padding * 2);
    const volumeHeight = showVolume ? height * 0.2 : 0;
    
    // Calculate price range
    const prices = candleData.flatMap(d => [d.high, d.low]);
    const maxPrice = Math.max(...prices);
    const minPrice = Math.min(...prices);
    const priceRange = maxPrice - minPrice;
    
    if (priceRange === 0) return; // Avoid division by zero
    
    // Calculate volume range
    const maxVolume = Math.max(...candleData.map(d => d.volume));
    
    // Draw grid lines
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    
    // Horizontal grid lines
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
      
      // Price labels
      const price = maxPrice - (priceRange / 5) * i;
      ctx.fillStyle = '#666666';
      ctx.font = '12px Arial';
      ctx.textAlign = 'right';
      ctx.fillText(`$${price.toLocaleString()}`, padding - 10, y + 4);
    }
    
    // Vertical grid lines
    const timeStep = Math.floor(candleData.length / 6);
    for (let i = 0; i < candleData.length; i += timeStep) {
      const x = padding + (chartWidth / (candleData.length - 1)) * i;
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, padding + chartHeight);
      ctx.stroke();
      
      // Time labels
      if (candleData[i]) {
        const time = new Date(candleData[i].timestamp);
        ctx.fillStyle = '#666666';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(
          time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          x,
          height - 10
        );
      }
    }
    
    // Draw candlesticks
    const candleWidth = Math.max(2, chartWidth / candleData.length * 0.8);
    
    candleData.forEach((candle, index) => {
      const x = padding + (chartWidth / (candleData.length - 1)) * index;
      
      // Calculate Y positions
      const openY = padding + ((maxPrice - candle.open) / priceRange) * chartHeight;
      const highY = padding + ((maxPrice - candle.high) / priceRange) * chartHeight;
      const lowY = padding + ((maxPrice - candle.low) / priceRange) * chartHeight;
      const closeY = padding + ((maxPrice - candle.close) / priceRange) * chartHeight;
      
      // Determine candle color
      const isGreen = candle.close > candle.open;
      const color = isGreen ? '#10B981' : '#EF4444';
      
      // Draw wick (high-low line)
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();
      
      // Draw body (open-close rectangle)
      ctx.fillStyle = color;
      const bodyTop = Math.min(openY, closeY);
      const bodyHeight = Math.abs(closeY - openY) || 1;
      ctx.fillRect(x - candleWidth/2, bodyTop, candleWidth, bodyHeight);
    });
    
    // Draw moving average if enabled
    if (showMA && candleData.length >= 20) {
      const maData = calculateMovingAverage(candleData, 20);
      ctx.strokeStyle = '#3B82F6';
      ctx.lineWidth = 2;
      ctx.beginPath();
      
      maData.forEach((ma, index) => {
        if (ma !== undefined) {
          const x = padding + (chartWidth / (candleData.length - 1)) * index;
          const y = padding + ((maxPrice - ma) / priceRange) * chartHeight;
          
          if (index === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
      });
      ctx.stroke();
    }
    
    // Draw volume bars if enabled
    if (showVolume && maxVolume > 0) {
      const volumeY = padding + chartHeight + 20;
      const volumeBarHeight = volumeHeight - 30;
      
      candleData.forEach((candle, index) => {
        const x = padding + (chartWidth / (candleData.length - 1)) * index;
        const barHeight = (candle.volume / maxVolume) * volumeBarHeight;
        
        ctx.fillStyle = candle.close > candle.open ? '#10B981' : '#EF4444';
        ctx.fillRect(x - candleWidth/2, volumeY + volumeBarHeight - barHeight, candleWidth, barHeight);
      });
    }
  };

  const calculateMovingAverage = (data: CandleData[], period: number): number[] => {
    const ma: number[] = [];
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        ma.push(data[i].close);
      } else {
        const sum = data.slice(i - period + 1, i + 1).reduce((acc, d) => acc + d.close, 0);
        ma.push(sum / period);
      }
    }
    return ma;
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-600';
      case 'error': return 'text-red-600';
      default: return 'text-yellow-600';
    }
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>;
      case 'error': return <div className="w-2 h-2 bg-red-500 rounded-full"></div>;
      default: return <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Live Data Status */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getConnectionStatusIcon()}
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                🔴 LIVE DATA MODE - Real Binance WebSocket
              </p>
              <p className="text-xs text-green-600 dark:text-green-300">
                {connectionStatus === 'connected' ? 'Real-time Bitcoin price and candlestick data' : 
                 connectionStatus === 'error' ? 'Connection error - check backend' : 'Connecting...'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              loadRealCandleData();
              loadRealMarketData();
            }}
            className="flex items-center px-3 py-1 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh Live Data
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mr-3" />
            <div>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">Live Data Error</p>
              <p className="text-xs text-red-600 dark:text-red-300 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Chart Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Bitcoin (BTC/USDT)</h2>
            <div className="flex items-center space-x-4 mt-2">
              <span className="text-3xl font-bold text-gray-900 dark:text-white">
                ${currentPrice ? currentPrice.toLocaleString() : '--'}
              </span>
              {currentPrice > 0 && (
                <span className={`flex items-center text-lg font-medium ${
                  priceChange >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {priceChange >= 0 ? <TrendingUp className="w-5 h-5 mr-1" /> : <TrendingDown className="w-5 h-5 mr-1" />}
                  {priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)} ({priceChangePercent >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%)
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Volume */}
            <div className="text-right">
              <p className="text-sm text-gray-600 dark:text-gray-400">24h Volume</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                ${volume ? (volume / 1000000).toFixed(2) + 'M' : '--'}
              </p>
            </div>
            
            {/* Last Update */}
            <div className="text-right">
              <p className="text-sm text-gray-600 dark:text-gray-400">Last Update</p>
              <p className={`text-sm font-medium ${getConnectionStatusColor()}`}>
                {lastUpdate.toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>

        {/* Chart Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Timeframe Selector */}
            <div className="flex space-x-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              {timeframes.map((tf) => (
                <button
                  key={tf.id}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    timeframe === tf.id 
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' 
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                  }`}
                  onClick={() => setTimeframe(tf.id)}
                >
                  {tf.label}
                </button>
              ))}
            </div>
            
            {/* Chart Type */}
            <div className="flex items-center space-x-2">
              <LineChart className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-600 dark:text-gray-400">Live Candlestick</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Indicators Toggle */}
            <button
              onClick={() => setShowMA(!showMA)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                showMA 
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              }`}
            >
              MA(20)
            </button>
            
            <button
              onClick={() => setShowVolume(!showVolume)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                showVolume 
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              }`}
            >
              <Volume2 className="w-4 h-4 mr-1 inline" />
              Volume
            </button>
            
            <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
              <Settings className="w-4 h-4" />
            </button>
            
            <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <div ref={containerRef} className="relative">
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mr-4"></div>
              <span className="text-gray-600 dark:text-gray-400">Loading live chart data...</span>
            </div>
          ) : candleData.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <AlertTriangle className="w-12 h-12 mx-auto text-red-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Live Data Available</h3>
                <p className="text-gray-500 dark:text-gray-400">Unable to load live Bitcoin data from backend</p>
              </div>
            </div>
          ) : (
            <canvas 
              ref={chartRef}
              className="w-full border border-gray-200 dark:border-gray-600 rounded"
              style={{ maxWidth: '100%', height: 'auto' }}
            />
          )}
        </div>
      </div>

      {/* Chart Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <TrendingUp className="w-5 h-5 text-green-600 mr-2" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">24h High</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                ${candleData.length > 0 ? Math.max(...candleData.map(d => d.high)).toLocaleString() : '--'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <TrendingDown className="w-5 h-5 text-red-600 mr-2" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">24h Low</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                ${candleData.length > 0 ? Math.min(...candleData.map(d => d.low)).toLocaleString() : '--'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Activity className="w-5 h-5 text-blue-600 mr-2" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Volatility</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                {candleData.length > 0 && currentPrice > 0 ? 
                  (((Math.max(...candleData.map(d => d.high)) - Math.min(...candleData.map(d => d.low))) / currentPrice) * 100).toFixed(2) + '%'
                  : '--'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Clock className="w-5 h-5 text-purple-600 mr-2" />
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Data Source</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                {connectionStatus === 'connected' ? 'Live' : 'Offline'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 