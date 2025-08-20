import { useState, useEffect } from 'preact/hooks';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine
} from 'recharts';
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Target, 
  Brain,
  Shuffle,
  Award,
  AlertTriangle,
  RefreshCw
} from 'lucide-preact';

interface PerformanceData {
  date: string;
  aiCumulative: number;
  randomCumulative: number;
  aiDaily: number;
  randomDaily: number;
  aiTrades: number;
  randomTrades: number;
  aiWins: number;
  randomWins: number;
  aiDrawdown: number;
  randomDrawdown: number;
}

interface ComparisonMetrics {
  aiTotalReturn: number;
  randomTotalReturn: number;
  aiWinRate: number;
  randomWinRate: number;
  aiSharpeRatio: number;
  randomSharpeRatio: number;
  aiMaxDrawdown: number;
  randomMaxDrawdown: number;
  aiTotalTrades: number;
  randomTotalTrades: number;
  aiProfitFactor: number;
  randomProfitFactor: number;
  statisticalSignificance: number;
  confidenceInterval: number;
  outperformanceDays: number;
  totalDays: number;
}

interface PerformanceComparisonProps {
  timeRange?: '7d' | '30d' | '90d' | '1y' | 'all';
  showStatistics?: boolean;
  showChart?: boolean;
  onTimeRangeChange?: (range: string) => void;
}

