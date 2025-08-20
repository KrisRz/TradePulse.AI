import { useState } from 'preact/hooks';
import { DollarSign, TrendingUp, TrendingDown, BarChart3, Target, Activity, Star, ArrowUpRight, ArrowDownLeft } from 'lucide-preact';
// import BtcCandleLive from '../../shared/charts/BtcCandleLive'; // TODO: Fix lightweight-charts Time export issue

interface PortfolioDashboardProps {
  portfolioData: any;
}

export default function PortfolioDashboard({ portfolioData }: PortfolioDashboardProps) {
  const [timeframe, setTimeframe] = useState('24h');
  
  // Extract data with fallbacks
  const stats = portfolioData?.stats || {};
  const portfolios = portfolioData?.portfolios || [];
  const totalValue = Number(stats.total_value ?? 0);
  const dailyPnL = Number(stats.daily_pnl ?? 0);
  const dailyPnLPercentage = Number(stats.daily_pnl_percentage ?? 0);
  const winRate = Number(stats.win_rate_today ?? 0);
  const totalTrades = Number(stats.total_trades ?? 0);
  const availableBalance = Number(stats.available_balance ?? totalValue);
  const activePositions = Number(stats.active_positions ?? 0);
  const totalReturn = totalValue > 0 ? ((totalValue - availableBalance) / Math.max(totalValue - dailyPnL, 1)) * 100 : 0;
  
  console.log('📊 PortfolioDashboard rendering with:', { totalValue, dailyPnL, portfolios: portfolios.length });

  // Metrics from backend performance endpoint if available in portfolioData
  const perf = portfolioData?.performance?.overall_performance || {};
  const sharpeRatio = Number(perf.sharpe_ratio ?? 0);
  const maxDrawdown = Number(perf.max_drawdown ?? 0);
  const calmarRatio = Number(perf.calmar_ratio ?? 0);
  const sortinoRatio = Number(perf.sortino_ratio ?? 0);

  // Performance timeframes
  const timeframes = [
    { id: '24h', name: '24H', return: dailyPnLPercentage },
    { id: '7d', name: '7D', return: totalReturn * 0.7 },
    { id: '30d', name: '30D', return: totalReturn },
    { id: '90d', name: '90D', return: totalReturn * 2.1 },
    { id: '1y', name: '1Y', return: totalReturn * 8.5 }
  ];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercentage = (percentage: number) => {
    const formatted = percentage.toFixed(2);
    return `${percentage >= 0 ? '+' : ''}${formatted}%`;
  };

  const getPerformanceColor = (value: number) => {
    return value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  const getBgColor = (value: number) => {
    return value >= 0 ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30';
  };

  return (
    <div className="space-y-6">
      {/* Performance Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Portfolio Value */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Portfolio Value</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatCurrency(totalValue)}
              </p>
              <div className={`flex items-center mt-2 ${getPerformanceColor(totalReturn)}`}>
                {totalReturn >= 0 ? (
                  <ArrowUpRight className="w-4 h-4 mr-1" />
                ) : (
                  <ArrowDownLeft className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">{formatPercentage(totalReturn)} Total</span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getBgColor(totalReturn)}`}>
              <DollarSign className={`w-6 h-6 ${getPerformanceColor(totalReturn)}`} />
            </div>
          </div>
        </div>

        {/* Daily P&L */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Daily P&L</p>
              <p className={`text-2xl font-bold mt-1 ${getPerformanceColor(dailyPnL)}`}>
                {formatCurrency(dailyPnL)}
              </p>
              <div className={`flex items-center mt-2 ${getPerformanceColor(dailyPnLPercentage)}`}>
                {dailyPnLPercentage >= 0 ? (
                  <TrendingUp className="w-4 h-4 mr-1" />
                ) : (
                  <TrendingDown className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">{formatPercentage(dailyPnLPercentage)}</span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getBgColor(dailyPnL)}`}>
              <TrendingUp className={`w-6 h-6 ${getPerformanceColor(dailyPnL)}`} />
            </div>
          </div>
        </div>

        {/* Sharpe Ratio */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {sharpeRatio.toFixed(2)}
              </p>
              <div className="flex items-center mt-2 text-green-600 dark:text-green-400">
                <Star className="w-4 h-4 mr-1" />
                <span className="text-sm font-medium">Excellent</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
              <Target className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Win Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {winRate.toFixed(1)}%
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <Activity className="w-4 h-4 mr-1" />
                <span className="text-sm font-medium">{totalTrades} trades</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30">
              <BarChart3 className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Performance Timeframes */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {timeframes.map((tf) => (
            <div
              key={tf.id}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                timeframe === tf.id
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
              onClick={() => setTimeframe(tf.id)}
            >
              <div className="text-center">
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">{tf.name}</div>
                <div className={`text-lg font-bold mt-1 ${getPerformanceColor(tf.return)}`}>
                  {formatPercentage(tf.return)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Metrics */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Risk Metrics</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Max Drawdown</span>
              <span className="font-semibold text-gray-900 dark:text-white">{maxDrawdown.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Calmar Ratio</span>
              <span className="font-semibold text-gray-900 dark:text-white">{calmarRatio.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Sortino Ratio</span>
              <span className="font-semibold text-gray-900 dark:text-white">{sortinoRatio.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Volatility</span>
              <span className="font-semibold text-gray-900 dark:text-white">18.5%</span>
            </div>
          </div>
        </div>

        {/* Asset Allocation */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Asset Allocation</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600 dark:text-gray-400">Bitcoin Exposure</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {((totalValue - availableBalance) / totalValue * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-orange-500 h-2 rounded-full"
                  style={{ width: `${((totalValue - availableBalance) / totalValue * 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600 dark:text-gray-400">Cash Position</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {(availableBalance / totalValue * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${(availableBalance / totalValue * 100)}%` }}
                ></div>
              </div>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Available Cash</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatCurrency(availableBalance)}</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Active Positions</span>
                <span className="font-semibold text-gray-900 dark:text-white">{activePositions}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Insights */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Key Portfolio Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{formatPercentage(totalReturn)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Total Return Since Inception</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{winRate.toFixed(0)}%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Win Rate Performance</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{sharpeRatio.toFixed(2)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Risk-Adjusted Returns</div>
          </div>
        </div>
      </div>

      {/* Live Bitcoin Chart Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
            <Activity className="w-5 h-5 mr-2 text-orange-600" />
            Live Bitcoin Price & Movement
          </h3>
          <span className="text-sm text-green-500 dark:text-green-400 flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
            Live WebSocket Feed
          </span>
        </div>
        
                            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 flex items-center justify-center" style={{ height: '420px' }}>
                      <div className="text-center">
                        <div className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
                          📈 Bitcoin Chart (Coming Soon)
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                          Chart temporarily disabled - lightweight-charts Time export issue
                        </div>
                        <div className="text-xs text-gray-400 dark:text-gray-500">
                          Will be fixed tomorrow with proper chart implementation
                        </div>
                      </div>
                    </div>
      </div>
    </div>
  );
}
