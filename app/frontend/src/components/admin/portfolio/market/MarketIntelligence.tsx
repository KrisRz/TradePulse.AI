import { useState, useEffect } from 'preact/hooks';
import { TrendingUp, TrendingDown, Activity, BarChart3, Globe, Zap } from 'lucide-preact';
import type { PortfolioOverviewResponse } from '../../../../types';
import { TradingViewChart } from '../../../shared/charts';

interface MarketData {
  market_overview: {
    current_price: number;
    price_change_24h: number;
    price_change_24h_percentage: number;
    volume_24h: number;
    market_cap: number;
    dominance: number;
  };
  technical_analysis: {
    trend: string;
    support_level: number;
    resistance_level: number;
    rsi: number;
    macd_signal: string;
    volume_trend: string;
    volatility: number;
  };
  sentiment_analysis: {
    overall_sentiment: string;
    fear_greed_index: number;
    social_sentiment: string;
    news_sentiment: number;
  };
  market_conditions: {
    liquidity: string;
    volatility_regime: string;
    trading_session: string;
    market_phase: string;
  };
  key_levels: {
    daily_high: number;
    daily_low: number;
    weekly_high: number;
    weekly_low: number;
    pivot_point: number;
    fibonacci_levels: {
      [key: string]: number;
    };
  };
  alerts: Array<{
    type: string;
    message: string;
    severity: string;
    timestamp: string;
  }>;
  last_updated: string;
}

interface MarketIntelligenceProps {
  portfolioData: PortfolioOverviewResponse | null;
}

