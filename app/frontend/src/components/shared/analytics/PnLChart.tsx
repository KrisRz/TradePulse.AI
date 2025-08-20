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
  AreaChart,
  Area,
  ReferenceLine,
  ComposedChart
} from 'recharts';
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Calendar,
  DollarSign,
  Target,
  RefreshCw,
  AlertTriangle,
  Eye,
  Download
} from 'lucide-preact';

interface PnLDataPoint {
  date: string;
  timestamp: number;
  dailyPnL: number;
  cumulativePnL: number;
  realized: number;
  unrealized: number;
  trades: number;
  winningTrades: number;
  losingTrades: number;
  volume: number;
  fees: number;
  drawdown: number;
}

interface PnLSummary {
  totalPnL: number;
  totalRealized: number;
  totalUnrealized: number;
  totalFees: number;
  totalVolume: number;
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  bestDay: number;
  worstDay: number;
  maxDrawdown: number;
  currentDrawdown: number;
  consecutiveWinningDays: number;
  consecutiveLosingDays: number;
  avgDailyPnL: number;
  volatility: number;
  sharpeRatio: number;
}

interface PnLChartProps {
  timeRange?: '7d' | '30d' | '90d' | '1y' | 'all';
  chartType?: 'line' | 'bar' | 'area' | 'composed';
  showVolume?: boolean;
  showDrawdown?: boolean;
  showSummary?: boolean;
  onTimeRangeChange?: (range: string) => void;
  onExport?: (data: PnLDataPoint[]) => void;
}

