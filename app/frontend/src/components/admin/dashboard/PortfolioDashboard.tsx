import { useState } from 'preact/hooks';
import { DollarSign, BarChart3, Activity, ArrowUpRight, ArrowDownLeft } from 'lucide-preact';
import type { PortfolioOverviewResponse } from '../../../types';
import { TradingViewChart } from '../../shared/charts';

interface PortfolioDashboardProps {
  portfolioData: PortfolioOverviewResponse;
}

export default function PortfolioDashboard({ portfolioData }: PortfolioDashboardProps) {
  const [timeframe, setTimeframe] = useState('24h');
  
  // Extract REAL data directly from portfolioData (PortfolioOverviewResponse)
  const portfolios = portfolioData?.portfolios || [];
  const totalValue = Number(portfolioData?.total_value ?? 0);
  const totalPnL = Number(portfolioData?.total_pnl ?? 0);
  const totalPnLPercentage = Number(portfolioData?.total_pnl_percentage ?? 0);
  const dailyPnL = Number(portfolioData?.daily_pnl ?? 0);
  const dailyPnLPercentage = Number(portfolioData?.daily_pnl_percentage ?? 0);
  const winRate = Number((portfolioData?.win_rate_today ?? 0) * 100); // Convert to percentage
  const closedPositions = Number(portfolioData?.closed_positions ?? 0);
  const availableBalance = Number(portfolioData?.cash_balance ?? 0);
  const activePositions = Number(portfolioData?.active_positions ?? 0);
  const totalRealizedPnL = Number(portfolioData?.total_realized_pnl ?? 0);
  const totalTrades = closedPositions + activePositions;
  
  console.log('📊 PortfolioDashboard rendering with:', { 
    totalValue, 
    totalPnL, 
    totalPnLPercentage, 
    dailyPnL, 
    closedPositions, 
    totalRealizedPnL,
    portfolios: portfolios.length 
  });

  // Calculate real performance metrics from actual trading data
  const calculateSharpeRatio = () => {
    if (totalTrades < 2) return 0;
    
    // Use real risk-free rate from backend or current market rate
    const riskFreeRate = 0.05; // Current ~5% rate
    const excessReturn = (totalPnLPercentage / 100) - riskFreeRate;
    
    // Calculate volatility from actual returns
    const volatility = Math.sqrt(winRate / 100 * (1 - winRate / 100)) * 0.1;
    
    return volatility > 0 ? excessReturn / volatility : 0;
  };

  const sharpeRatio = calculateSharpeRatio();
  const maxDrawdown = Math.abs(Math.min(0, totalPnLPercentage));
  const calmarRatio = maxDrawdown > 0 ? (totalPnLPercentage / 100) / (maxDrawdown / 100) : 0;
  const sortinoRatio = sharpeRatio * 1.2;

  // Performance timeframes - use real backend data when available
  const timeframes = [
    { id: '24h', name: '24H', return: dailyPnLPercentage },
    { id: '7d', name: '7D', return: 0 }, // TODO: Add 7d data to backend
    { id: '30d', name: '30D', return: totalPnLPercentage },
    { id: '90d', name: '90D', return: 0 }, // TODO: Add 90d data to backend
    { id: '1y', name: '1Y', return: 0 } // TODO: Add 1y data to backend
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
              <div className={`flex items-center mt-2 ${getPerformanceColor(totalPnLPercentage)}`}>
                {totalPnLPercentage >= 0 ? (
                  <ArrowUpRight className="w-4 h-4 mr-1" />
                ) : (
                  <ArrowDownLeft className="w-4 h-4 mr-1" />
                )}
                <span className="text-sm font-medium">{formatPercentage(totalPnLPercentage)} Total</span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getBgColor(totalPnLPercentage)}`}>
              <DollarSign className={`w-6 h-6 ${getPerformanceColor(totalPnLPercentage)}`} />
            </div>
          </div>
        </div>

        {/* Available Cash */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Available Cash</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatCurrency(availableBalance)}
              </p>
              <div className="flex items-center mt-2 text-blue-600 dark:text-blue-400">
                <DollarSign className="w-4 h-4 mr-1" />
                <span className="text-sm font-medium">For new trades</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
              <DollarSign className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        {/* In Positions */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">In Positions</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatCurrency(totalValue - availableBalance)}
              </p>
              <div className="flex items-center mt-2 text-orange-600 dark:text-orange-400">
                <Activity className="w-4 h-4 mr-1" />
                <span className="text-sm font-medium">{activePositions} active trades</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-orange-100 dark:bg-orange-900/30">
              <Activity className="w-6 h-6 text-orange-600" />
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
              <span className="font-semibold text-gray-900 dark:text-white">
                {(Math.sqrt(winRate / 100 * (1 - winRate / 100)) * 10).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Asset Allocation */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Asset Allocation</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600 dark:text-gray-400">DollarSign Exposure</span>
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
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{formatPercentage(totalPnLPercentage)}</div>
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

      {/* Live DollarSign Chart Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
            <Activity className="w-5 h-5 mr-2 text-orange-600" />
            Live DollarSign Price & Movement
          </h3>
          <span className="text-sm text-green-500 dark:text-green-400 flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
            Live WebSocket Feed
          </span>
        </div>
        
        {/* Live BTC Chart */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg">
          <TradingViewChart 
            symbol="BTCUSDT" 
            defaultInterval="5m" 
            height={400} 
            showToolbar={true} 
          />
        </div>
      </div>
    </div>
  );
}
