import { useState, useEffect } from 'preact/hooks';
import { 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart
} from 'recharts';
import { 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Award, 
  AlertTriangle,
  RefreshCw,
  Calendar,
  Brain,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Zap,
  Clock,
  Filter
} from 'lucide-preact';

interface WinRateData {
  strategy: string;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  avgWinAmount: number;
  avgLossAmount: number;
  profitFactor: number;
  largestWin: number;
  largestLoss: number;
  avgWinDuration: number;
  avgLossDuration: number;
  consecutiveWins: number;
  consecutiveLosses: number;
  color: string;
}

interface TimeBasedWinRate {
  period: string;
  winRate: number;
  trades: number;
  avgReturn: number;
  volatility: number;
}

interface MarketConditionWinRate {
  condition: string;
  winRate: number;
  trades: number;
  description: string;
  color: string;
}

interface WinRateAnalysisProps {
  timeRange?: '7d' | '30d' | '90d' | '1y' | 'all';
  groupBy?: 'strategy' | 'timeOfDay' | 'marketCondition' | 'volume';
  showCharts?: boolean;
  showDetails?: boolean;
  onGroupByChange?: (groupBy: string) => void;
}

export default function WinRateAnalysis({
  timeRange = '30d',
  groupBy = 'strategy',
  showCharts = true,
  showDetails = true,
  onGroupByChange
}: WinRateAnalysisProps) {
  const [strategyData, setStrategyData] = useState<WinRateData[]>([]);
  const [timeBasedData, setTimeBasedData] = useState<TimeBasedWinRate[]>([]);
  const [marketConditionData, setMarketConditionData] = useState<MarketConditionWinRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);

  useEffect(() => {
    fetchWinRateData();
  }, [timeRange, groupBy]);

  const fetchWinRateData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Generate mock strategy win rate data
      const mockStrategyData: WinRateData[] = [
        {
          strategy: 'AI Breakout',
          totalTrades: 85,
          winningTrades: 61,
          losingTrades: 24,
          winRate: 71.8,
          avgWinAmount: 45.67,
          avgLossAmount: -28.34,
          profitFactor: 2.95,
          largestWin: 156.78,
          largestLoss: -89.23,
          avgWinDuration: 78,
          avgLossDuration: 45,
          consecutiveWins: 8,
          consecutiveLosses: 3,
          color: '#10B981'
        },
        {
          strategy: 'AI Reversal',
          totalTrades: 62,
          winningTrades: 39,
          losingTrades: 23,
          winRate: 62.9,
          avgWinAmount: 38.92,
          avgLossAmount: -31.45,
          profitFactor: 1.92,
          largestWin: 124.56,
          largestLoss: -76.89,
          avgWinDuration: 92,
          avgLossDuration: 67,
          consecutiveWins: 6,
          consecutiveLosses: 4,
          color: '#3B82F6'
        },
        {
          strategy: 'AI Momentum',
          totalTrades: 73,
          winningTrades: 47,
          losingTrades: 26,
          winRate: 64.4,
          avgWinAmount: 41.23,
          avgLossAmount: -25.67,
          profitFactor: 2.18,
          largestWin: 189.34,
          largestLoss: -62.78,
          avgWinDuration: 65,
          avgLossDuration: 38,
          consecutiveWins: 7,
          consecutiveLosses: 2,
          color: '#8B5CF6'
        },
        {
          strategy: 'AI Trend',
          totalTrades: 58,
          winningTrades: 42,
          losingTrades: 16,
          winRate: 72.4,
          avgWinAmount: 52.34,
          avgLossAmount: -34.56,
          profitFactor: 3.12,
          largestWin: 198.76,
          largestLoss: -89.45,
          avgWinDuration: 124,
          avgLossDuration: 67,
          consecutiveWins: 9,
          consecutiveLosses: 2,
          color: '#F59E0B'
        },
        {
          strategy: 'Manual Trading',
          totalTrades: 34,
          winningTrades: 18,
          losingTrades: 16,
          winRate: 52.9,
          avgWinAmount: 28.67,
          avgLossAmount: -32.89,
          profitFactor: 1.24,
          largestWin: 89.23,
          largestLoss: -78.56,
          avgWinDuration: 89,
          avgLossDuration: 78,
          consecutiveWins: 4,
          consecutiveLosses: 5,
          color: '#6B7280'
        }
      ];

      // Generate time-based win rate data
      const mockTimeBasedData: TimeBasedWinRate[] = [
        { period: '00:00-03:00', winRate: 58.3, trades: 24, avgReturn: 12.45, volatility: 15.6 },
        { period: '03:00-06:00', winRate: 52.1, trades: 18, avgReturn: 8.92, volatility: 12.3 },
        { period: '06:00-09:00', winRate: 64.7, trades: 42, avgReturn: 18.76, volatility: 18.9 },
        { period: '09:00-12:00', winRate: 72.8, trades: 67, avgReturn: 24.35, volatility: 21.4 },
        { period: '12:00-15:00', winRate: 69.4, trades: 58, avgReturn: 21.89, volatility: 19.7 },
        { period: '15:00-18:00', winRate: 66.2, trades: 51, avgReturn: 19.23, volatility: 17.8 },
        { period: '18:00-21:00', winRate: 61.5, trades: 39, avgReturn: 15.67, volatility: 16.2 },
        { period: '21:00-24:00', winRate: 59.8, trades: 31, avgReturn: 13.45, volatility: 14.9 }
      ];

      // Generate market condition win rate data
      const mockMarketConditionData: MarketConditionWinRate[] = [
        {
          condition: 'Strong Bull Market',
          winRate: 78.5,
          trades: 89,
          description: 'Clear upward trend with high volume',
          color: '#10B981'
        },
        {
          condition: 'Weak Bull Market',
          winRate: 65.2,
          trades: 67,
          description: 'Moderate upward movement',
          color: '#34D399'
        },
        {
          condition: 'Sideways/Consolidation',
          winRate: 58.7,
          trades: 124,
          description: 'Range-bound market with low volatility',
          color: '#6B7280'
        },
        {
          condition: 'Weak Bear Market',
          winRate: 62.1,
          trades: 53,
          description: 'Moderate downward movement',
          color: '#F87171'
        },
        {
          condition: 'Strong Bear Market',
          winRate: 69.3,
          trades: 37,
          description: 'Clear downward trend with high volume',
          color: '#EF4444'
        },
        {
          condition: 'High Volatility',
          winRate: 71.8,
          trades: 76,
          description: 'Rapid price movements in either direction',
          color: '#8B5CF6'
        }
      ];

      setTimeout(() => {
        setStrategyData(mockStrategyData);
        setTimeBasedData(mockTimeBasedData);
        setMarketConditionData(mockMarketConditionData);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch win rate data');
      setLoading(false);
    }
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 70) return 'text-green-600 dark:text-green-400';
    if (winRate >= 60) return 'text-blue-600 dark:text-blue-400';
    if (winRate >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getWinRateStatus = (winRate: number) => {
    if (winRate >= 70) return 'Excellent';
    if (winRate >= 60) return 'Good';
    if (winRate >= 50) return 'Average';
    return 'Poor';
  };

  const renderPieChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={strategyData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ strategy, winRate }) => `${strategy}: ${formatPercent(winRate)}`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="winRate"
        >
          {strategyData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip 
          formatter={(value: number) => [formatPercent(value), 'Win Rate']}
          contentStyle={{ 
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            border: '1px solid #374151',
            borderRadius: '8px',
            color: '#F9FAFB'
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );

  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={strategyData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
        <XAxis dataKey="strategy" stroke="#6B7280" fontSize={12} />
        <YAxis stroke="#6B7280" fontSize={12} />
        <Tooltip 
          formatter={(value: number) => [formatPercent(value), 'Win Rate']}
          contentStyle={{ 
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            border: '1px solid #374151',
            borderRadius: '8px',
            color: '#F9FAFB'
          }}
        />
        <Bar dataKey="winRate" fill="#3B82F6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );

  const renderTimeBasedChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={timeBasedData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
        <XAxis dataKey="period" stroke="#6B7280" fontSize={12} />
        <YAxis stroke="#6B7280" fontSize={12} />
        <Tooltip 
          formatter={(value: number, name: string) => [
            name === 'winRate' ? formatPercent(value) : value,
            name === 'winRate' ? 'Win Rate' : name === 'trades' ? 'Trades' : 'Avg Return'
          ]}
          contentStyle={{ 
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            border: '1px solid #374151',
            borderRadius: '8px',
            color: '#F9FAFB'
          }}
        />
        <Line type="monotone" dataKey="winRate" stroke="#3B82F6" strokeWidth={2} />
        <Line type="monotone" dataKey="trades" stroke="#10B981" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );

  const overallWinRate = strategyData.length > 0 
    ? strategyData.reduce((sum, d) => sum + (d.winRate * d.totalTrades), 0) / 
      strategyData.reduce((sum, d) => sum + d.totalTrades, 0)
    : 0;

  const totalTrades = strategyData.reduce((sum, d) => sum + d.totalTrades, 0);
  const totalWinningTrades = strategyData.reduce((sum, d) => sum + d.winningTrades, 0);
  const bestStrategy = strategyData.reduce((best, current) => 
    current.winRate > best.winRate ? current : best, strategyData[0] || { winRate: 0, strategy: 'None' }
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading win rate analysis...</span>
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Win Rate Analysis
        </h2>
        
        <div className="flex items-center space-x-2">
          {/* Group By Selector */}
          <select
            value={groupBy}
            onChange={(e) => onGroupByChange?.(e.currentTarget.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="strategy">By Strategy</option>
            <option value="timeOfDay">By Time of Day</option>
            <option value="marketCondition">By Market Condition</option>
            <option value="volume">By Volume</option>
          </select>
          
          <button
            onClick={fetchWinRateData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Overall Win Rate
              </div>
              <div className={`text-2xl font-bold ${getWinRateColor(overallWinRate)}`}>
                {formatPercent(overallWinRate)}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {getWinRateStatus(overallWinRate)}
              </div>
            </div>
            <Target className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Trades
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {totalTrades}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {totalWinningTrades} wins
              </div>
            </div>
            <Activity className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Best Strategy
              </div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {bestStrategy.strategy}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {formatPercent(bestStrategy.winRate)}
              </div>
            </div>
            <Award className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Consistency
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {(strategyData.filter(s => s.winRate >= 60).length / strategyData.length * 100).toFixed(0)}%
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Strategies {'>'} 60%
              </div>
            </div>
            <BarChart3 className="w-8 h-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Charts */}
      {showCharts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Strategy Win Rate Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Win Rate by Strategy
            </h3>
            {renderBarChart()}
          </div>

          {/* Time-Based Win Rate Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Win Rate by Time of Day
            </h3>
            {renderTimeBasedChart()}
          </div>
        </div>
      )}

      {/* Detailed Strategy Analysis */}
      {showDetails && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Strategy Performance Details
          </h3>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Strategy</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Win Rate</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Trades</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Avg Win</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Avg Loss</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Profit Factor</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600 dark:text-gray-400">Max Streak</th>
                </tr>
              </thead>
              <tbody>
                {strategyData.map((strategy, index) => (
                  <tr 
                    key={index} 
                    className={`border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ${
                      selectedStrategy === strategy.strategy ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                    }`}
                    onClick={() => setSelectedStrategy(strategy.strategy === selectedStrategy ? null : strategy.strategy)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center">
                        <div 
                          className="w-3 h-3 rounded-full mr-3"
                          style={{ backgroundColor: strategy.color }}
                        />
                        <span className="font-medium text-gray-900 dark:text-white">
                          {strategy.strategy}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`font-medium ${getWinRateColor(strategy.winRate)}`}>
                        {formatPercent(strategy.winRate)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-900 dark:text-white">
                      {strategy.totalTrades}
                    </td>
                    <td className="py-3 px-4 text-green-600 dark:text-green-400">
                      {formatCurrency(strategy.avgWinAmount)}
                    </td>
                    <td className="py-3 px-4 text-red-600 dark:text-red-400">
                      {formatCurrency(strategy.avgLossAmount)}
                    </td>
                    <td className="py-3 px-4 text-gray-900 dark:text-white">
                      {strategy.profitFactor.toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-sm">
                        <div className="text-green-600 dark:text-green-400">
                          W: {strategy.consecutiveWins}
                        </div>
                        <div className="text-red-600 dark:text-red-400">
                          L: {strategy.consecutiveLosses}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Market Condition Analysis */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Performance by Market Condition
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {marketConditionData.map((condition, index) => (
            <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <div 
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: condition.color }}
                  />
                  <span className="font-medium text-gray-900 dark:text-white">
                    {condition.condition}
                  </span>
                </div>
                <span className={`font-bold ${getWinRateColor(condition.winRate)}`}>
                  {formatPercent(condition.winRate)}
                </span>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                {condition.description}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {condition.trades} trades
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Insights */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start">
          <Brain className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3" />
          <div>
            <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
              Win Rate Insights
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
              <li>• AI strategies consistently outperform manual trading ({formatPercent(overallWinRate)} vs {formatPercent(strategyData.find(s => s.strategy === 'Manual Trading')?.winRate || 0)})</li>
              <li>• Best performance occurs during market hours (9 AM - 4 PM) with {formatPercent(timeBasedData.find(t => t.period === '09:00-12:00')?.winRate || 0)} win rate</li>
              <li>• {bestStrategy.strategy} shows the highest consistency with {formatPercent(bestStrategy.winRate)} win rate</li>
              <li>• Strong trending markets provide better opportunities than sideways consolidation</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 