export default function MarketIntelligence({ }: MarketIntelligenceProps) {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch live market data
  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        // Fetch comprehensive market intelligence data
        const response = await fetch('http://localhost:9002/api/signals/market-intelligence');
        if (response.ok) {
          const data = await response.json();
          setMarketData(data);
          console.log('✅ Real market intelligence data loaded:', data);
        } else {
          console.error('Failed to fetch market intelligence:', response.status);
          setMarketData(null);
        }
      } catch (error) {
        console.error('Error fetching market data:', error);
        setMarketData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Real enhanced market intelligence data from backend
  const marketIntelligence = {
    price: marketData?.market_overview?.current_price || 0,
    change24h: marketData?.market_overview?.price_change_24h || 0,
    change24hPercentage: marketData?.market_overview?.price_change_24h_percentage || 0,
    volume24h: marketData?.market_overview?.volume_24h || 0,
    marketCap: marketData?.market_overview?.market_cap || 0,
    dominance: marketData?.market_overview?.dominance || 0,
    volatilityIndex: marketData?.technical_analysis?.volatility || 0,
    fearGreedIndex: marketData?.sentiment_analysis?.fear_greed_index || 0,
    sentimentScore: marketData?.sentiment_analysis?.news_sentiment ? marketData.sentiment_analysis.news_sentiment * 100 : 0,
    technicalScore: marketData?.technical_analysis?.rsi || 0,
    supportLevel: marketData?.technical_analysis?.support_level || 0,
    resistanceLevel: marketData?.technical_analysis?.resistance_level || 0,
    rsi: marketData?.technical_analysis?.rsi || 0,
    macd: marketData?.technical_analysis?.macd_signal || 'Neutral',
    trend: marketData?.technical_analysis?.trend || 'NEUTRAL',
    volumeTrend: marketData?.technical_analysis?.volume_trend || 'Normal',
    marketPhase: marketData?.market_conditions?.market_phase || 'NEUTRAL',
    liquidity: marketData?.market_conditions?.liquidity || 'MEDIUM',
    volatilityRegime: marketData?.market_conditions?.volatility_regime || 'NORMAL',
    tradingSession: marketData?.market_conditions?.trading_session || 'ACTIVE',
    dailyHigh: marketData?.key_levels?.daily_high || 0,
    dailyLow: marketData?.key_levels?.daily_low || 0,
    weeklyHigh: marketData?.key_levels?.weekly_high || 0,
    weeklyLow: marketData?.key_levels?.weekly_low || 0,
    pivotPoint: marketData?.key_levels?.pivot_point || 0,
    fibonacciLevels: marketData?.key_levels?.fibonacci_levels || {}
  };

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

  // Market conditions indicators based on real data
  const marketConditions = [
    { 
      name: `${marketIntelligence.trend} Market Signals`, 
      indicators: [
        `RSI ${marketIntelligence.rsi > 50 ? '>' : '<'} 50`, 
        `MACD ${marketIntelligence.macd}`, 
        `Trend: ${marketIntelligence.trend}`
      ], 
      status: marketIntelligence.trend === 'BULLISH' ? 'Active' : marketIntelligence.trend === 'BEARISH' ? 'Declining' : 'Neutral',
      strength: marketIntelligence.technicalScore / 10 
    },
    { 
      name: 'Volume Analysis', 
      indicators: [
        `Volume Trend: ${marketIntelligence.volumeTrend}`, 
        `24h Volume: ${marketIntelligence.volume24h.toFixed(0)}`, 
        `Liquidity: ${marketIntelligence.liquidity}`
      ], 
      status: marketIntelligence.volumeTrend === 'INCREASING' ? 'Strong' : 'Normal',
      strength: marketIntelligence.volumeTrend === 'INCREASING' ? 7.8 : 5.5 
    },
    { 
      name: 'Key Levels', 
      indicators: [
        `Support: ${formatCurrency(marketIntelligence.supportLevel)}`, 
        `Resistance: ${formatCurrency(marketIntelligence.resistanceLevel)}`, 
        `Pivot: ${formatCurrency(marketIntelligence.pivotPoint)}`
      ], 
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
      {/* Live Market Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Live Market Analysis</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">Real-time BTC/USDT with technical indicators</p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-600 dark:text-green-400 font-medium">LIVE DATA</span>
            </div>
          </div>
        </div>
        <TradingViewChart 
          symbol="BTCUSDT" 
          defaultInterval="15m" 
          height={500} 
          showToolbar={true} 
        />
      </div>

      {/* Market Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* DollarSign Price */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">DollarSign Price</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatCurrency(marketIntelligence.price)}
              </p>
              <div className={`flex items-center mt-2 ${marketIntelligence.change24hPercentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {marketIntelligence.change24hPercentage >= 0 ? (
                  <TrendingUp className="w-4 h-4 mr-1" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">{formatPercentage(marketIntelligence.change24hPercentage)} 24h</span>
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
              <Activity className={`w-6 h-6 ${getSentimentColor(marketIntelligence.sentimentScore)}`} />
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
              <span className="text-gray-600 dark:text-gray-400">Market Phase</span>
              <span className="font-semibold text-gray-900 dark:text-white">{marketIntelligence.marketPhase}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Volume Trend</span>
              <span className={`font-semibold ${
                marketIntelligence.volumeTrend === 'INCREASING' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {marketIntelligence.volumeTrend}
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
                {formatLargeNumber(marketIntelligence.volume24h / 1000000000, 'B')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Market Cap</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                ${formatLargeNumber(marketIntelligence.marketCap / 1000000000000, 'T')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">BTC Dominance</span>
              <span className="font-semibold text-gray-900 dark:text-white">{marketIntelligence.dominance.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Liquidity</span>
              <span className="font-semibold text-green-600 dark:text-green-400">{marketIntelligence.liquidity}</span>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Volatility Regime</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {marketIntelligence.volatilityRegime}
                </span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Trading Session</span>
                <span className="font-semibold text-green-600 dark:text-green-400">
                  {marketIntelligence.tradingSession}
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
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{marketIntelligence.rsi.toFixed(0)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">RSI Score</div>
            <div className="text-xs text-green-600 dark:text-green-400">{marketIntelligence.rsi > 50 ? 'Bullish' : 'Bearish'}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{marketIntelligence.fearGreedIndex}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Fear & Greed</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">{getFearGreedLabel(marketIntelligence.fearGreedIndex)}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{marketIntelligence.liquidity}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Liquidity</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">Market Depth</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{marketIntelligence.trend}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Market Trend</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">{marketIntelligence.marketPhase}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
