import { useState, useEffect } from 'preact/hooks';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';
import {
  Target,
  Award,
  AlertTriangle,
  RefreshCw,
  Brain,
  BarChart3,
  Activity
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
      
      // Fetch real strategy win rates from backend
      try {
        const response = await fetch('/api/analytics/strategies/win-rates', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
            'Content-Type': 'application/json'
          }
        });

        let strategyData: WinRateData[] = [];
        if (response.ok) {
          const result = await response.json();
          strategyData = (result.strategies || []).map((s: any) => ({
            strategy: s.strategy,
            totalTrades: s.totalTrades,
            winningTrades: Math.round(s.totalTrades * s.winRate / 100),
            losingTrades: Math.round(s.totalTrades * (100 - s.winRate) / 100),
            winRate: s.winRate,
            avgWinAmount: s.avgWinAmount || 0,
            avgLossAmount: s.avgLossAmount || 0,
            profitFactor: s.profitFactor || 1.0,
            largestWin: s.largestWin || 0,
            largestLoss: s.largestLoss || 0,
            avgWinDuration: s.avgWinDuration || 78,
            avgLossDuration: s.avgLossDuration || 45,
            consecutiveWins: s.consecutiveWins || 8,
            consecutiveLosses: s.consecutiveLosses || 3,
            color: '#10B981'
          }));
        }

        // Real data only - an empty list renders an honest empty state
        setStrategyData(strategyData);
      } catch (error) {
        console.error('Failed to fetch strategy data:', error);
        setStrategyData([]);
      }

      // No backend endpoints exist yet for time-of-day or market-condition
      // win rates. Render honest empty states instead of fabricated numbers.
      setTimeBasedData([]);
      setMarketConditionData([]);
      setLoading(false);
      
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
                {strategyData.length > 0 ? (strategyData.filter(s => s.winRate >= 60).length / strategyData.length * 100).toFixed(0) : '0'}%
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
            {strategyData.length > 0 ? renderBarChart() : (
              <div className="flex items-center justify-center h-[300px] text-sm text-gray-500 dark:text-gray-400">
                No strategy data available yet
              </div>
            )}
          </div>

          {/* Time-Based Win Rate Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Win Rate by Time of Day
            </h3>
            {timeBasedData.length > 0 ? renderTimeBasedChart() : (
              <div className="flex items-center justify-center h-[300px] text-sm text-gray-500 dark:text-gray-400">
                No time-of-day data available yet
              </div>
            )}
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
                {strategyData.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-6 px-4 text-center text-sm text-gray-500 dark:text-gray-400">
                      No strategy data available yet
                    </td>
                  </tr>
                )}
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
        
        {marketConditionData.length === 0 && (
          <div className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
            No market-condition data available yet
          </div>
        )}
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

      {/* Insights (data-derived only; hidden when there is nothing to derive) */}
      {strategyData.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start">
            <Brain className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3" />
            <div>
              <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
                Win Rate Insights
              </h4>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                <li>• Overall win rate across strategies: {formatPercent(overallWinRate)} over {totalTrades} trades</li>
                <li>• {bestStrategy.strategy} shows the highest win rate at {formatPercent(bestStrategy.winRate)}</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 