export default function PerformanceComparison({
  timeRange = '30d',
  showStatistics = true,
  showChart = true,
  onTimeRangeChange
}: PerformanceComparisonProps) {
  const [data, setData] = useState<PerformanceData[]>([]);
  const [metrics, setMetrics] = useState<ComparisonMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'cumulative' | 'daily' | 'drawdown'>('cumulative');

  useEffect(() => {
    fetchPerformanceData();
  }, [timeRange]);

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Generate mock performance data
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
      const mockData: PerformanceData[] = [];
      
      let aiCumulative = 0;
      let randomCumulative = 0;
      let aiDrawdown = 0;
      let randomDrawdown = 0;
      let aiPeak = 0;
      let randomPeak = 0;
      
      for (let i = 0; i < days; i++) {
        const date = new Date();
        date.setDate(date.getDate() - (days - i));
        
        // AI performance with trend and volatility
        const aiDailyReturn = (Math.random() - 0.45) * 0.02 + 0.0008; // Slight positive bias
        const randomDailyReturn = (Math.random() - 0.5) * 0.025; // Pure random
        
        aiCumulative += aiDailyReturn;
        randomCumulative += randomDailyReturn;
        
        // Update drawdown calculations
        aiPeak = Math.max(aiPeak, aiCumulative);
        randomPeak = Math.max(randomPeak, randomCumulative);
        aiDrawdown = Math.min(aiDrawdown, aiCumulative - aiPeak);
        randomDrawdown = Math.min(randomDrawdown, randomCumulative - randomPeak);
        
        // Generate trade counts
        const aiTrades = Math.floor(Math.random() * 8) + 2; // 2-10 trades per day
        const randomTrades = Math.floor(Math.random() * 6) + 1; // 1-7 trades per day
        
        // Win rates (AI slightly better)
        const aiWins = Math.floor(aiTrades * (0.58 + Math.random() * 0.2)); // 58-78% win rate
        const randomWins = Math.floor(randomTrades * (0.45 + Math.random() * 0.2)); // 45-65% win rate
        
        mockData.push({
          date: date.toISOString().split('T')[0],
          aiCumulative: aiCumulative * 100, // Convert to percentage
          randomCumulative: randomCumulative * 100,
          aiDaily: aiDailyReturn * 100,
          randomDaily: randomDailyReturn * 100,
          aiTrades,
          randomTrades,
          aiWins,
          randomWins,
          aiDrawdown: aiDrawdown * 100,
          randomDrawdown: randomDrawdown * 100
        });
      }
      
      // Calculate comparison metrics
      const totalAiTrades = mockData.reduce((sum, d) => sum + d.aiTrades, 0);
      const totalRandomTrades = mockData.reduce((sum, d) => sum + d.randomTrades, 0);
      const totalAiWins = mockData.reduce((sum, d) => sum + d.aiWins, 0);
      const totalRandomWins = mockData.reduce((sum, d) => sum + d.randomWins, 0);
      
      const aiWinRate = (totalAiWins / totalAiTrades) * 100;
      const randomWinRate = (totalRandomWins / totalRandomTrades) * 100;
      
      // Calculate Sharpe ratios (simplified)
      const aiReturns = mockData.map(d => d.aiDaily);
      const randomReturns = mockData.map(d => d.randomDaily);
      
      const aiAvgReturn = aiReturns.reduce((a, b) => a + b, 0) / aiReturns.length;
      const randomAvgReturn = randomReturns.reduce((a, b) => a + b, 0) / randomReturns.length;
      
      const aiStdDev = Math.sqrt(aiReturns.reduce((sum, r) => sum + Math.pow(r - aiAvgReturn, 2), 0) / aiReturns.length);
      const randomStdDev = Math.sqrt(randomReturns.reduce((sum, r) => sum + Math.pow(r - randomAvgReturn, 2), 0) / randomReturns.length);
      
      const aiSharpeRatio = aiAvgReturn / aiStdDev;
      const randomSharpeRatio = randomAvgReturn / randomStdDev;
      
      // Count outperformance days
      const outperformanceDays = mockData.filter(d => d.aiDaily > d.randomDaily).length;
      
      // Statistical significance (simplified t-test)
      const statisticalSignificance = Math.min(99.9, Math.max(0, 
        (Math.abs(aiWinRate - randomWinRate) / Math.sqrt(aiWinRate * (100 - aiWinRate) / totalAiTrades)) * 10
      ));
      
      const mockMetrics: ComparisonMetrics = {
        aiTotalReturn: aiCumulative * 100,
        randomTotalReturn: randomCumulative * 100,
        aiWinRate,
        randomWinRate,
        aiSharpeRatio,
        randomSharpeRatio,
        aiMaxDrawdown: Math.min(...mockData.map(d => d.aiDrawdown)),
        randomMaxDrawdown: Math.min(...mockData.map(d => d.randomDrawdown)),
        aiTotalTrades: totalAiTrades,
        randomTotalTrades: totalRandomTrades,
        aiProfitFactor: 1.8 + Math.random() * 0.8, // 1.8-2.6
        randomProfitFactor: 0.8 + Math.random() * 0.8, // 0.8-1.6
        statisticalSignificance,
        confidenceInterval: 95,
        outperformanceDays,
        totalDays: days
      };
      
      setTimeout(() => {
        setData(mockData);
        setMetrics(mockMetrics);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch performance data');
      setLoading(false);
    }
  };

  const formatPercent = (value: number, decimals: number = 2) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  };

  const getPerformanceColor = (value: number) => {
    return value >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  const getChartData = () => {
    switch (chartType) {
      case 'daily':
        return data.map(d => ({
          ...d,
          aiValue: d.aiDaily,
          randomValue: d.randomDaily,
          aiLabel: 'AI Daily Return',
          randomLabel: 'Random Daily Return'
        }));
      case 'drawdown':
        return data.map(d => ({
          ...d,
          aiValue: d.aiDrawdown,
          randomValue: d.randomDrawdown,
          aiLabel: 'AI Drawdown',
          randomLabel: 'Random Drawdown'
        }));
      default:
        return data.map(d => ({
          ...d,
          aiValue: d.aiCumulative,
          randomValue: d.randomCumulative,
          aiLabel: 'AI Cumulative Return',
          randomLabel: 'Random Cumulative Return'
        }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading performance data...</span>
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
          AI vs Random Performance
        </h2>
        
        <div className="flex items-center space-x-2">
          {/* Time Range Selector */}
          <select
            value={timeRange}
            onChange={(e) => onTimeRangeChange?.(e.currentTarget.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
            <option value="all">All time</option>
          </select>
          
          <button
            onClick={fetchPerformanceData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Key Metrics Overview */}
      {metrics && showStatistics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Total Return
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <span className={`font-bold ${getPerformanceColor(metrics.aiTotalReturn)}`}>
                    {formatPercent(metrics.aiTotalReturn)}
                  </span>
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Shuffle className="w-4 h-4 text-gray-500" />
                  <span className={`font-bold ${getPerformanceColor(metrics.randomTotalReturn)}`}>
                    {formatPercent(metrics.randomTotalReturn)}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600 dark:text-gray-400">Difference</div>
                <div className={`text-lg font-bold ${getPerformanceColor(metrics.aiTotalReturn - metrics.randomTotalReturn)}`}>
                  {formatPercent(metrics.aiTotalReturn - metrics.randomTotalReturn)}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Win Rate
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <span className="font-bold text-gray-900 dark:text-white">
                    {metrics.aiWinRate.toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Shuffle className="w-4 h-4 text-gray-500" />
                  <span className="font-bold text-gray-900 dark:text-white">
                    {metrics.randomWinRate.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600 dark:text-gray-400">Advantage</div>
                <div className="text-lg font-bold text-green-600 dark:text-green-400">
                  +{(metrics.aiWinRate - metrics.randomWinRate).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Sharpe Ratio
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <span className="font-bold text-gray-900 dark:text-white">
                    {metrics.aiSharpeRatio.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Shuffle className="w-4 h-4 text-gray-500" />
                  <span className="font-bold text-gray-900 dark:text-white">
                    {metrics.randomSharpeRatio.toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600 dark:text-gray-400">Risk-Adj</div>
                <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                  {metrics.aiSharpeRatio > metrics.randomSharpeRatio ? 'Better' : 'Worse'}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Max Drawdown
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <span className="font-bold text-red-600 dark:text-red-400">
                    {formatPercent(metrics.aiMaxDrawdown)}
                  </span>
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <Shuffle className="w-4 h-4 text-gray-500" />
                  <span className="font-bold text-red-600 dark:text-red-400">
                    {formatPercent(metrics.randomMaxDrawdown)}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600 dark:text-gray-400">Lower Risk</div>
                <div className="text-lg font-bold text-green-600 dark:text-green-400">
                  {Math.abs(metrics.aiMaxDrawdown) < Math.abs(metrics.randomMaxDrawdown) ? 'AI' : 'Random'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Statistical Significance */}
      {metrics && showStatistics && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Award className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" />
              <div>
                <div className="font-medium text-blue-900 dark:text-blue-200">
                  Statistical Significance: {metrics.statisticalSignificance.toFixed(1)}%
                </div>
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  AI outperformed random trading on {metrics.outperformanceDays} out of {metrics.totalDays} days 
                  ({((metrics.outperformanceDays / metrics.totalDays) * 100).toFixed(1)}% of the time)
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-blue-600 dark:text-blue-400">Confidence Level</div>
              <div className="text-lg font-bold text-blue-900 dark:text-blue-200">
                {metrics.confidenceInterval}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      {showChart && data.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Performance Chart
            </h3>
            
            <div className="flex space-x-2">
              <button
                onClick={() => setChartType('cumulative')}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  chartType === 'cumulative'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Cumulative
              </button>
              <button
                onClick={() => setChartType('daily')}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  chartType === 'daily'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Daily
              </button>
              <button
                onClick={() => setChartType('drawdown')}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  chartType === 'drawdown'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Drawdown
              </button>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={getChartData()}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="date" 
                stroke="#6B7280"
                fontSize={12}
                tickFormatter={(date) => new Date(date).toLocaleDateString()}
              />
              <YAxis 
                stroke="#6B7280"
                fontSize={12}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(17, 24, 39, 0.95)',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB'
                }}
                formatter={(value: number, name: string) => [
                  `${value.toFixed(2)}%`,
                  name === 'aiValue' ? 'AI Performance' : 'Random Performance'
                ]}
                labelFormatter={(date) => new Date(date).toLocaleDateString()}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="aiValue" 
                stroke="#3B82F6" 
                strokeWidth={2}
                name="AI Performance"
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="randomValue" 
                stroke="#6B7280" 
                strokeWidth={2}
                name="Random Performance"
                dot={false}
              />
              {chartType !== 'drawdown' && <ReferenceLine y={0} stroke="#374151" strokeDasharray="2 2" />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detailed Statistics */}
      {metrics && showStatistics && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Detailed Statistics
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white flex items-center">
                <Brain className="w-4 h-4 text-blue-500 mr-2" />
                AI Performance
              </h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Return</span>
                  <span className={`font-medium ${getPerformanceColor(metrics.aiTotalReturn)}`}>
                    {formatPercent(metrics.aiTotalReturn)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.aiWinRate.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.aiProfitFactor.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Trades</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.aiTotalTrades}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.aiSharpeRatio.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</span>
                  <span className="font-medium text-red-600 dark:text-red-400">
                    {formatPercent(metrics.aiMaxDrawdown)}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium text-gray-900 dark:text-white flex items-center">
                <Shuffle className="w-4 h-4 text-gray-500 mr-2" />
                Random Performance
              </h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Return</span>
                  <span className={`font-medium ${getPerformanceColor(metrics.randomTotalReturn)}`}>
                    {formatPercent(metrics.randomTotalReturn)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.randomWinRate.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.randomProfitFactor.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Trades</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.randomTotalTrades}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {metrics.randomSharpeRatio.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</span>
                  <span className="font-medium text-red-600 dark:text-red-400">
                    {formatPercent(metrics.randomMaxDrawdown)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 