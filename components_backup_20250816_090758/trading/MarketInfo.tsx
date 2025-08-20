import { useState, useEffect } from 'preact/hooks';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  BarChart3, 
  Volume2, 
  Clock, 
  Activity,
  AlertTriangle,
  Info,
  Zap,
  RefreshCw,
  ExternalLink
} from 'lucide-preact';

interface MarketData {
  symbol: string;
  price: number;
  priceChange: number;
  priceChangePercent: number;
  high24h: number;
  low24h: number;
  volume24h: number;
  volumeChange: number;
  trades24h: number;
  marketCap?: number;
  lastUpdate: Date;
}

interface OrderBookData {
  symbol: string;
  bids: [number, number][]; // [price, quantity]
  asks: [number, number][]; // [price, quantity]
  spread: number;
  spreadPercent: number;
}

interface MarketSentiment {
  fearGreedIndex: number;
  bitcoinDominance: number;
  activeAddresses: number;
  networkHashRate: number;
  sentiment: 'EXTREME_FEAR' | 'FEAR' | 'NEUTRAL' | 'GREED' | 'EXTREME_GREED';
}

interface MarketInfoProps {
  symbol?: string;
  showOrderBook?: boolean;
  showSentiment?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export default function MarketInfo({
  symbol = 'BTCUSDT',
  showOrderBook = true,
  showSentiment = true,
  autoRefresh = true,
  refreshInterval = 5000
}: MarketInfoProps) {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
  const [sentiment, setSentiment] = useState<MarketSentiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  useEffect(() => {
    fetchMarketData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchMarketData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [symbol, autoRefresh, refreshInterval]);

  const fetchMarketData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Mock market data - will be replaced with real API calls
      const mockMarketData: MarketData = {
        symbol: symbol,
        price: 65234.67,
        priceChange: 1234.56,
        priceChangePercent: 1.93,
        high24h: 66500.00,
        low24h: 63800.00,
        volume24h: 28450.67,
        volumeChange: 5.67,
        trades24h: 1234567,
        marketCap: 1280000000000, // 1.28T
        lastUpdate: new Date()
      };

      const mockOrderBook: OrderBookData = {
        symbol: symbol,
        bids: [
          [65234.67, 0.54321],
          [65234.66, 1.23456],
          [65234.65, 0.98765],
          [65234.64, 2.11111],
          [65234.63, 0.77777]
        ],
        asks: [
          [65234.68, 0.43210],
          [65234.69, 0.87654],
          [65234.70, 1.56789],
          [65234.71, 0.65432],
          [65234.72, 1.98765]
        ],
        spread: 0.01,
        spreadPercent: 0.00001534
      };

      const mockSentiment: MarketSentiment = {
        fearGreedIndex: 72,
        bitcoinDominance: 52.3,
        activeAddresses: 1045234,
        networkHashRate: 450.5, // EH/s
        sentiment: 'GREED'
      };

      setTimeout(() => {
        setMarketData(mockMarketData);
        setOrderBook(mockOrderBook);
        setSentiment(mockSentiment);
        setLastRefresh(new Date());
        setLoading(false);
      }, 300);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market data');
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatLargeNumber = (num: number) => {
    if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toString();
  };

  const getSentimentColor = (sentiment: MarketSentiment['sentiment']) => {
    switch (sentiment) {
      case 'EXTREME_FEAR': return 'text-red-600 dark:text-red-400';
      case 'FEAR': return 'text-orange-600 dark:text-orange-400';
      case 'NEUTRAL': return 'text-gray-600 dark:text-gray-400';
      case 'GREED': return 'text-green-600 dark:text-green-400';
      case 'EXTREME_GREED': return 'text-purple-600 dark:text-purple-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getSentimentIcon = (sentiment: MarketSentiment['sentiment']) => {
    switch (sentiment) {
      case 'EXTREME_FEAR': return '😨';
      case 'FEAR': return '😰';
      case 'NEUTRAL': return '😐';
      case 'GREED': return '🤑';
      case 'EXTREME_GREED': return '🚀';
      default: return '😐';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading market data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
        <span className="text-red-600 dark:text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Market Information
        </h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchMarketData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh market data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Current Price */}
      {marketData && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {marketData.symbol}
                </h3>
                <div className="flex items-center space-x-2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    ${marketData.price.toLocaleString()}
                  </span>
                  <div className={`flex items-center space-x-1 ${
                    marketData.priceChange >= 0 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {marketData.priceChange >= 0 ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    <span className="font-medium">
                      {marketData.priceChange >= 0 ? '+' : ''}
                      {formatCurrency(marketData.priceChange)}
                    </span>
                    <span className="text-sm">
                      ({marketData.priceChangePercent >= 0 ? '+' : ''}{marketData.priceChangePercent.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="text-right">
              <div className="text-sm text-gray-500 dark:text-gray-400">24h Range</div>
              <div className="font-medium text-gray-900 dark:text-white">
                ${marketData.low24h.toLocaleString()} - ${marketData.high24h.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Market Statistics */}
      {marketData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <Volume2 className="w-5 h-5 text-blue-500 mr-2" />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">24h Volume</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {formatLargeNumber(marketData.volume24h)} BTC
                </div>
                <div className={`text-sm ${
                  marketData.volumeChange >= 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                }`}>
                  {marketData.volumeChange >= 0 ? '+' : ''}{marketData.volumeChange.toFixed(2)}%
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <Activity className="w-5 h-5 text-green-500 mr-2" />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">24h Trades</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {formatLargeNumber(marketData.trades24h)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Avg: {formatLargeNumber(marketData.volume24h / marketData.trades24h)} BTC
                </div>
              </div>
            </div>
          </div>

          {marketData.marketCap && (
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center">
                <BarChart3 className="w-5 h-5 text-purple-500 mr-2" />
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Market Cap</div>
                  <div className="font-bold text-gray-900 dark:text-white">
                    ${formatLargeNumber(marketData.marketCap)}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Rank #1
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Order Book */}
      {showOrderBook && orderBook && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Order Book
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Spread: {formatCurrency(orderBook.spread)}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({orderBook.spreadPercent.toFixed(4)}%)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Asks (Sell Orders) */}
            <div>
              <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">
                Asks (Sell Orders)
              </h4>
              <div className="space-y-1">
                {orderBook.asks.slice(0, 5).reverse().map(([price, quantity], index) => (
                  <div key={index} className="flex justify-between items-center text-sm">
                    <span className="text-red-600 dark:text-red-400 font-mono">
                      ${price.toLocaleString()}
                    </span>
                    <span className="text-gray-900 dark:text-white font-mono">
                      {quantity.toFixed(5)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Bids (Buy Orders) */}
            <div>
              <h4 className="text-sm font-medium text-green-600 dark:text-green-400 mb-2">
                Bids (Buy Orders)
              </h4>
              <div className="space-y-1">
                {orderBook.bids.slice(0, 5).map(([price, quantity], index) => (
                  <div key={index} className="flex justify-between items-center text-sm">
                    <span className="text-green-600 dark:text-green-400 font-mono">
                      ${price.toLocaleString()}
                    </span>
                    <span className="text-gray-900 dark:text-white font-mono">
                      {quantity.toFixed(5)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Market Sentiment */}
      {showSentiment && sentiment && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Market Sentiment
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl mb-2">{getSentimentIcon(sentiment.sentiment)}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Fear & Greed Index</div>
              <div className={`text-2xl font-bold ${getSentimentColor(sentiment.sentiment)}`}>
                {sentiment.fearGreedIndex}
              </div>
              <div className={`text-sm capitalize ${getSentimentColor(sentiment.sentiment)}`}>
                {sentiment.sentiment.replace('_', ' ')}
              </div>
            </div>

            <div className="text-center">
              <div className="text-2xl mb-2">₿</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">BTC Dominance</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {sentiment.bitcoinDominance.toFixed(1)}%
              </div>
            </div>

            <div className="text-center">
              <div className="text-2xl mb-2">🏠</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Active Addresses</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatLargeNumber(sentiment.activeAddresses)}
              </div>
            </div>

            <div className="text-center">
              <div className="text-2xl mb-2">⚡</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Network Hash Rate</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {sentiment.networkHashRate.toFixed(1)} EH/s
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trading Insights */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3" />
          <div>
            <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
              Trading Insights
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
              <li>• High volume suggests strong market interest</li>
              <li>• Low spread indicates good liquidity</li>
              <li>• Current sentiment is {sentiment?.sentiment.toLowerCase().replace('_', ' ')} based on Fear & Greed Index</li>
              <li>• Consider risk management in volatile market conditions</li>
            </ul>
          </div>
        </div>
      </div>

      {/* External Links */}
      <div className="flex justify-center space-x-4">
        <a
          href={`https://www.binance.com/en/trade/${symbol}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
        >
          <ExternalLink className="w-4 h-4 mr-2" />
          Trade on Binance
        </a>
        <a
          href={`https://www.tradingview.com/chart/?symbol=BINANCE:${symbol}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          <ExternalLink className="w-4 h-4 mr-2" />
          View on TradingView
        </a>
      </div>
    </div>
  );
} 