export default function PnLChart({
  timeRange = '30d',
  chartType = 'line',
  showVolume = true,
  showDrawdown = true,
  showSummary = true,
  onTimeRangeChange,
  onExport
}: PnLChartProps) {
  const [data, setData] = useState<PnLDataPoint[]>([]);
  const [summary, setSummary] = useState<PnLSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDataPoint, setSelectedDataPoint] = useState<PnLDataPoint | null>(null);
  const [viewMode, setViewMode] = useState<'cumulative' | 'daily' | 'drawdown'>('cumulative');

  useEffect(() => {
    fetchPnLData();
  }, [timeRange]);

  const fetchPnLData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Generate mock P&L data
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
      const mockData: PnLDataPoint[] = [];
      
      let cumulativePnL = 0;
      let peak = 0;
      let drawdown = 0;
      
      for (let i = 0; i < days; i++) {
        const date = new Date();
        date.setDate(date.getDate() - (days - i));
        
        // Generate realistic P&L data with some trends
        const baseReturn = (Math.random() - 0.45) * 100; // Slight positive bias
        const volatility = 20 + Math.random() * 30; // Variable volatility
        const dailyPnL = baseReturn + (Math.random() - 0.5) * volatility;
        
        cumulativePnL += dailyPnL;
        
        // Calculate drawdown
        peak = Math.max(peak, cumulativePnL);
        drawdown = Math.min(0, cumulativePnL - peak);
        
        // Generate trade data
        const trades = Math.floor(Math.random() * 12) + 1; // 1-12 trades per day
        const winningTrades = Math.floor(trades * (0.5 + Math.random() * 0.3)); // 50-80% win rate
        const losingTrades = trades - winningTrades;
        
        const volume = Math.random() * 50000 + 10000; // $10k-$60k daily volume
        const fees = volume * 0.001; // 0.1% fees
        
        const realized = dailyPnL * (0.7 + Math.random() * 0.3); // 70-100% realized
        const unrealized = dailyPnL - realized;
        
        mockData.push({
          date: date.toISOString().split('T')[0],
          timestamp: date.getTime(),
          dailyPnL,
          cumulativePnL,
          realized,
          unrealized,
          trades,
          winningTrades,
          losingTrades,
          volume,
          fees,
          drawdown
        });
      }
      
      // Calculate summary statistics
      const totalPnL = cumulativePnL;
      const totalRealized = mockData.reduce((sum, d) => sum + d.realized, 0);
      const totalUnrealized = mockData.reduce((sum, d) => sum + d.unrealized, 0);
      const totalFees = mockData.reduce((sum, d) => sum + d.fees, 0);
      const totalVolume = mockData.reduce((sum, d) => sum + d.volume, 0);
      const totalTrades = mockData.reduce((sum, d) => sum + d.trades, 0);
      const totalWinningTrades = mockData.reduce((sum, d) => sum + d.winningTrades, 0);
      
      const winRate = (totalWinningTrades / totalTrades) * 100;
      const bestDay = Math.max(...mockData.map(d => d.dailyPnL));
      const worstDay = Math.min(...mockData.map(d => d.dailyPnL));
      const maxDrawdown = Math.min(...mockData.map(d => d.drawdown));
      
      const avgDailyPnL = totalPnL / days;
      const dailyReturns = mockData.map(d => d.dailyPnL);
      const volatility = Math.sqrt(
        dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgDailyPnL, 2), 0) / days
      );
      const sharpeRatio = volatility > 0 ? avgDailyPnL / volatility : 0;
      
      // Calculate profit factor
      const grossProfit = mockData.filter(d => d.dailyPnL > 0).reduce((sum, d) => sum + d.dailyPnL, 0);
      const grossLoss = Math.abs(mockData.filter(d => d.dailyPnL < 0).reduce((sum, d) => sum + d.dailyPnL, 0));
      const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 999 : 0;
      
      // Calculate consecutive winning/losing days
      let consecutiveWinningDays = 0;
      let consecutiveLosingDays = 0;
      let currentWinStreak = 0;
      let currentLossStreak = 0;
      
      for (const point of mockData) {
        if (point.dailyPnL > 0) {
          currentWinStreak++;
          currentLossStreak = 0;
          consecutiveWinningDays = Math.max(consecutiveWinningDays, currentWinStreak);
        } else if (point.dailyPnL < 0) {
          currentLossStreak++;
          currentWinStreak = 0;
          consecutiveLosingDays = Math.max(consecutiveLosingDays, currentLossStreak);
        }
      }
      
      const mockSummary: PnLSummary = {
        totalPnL,
        totalRealized,
        totalUnrealized,
        totalFees,
        totalVolume,
        totalTrades,
        winRate,
        profitFactor,
        bestDay,
        worstDay,
        maxDrawdown,
        currentDrawdown: drawdown,
        consecutiveWinningDays,
        consecutiveLosingDays,
        avgDailyPnL,
        volatility,
        sharpeRatio
      };
      
      setTimeout(() => {
        setData(mockData);
        setSummary(mockSummary);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch P&L data');
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

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getColorByValue = (value: number) => {
    return value >= 0 ? '#10B981' : '#EF4444';
  };

  const getChartData = () => {
    switch (viewMode) {
      case 'daily':
        return data.map(d => ({
          ...d,
          value: d.dailyPnL,
          label: 'Daily P&L'
        }));
      case 'drawdown':
        return data.map(d => ({
          ...d,
          value: d.drawdown,
          label: 'Drawdown'
        }));
      default:
        return data.map(d => ({
          ...d,
          value: d.cumulativePnL,
          label: 'Cumulative P&L'
        }));
    }
  };

  const renderChart = () => {
    const chartData = getChartData();
    
    switch (chartType) {
      case 'bar':
        return (
          <BarChart data={chartData}>
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
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              formatter={(value: number) => [formatCurrency(value), 'P&L']}
              labelFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <Bar 
              dataKey="value" 
              fill={(entry) => getColorByValue(entry.value)}
              radius={[2, 2, 0, 0]}
            />
          </BarChart>
        );
      
      case 'area':
        return (
          <AreaChart data={chartData}>
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
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              formatter={(value: number) => [formatCurrency(value), 'P&L']}
              labelFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#3B82F6" 
              fill="#3B82F6"
              fillOpacity={0.1}
            />
            <ReferenceLine y={0} stroke="#374151" strokeDasharray="2 2" />
          </AreaChart>
        );
      
      case 'composed':
        return (
          <ComposedChart data={chartData}>
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
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              formatter={(value: number, name: string) => [
                formatCurrency(value), 
                name === 'value' ? 'P&L' : name === 'volume' ? 'Volume' : name
              ]}
              labelFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#3B82F6" 
              fill="#3B82F6"
              fillOpacity={0.1}
            />
            {showVolume && (
              <Bar 
                dataKey="volume" 
                fill="#6B7280"
                opacity={0.3}
                yAxisId="volume"
              />
            )}
            <ReferenceLine y={0} stroke="#374151" strokeDasharray="2 2" />
          </ComposedChart>
        );
      
      default:
        return (
          <LineChart data={chartData}>
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
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              formatter={(value: number) => [formatCurrency(value), 'P&L']}
              labelFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={false}
            />
            <ReferenceLine y={0} stroke="#374151" strokeDasharray="2 2" />
          </LineChart>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading P&L data...</span>
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
          Profit & Loss Analysis
        </h2>
        
        <div className="flex items-center space-x-2 flex-wrap">
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
            onClick={() => onExport?.(data)}
            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          
          <button
            onClick={fetchPnLData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && showSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Total P&L
                </div>
                <div className={`text-2xl font-bold ${
                  summary.totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(summary.totalPnL)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Avg: {formatCurrency(summary.avgDailyPnL)}/day
                </div>
              </div>
              <DollarSign className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Win Rate
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.winRate.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {summary.totalTrades} trades
                </div>
              </div>
              <Target className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Best Day
                </div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {formatCurrency(summary.bestDay)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Worst: {formatCurrency(summary.worstDay)}
                </div>
              </div>
              <TrendingUp className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Max Drawdown
                </div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {formatCurrency(summary.maxDrawdown)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Current: {formatCurrency(summary.currentDrawdown)}
                </div>
              </div>
              <TrendingDown className="w-8 h-8 text-gray-400" />
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      {data.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              P&L Chart
            </h3>
            
            <div className="flex space-x-2">
              {/* View Mode Buttons */}
              <button
                onClick={() => setViewMode('cumulative')}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  viewMode === 'cumulative'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Cumulative
              </button>
              <button
                onClick={() => setViewMode('daily')}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  viewMode === 'daily'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Daily
              </button>
              {showDrawdown && (
                <button
                  onClick={() => setViewMode('drawdown')}
                  className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                    viewMode === 'drawdown'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  Drawdown
                </button>
              )}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            {renderChart()}
          </ResponsiveContainer>
        </div>
      )}

      {/* Detailed Statistics */}
      {summary && showSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Trading Statistics
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Trades</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {summary.totalTrades}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {summary.winRate.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {summary.profitFactor.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {summary.sharpeRatio.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Volatility</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {formatCurrency(summary.volatility)}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              P&L Breakdown
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Realized P&L</span>
                <span className={`font-medium ${
                  summary.totalRealized >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(summary.totalRealized)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Unrealized P&L</span>
                <span className={`font-medium ${
                  summary.totalUnrealized >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(summary.totalUnrealized)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Fees</span>
                <span className="font-medium text-red-600 dark:text-red-400">
                  -{formatCurrency(summary.totalFees)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Volume</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {formatCurrency(summary.totalVolume)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Net P&L</span>
                <span className={`font-medium ${
                  summary.totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(summary.totalPnL)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 