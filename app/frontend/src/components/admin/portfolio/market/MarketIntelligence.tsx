import { useState, useEffect } from 'preact/hooks';
import { Compass, TrendingUp, TrendingDown, Activity, Zap, Globe, BarChart3, AlertCircle } from 'lucide-preact';

interface MarketIntelligenceProps {
  portfolioData: any;
}

export default function MarketIntelligence({ portfolioData }: MarketIntelligenceProps) {
  const [marketData, setMarketData] = useState<any>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('24h');
  const [loading, setLoading] = useState(true);

  // Fetch live market data
  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        const response = await fetch('http://localhost:9001/api/signals/live/bitcoin-price');
        if (response.ok) {
          const data = await response.json();
          setMarketData(data);
        }
      } catch (error) {
        console.error('Error fetching market data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Mock enhanced market intelligence data
  const marketIntelligence = {
    price: marketData?.price || 117287,
    change24h: marketData?.change_24h || 2.34,
    volume24h: 28.5, // Billion USD
    marketCap: 2.31, // Trillion USD
    volatilityIndex: 18.5,
    fearGreedIndex: 74, // 0-100 scale
    dominance: 54.2,
    liquidityScore: 85.3,
    sentimentScore: 68.2,
    technicalScore: 72.1,
    momentumScore: 81.4,
    trendStrength: 7.2, // 0-10 scale
    supportLevel: 115000,
    resistanceLevel: 120000,
    rsi: 58.2,
    macd: 'Bullish',
    bollingerPosition: 'Upper Band',
    volumeProfile: 'High'
  };

  const timeframes = ['1h', '4h', '24h', '7d', '30d'];

  const getSentimentColor = (score: number) => {
    if (score >= 75) return 'text-green-600 dark:text-green-400';
    if (score >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getSentimentBgColor = (score: number) => {
    if (score >= 75) return 'bg-green-100 dark:bg-green-900/30';
    if (score >= 50) return 'bg-yellow-100 dark:bg-yellow-900/30';
    return 'bg-red-100 dark:bg-red-900/30';
  };

  const getFearGreedLabel = (index: number) => {
    if (index >= 75) return 'Extreme Greed';
    if (index >= 55) return 'Greed';
    if (index >= 45) return 'Neutral';
    if (index >= 25) return 'Fear';
    return 'Extreme Fear';
  };

  const getVolatilityLevel = (volatility: number) => {
    if (volatility < 15) return 'Low';
    if (volatility < 25) return 'Medium';
    return 'High';
  };

  const getTrendDirection = (score: number) => {
    if (score >= 6) return 'Strong Bullish';
    if (score >= 4) return 'Bullish';
    if (score >= 3) return 'Neutral';
    if (score >= 1) return 'Bearish';
    return 'Strong Bearish';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatLargeNumber = (num: number, suffix: string) => {
    return `${num.toFixed(1)}${suffix}`;
  };

  const formatPercentage = (percentage: number) => {
    const formatted = percentage.toFixed(2);
    return `${percentage >= 0 ? '+' : ''}${formatted}%`;
  };

  // Market conditions indicators
  const marketConditions = [
    { 
      name: 'Bull Market Signals', 
      indicators: ['RSI > 50', 'MACD Bullish', 'Price > MA200'], 
      status: 'Active',
      strength: 8.2 
    },
    { 
      name: 'Momentum Strength', 
      indicators: ['Volume Increase', 'Breakout Pattern', 'Higher Highs'], 
      status: 'Strong',
      strength: 7.8 
    },
    { 
      name: 'Support Levels', 
      indicators: ['$115K Support', 'Volume Profile', 'Technical Floor'], 
      status: 'Solid',
      strength: 8.5 
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
        <span className="text-gray-600 dark:text-gray-400">Loading market intelligence...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Market Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Bitcoin Price */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Bitcoin Price</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatCurrency(marketIntelligence.price)}
              </p>
              <div className={`flex items-center mt-2 ${marketIntelligence.change24h >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {marketIntelligence.change24h >= 0 ? (
                  <TrendingUp className="w-4 h-4 mr-1" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">{formatPercentage(marketIntelligence.change24h)} 24h</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-orange-100 dark:bg-orange-900/30">
              <Globe className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </div>

        {/* Market Sentiment */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Market Sentiment</p>
              <p className={`text-2xl font-bold mt-1 ${getSentimentColor(marketIntelligence.sentimentScore)}`}>
                {marketIntelligence.sentimentScore.toFixed(0)}/100
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <Activity className="w-4 h-4 mr-1" />
                <span className="text-sm">
                  {marketIntelligence.sentimentScore >= 70 ? 'Bullish' : 
                   marketIntelligence.sentimentScore >= 40 ? 'Neutral' : 'Bearish'}
                </span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getSentimentBgColor(marketIntelligence.sentimentScore)}`}>
              <Compass className={`w-6 h-6 ${getSentimentColor(marketIntelligence.sentimentScore)}`} />
            </div>
          </div>
        </div>

        {/* Volatility Index */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Volatility Index</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {marketIntelligence.volatilityIndex.toFixed(1)}%
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <Zap className="w-4 h-4 mr-1" />
                <span className="text-sm">{getVolatilityLevel(marketIntelligence.volatilityIndex)}</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30">
              <Activity className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>

        {/* Fear & Greed Index */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Fear & Greed</p>
              <p className={`text-2xl font-bold mt-1 ${getSentimentColor(marketIntelligence.fearGreedIndex)}`}>
                {marketIntelligence.fearGreedIndex}
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <BarChart3 className="w-4 h-4 mr-1" />
                <span className="text-sm">{getFearGreedLabel(marketIntelligence.fearGreedIndex)}</span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getSentimentBgColor(marketIntelligence.fearGreedIndex)}`}>
              <BarChart3 className={`w-6 h-6 ${getSentimentColor(marketIntelligence.fearGreedIndex)}`} />
            </div>
          </div>
        </div>
      </div>

      {/* Technical Analysis Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Technical Indicators */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Technical Analysis</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">RSI (14)</span>
              <span className={`font-semibold ${
                marketIntelligence.rsi > 70 ? 'text-red-600' :
                marketIntelligence.rsi > 30 ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {marketIntelligence.rsi.toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">MACD Signal</span>
              <span className={`font-semibold ${
                marketIntelligence.macd === 'Bullish' ? 'text-green-600' : 'text-red-600'
              }`}>
                {marketIntelligence.macd}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Bollinger Bands</span>
              <span className="font-semibold text-gray-900 dark:text-white">{marketIntelligence.bollingerPosition}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Volume Profile</span>
              <span className={`font-semibold ${
                marketIntelligence.volumeProfile === 'High' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {marketIntelligence.volumeProfile}
              </span>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Support Level</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(marketIntelligence.supportLevel)}</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Resistance Level</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(marketIntelligence.resistanceLevel)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Market Metrics */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Market Metrics</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">24h Volume</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                ${formatLargeNumber(marketIntelligence.volume24h, 'B')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Market Cap</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                ${formatLargeNumber(marketIntelligence.marketCap, 'T')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">BTC Dominance</span>
              <span className="font-semibold text-gray-900 dark:text-white">{marketIntelligence.dominance.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Liquidity Score</span>
              <span className="font-semibold text-green-600 dark:text-green-400">{marketIntelligence.liquidityScore.toFixed(1)}%</span>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Trend Strength</span>
                <span className={`font-semibold ${getSentimentColor(marketIntelligence.trendStrength * 10)}`}>
                  {marketIntelligence.trendStrength.toFixed(1)}/10
                </span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Trend Direction</span>
                <span className={`font-semibold ${getSentimentColor(marketIntelligence.trendStrength * 10)}`}>
                  {getTrendDirection(marketIntelligence.trendStrength)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Market Conditions Analysis */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Market Conditions Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {marketConditions.map((condition, index) => (
            <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900 dark:text-white">{condition.name}</h4>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  condition.status === 'Active' || condition.status === 'Strong' || condition.status === 'Solid'
                    ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                }`}>
                  {condition.status}
                </span>
              </div>
              <div className="space-y-2 mb-3">
                {condition.indicators.map((indicator, idx) => (
                  <div key={idx} className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    {indicator}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Strength</span>
                <span className="font-semibold text-gray-900 dark:text-white">{condition.strength.toFixed(1)}/10</span>
              </div>
              <div className="mt-2">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${(condition.strength / 10) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trading Environment Summary */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Trading Environment Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{marketIntelligence.technicalScore.toFixed(0)}%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Technical Score</div>
            <div className="text-xs text-green-600 dark:text-green-400">Strong Signals</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{marketIntelligence.momentumScore.toFixed(0)}%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Momentum Score</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">High Momentum</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{marketIntelligence.liquidityScore.toFixed(0)}%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Liquidity Score</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">High Liquidity</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">Optimal</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Trading Conditions</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">Favorable</div>
          </div>
        </div>
      </div>
    </div>
  );
}
