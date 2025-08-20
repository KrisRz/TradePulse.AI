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
  Area,
  AreaChart,
  ReferenceLine,
  ReferenceArea
} from 'recharts';
import { TrendingDown, AlertTriangle, Shield, Clock, Target, Info } from 'lucide-preact';

interface DrawdownData {
  date: string;
  portfolio_value: number;
  peak_value: number;
  drawdown_amount: number;
  drawdown_percentage: number;
  underwater_days: number;
  recovery_factor: number;
}

interface DrawdownPeriod {
  start_date: string;
  end_date: string;
  recovery_date?: string;
  max_drawdown: number;
  duration_days: number;
  recovery_days?: number;
  cause?: string;
}

interface DrawdownChartProps {
  className?: string;
  period?: '30d' | '90d' | '1y' | 'all';
  showUnderwater?: boolean;
}

export function DrawdownChart({ 
  className = '',
  period = '90d',
  showUnderwater = true
}: DrawdownChartProps) {
  const [data, setData] = useState<DrawdownData[]>([]);
  const [loading, setLoading] = useState(true);
  const [drawdownPeriods, setDrawdownPeriods] = useState<DrawdownPeriod[]>([]);
  const [activeView, setActiveView] = useState<'drawdown' | 'underwater' | 'recovery'>('drawdown');

  // Mock drawdown data
  const generateMockData = (days: number): DrawdownData[] => {
    const data: DrawdownData[] = [];
    let portfolioValue = 10000;
    let peakValue = 10000;
    let underwaterDays = 0;
    
    for (let i = days; i >= 0; i--) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
      
      // Simulate market movements with occasional drawdowns
      let dailyReturn = (Math.random() - 0.45) * 0.03; // Slight positive bias with volatility
      
      // Simulate major drawdown events
      if (Math.random() < 0.02) { // 2% chance of major drawdown
        dailyReturn = -Math.random() * 0.08; // Major loss day
      }
      
      portfolioValue *= (1 + dailyReturn);
      
      // Update peak value
      if (portfolioValue > peakValue) {
        peakValue = portfolioValue;
        underwaterDays = 0;
      } else {
        underwaterDays++;
      }
      
      const drawdownAmount = peakValue - portfolioValue;
      const drawdownPercentage = (drawdownAmount / peakValue) * 100;
      
      // Recovery factor (how close to recovery)
      const recoveryFactor = portfolioValue / peakValue;
      
      data.push({
        date: date.toISOString().split('T')[0],
        portfolio_value: portfolioValue,
        peak_value: peakValue,
        drawdown_amount: drawdownAmount,
        drawdown_percentage: drawdownPercentage,
        underwater_days: underwaterDays,
        recovery_factor: recoveryFactor
      });
    }
    
    return data;
  };

  const identifyDrawdownPeriods = (data: DrawdownData[]): DrawdownPeriod[] => {
    const periods: DrawdownPeriod[] = [];
    let currentPeriod: Partial<DrawdownPeriod> | null = null;
    
    data.forEach((point, index) => {
      if (point.drawdown_percentage > 1 && !currentPeriod) {
        // Start of drawdown period
        currentPeriod = {
          start_date: point.date,
          max_drawdown: point.drawdown_percentage,
          duration_days: 1
        };
      } else if (currentPeriod && point.drawdown_percentage > 1) {
        // Continue drawdown period
        currentPeriod.max_drawdown = Math.max(currentPeriod.max_drawdown!, point.drawdown_percentage);
        currentPeriod.duration_days!++;
        currentPeriod.end_date = point.date;
      } else if (currentPeriod && point.drawdown_percentage <= 1) {
        // End of drawdown period
        currentPeriod.recovery_date = point.date;
        currentPeriod.recovery_days = 
          (new Date(point.date).getTime() - new Date(currentPeriod.end_date!).getTime()) / (1000 * 60 * 60 * 24);
        
        // Add cause based on max drawdown
        if (currentPeriod.max_drawdown! > 15) {
          currentPeriod.cause = 'Major Market Correction';
        } else if (currentPeriod.max_drawdown! > 8) {
          currentPeriod.cause = 'Market Volatility';
        } else {
          currentPeriod.cause = 'Normal Fluctuation';
        }
        
        periods.push(currentPeriod as DrawdownPeriod);
        currentPeriod = null;
      }
    });
    
    return periods;
  };

  const fetchDrawdownData = async () => {
    try {
      setLoading(true);
      // TODO: Replace with real API call
      // const response = await fetch(`/api/analytics/drawdown?period=${period}`);
      
      const days = period === '30d' ? 30 : period === '90d' ? 90 : period === '1y' ? 365 : 1000;
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockData = generateMockData(days);
      setData(mockData);
      setDrawdownPeriods(identifyDrawdownPeriods(mockData));
    } catch (err) {
      console.error('Failed to fetch drawdown data:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateDrawdownStats = () => {
    if (data.length === 0) return null;
    
    const maxDrawdown = Math.max(...data.map(d => d.drawdown_percentage));
    const avgDrawdown = data.filter(d => d.drawdown_percentage > 0)
      .reduce((sum, d) => sum + d.drawdown_percentage, 0) / 
      data.filter(d => d.drawdown_percentage > 0).length || 0;
    
    const longestUnderwaterPeriod = Math.max(...data.map(d => d.underwater_days));
    const currentDrawdown = data[data.length - 1]?.drawdown_percentage || 0;
    
    const drawdownDays = data.filter(d => d.drawdown_percentage > 1).length;
    const totalDays = data.length;
    const timeInDrawdown = (drawdownDays / totalDays) * 100;
    
    return {
      max_drawdown: maxDrawdown,
      avg_drawdown: avgDrawdown,
      current_drawdown: currentDrawdown,
      longest_underwater: longestUnderwaterPeriod,
      time_in_drawdown: timeInDrawdown,
      total_periods: drawdownPeriods.length,
      avg_recovery_time: drawdownPeriods
        .filter(p => p.recovery_days)
        .reduce((sum, p) => sum + (p.recovery_days || 0), 0) / 
        drawdownPeriods.filter(p => p.recovery_days).length || 0
    };
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 
                        rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            {formatDate(label)}
          </p>
          <div className="space-y-1 text-sm">
            <p className="text-blue-600">
              Portfolio: {formatCurrency(data.portfolio_value)}
            </p>
            <p className="text-green-600">
              Peak: {formatCurrency(data.peak_value)}
            </p>
            <p className="text-red-600">
              Drawdown: -{formatPercentage(data.drawdown_percentage)}
            </p>
            {data.underwater_days > 0 && (
              <p className="text-orange-600">
                Underwater: {data.underwater_days} days
              </p>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  const getRiskLevel = (drawdown: number) => {
    if (drawdown < 5) return { level: 'Low', color: 'text-green-600', bg: 'bg-green-100 dark:bg-green-900/30' };
    if (drawdown < 10) return { level: 'Medium', color: 'text-yellow-600', bg: 'bg-yellow-100 dark:bg-yellow-900/30' };
    if (drawdown < 20) return { level: 'High', color: 'text-orange-600', bg: 'bg-orange-100 dark:bg-orange-900/30' };
    return { level: 'Critical', color: 'text-red-600', bg: 'bg-red-100 dark:bg-red-900/30' };
  };

  const stats = calculateDrawdownStats();

  useEffect(() => {
    fetchDrawdownData();
  }, [period]);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <TrendingDown className="h-8 w-8 text-red-600 dark:text-red-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Drawdown Analysis
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Portfolio risk and recovery patterns
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <select
              value={period}
              onChange={(e) => {
                // Update period and refetch data
                fetchDrawdownData();
              }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-red-500"
            >
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="1y">Last Year</option>
              <option value="all">All Time</option>
            </select>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Max Drawdown</span>
              </div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                -{formatPercentage(stats.max_drawdown)}
              </div>
              <div className={`text-xs px-2 py-1 rounded-full mt-1 inline-block ${getRiskLevel(stats.max_drawdown).bg} ${getRiskLevel(stats.max_drawdown).color}`}>
                {getRiskLevel(stats.max_drawdown).level} Risk
              </div>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-2">
                <Target className="h-5 w-5 text-orange-600" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Drawdown</span>
              </div>
              <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                -{formatPercentage(stats.avg_drawdown)}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {stats.total_periods} periods
              </div>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-2">
                <Clock className="h-5 w-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Recovery Time</span>
              </div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {Math.round(stats.avg_recovery_time)}d
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Average recovery
              </div>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center space-x-2 mb-2">
                <Shield className="h-5 w-5 text-purple-600" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Time Underwater</span>
              </div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {formatPercentage(stats.time_in_drawdown)}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Of total time
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart Tabs */}
      <div className="px-6 pt-6">
        <div className="flex space-x-1 border-b border-gray-200 dark:border-gray-700">
          {[
            { id: 'drawdown', label: 'Drawdown %', icon: TrendingDown },
            { id: 'underwater', label: 'Underwater Period', icon: Clock },
            { id: 'recovery', label: 'Recovery Factor', icon: Target }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveView(id as any)}
              className={`flex items-center space-x-2 px-4 py-2 border-b-2 transition-colors ${
                activeView === id
                  ? 'border-red-500 text-red-600 dark:text-red-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Icon size={16} />
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="p-6">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {activeView === 'drawdown' && (
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <YAxis 
                  tickFormatter={(value) => `-${formatPercentage(value)}`}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="drawdown_percentage"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.3}
                  name="Drawdown %"
                />
                {/* Reference lines for risk levels */}
                <ReferenceLine y={5} stroke="#f59e0b" strokeDasharray="5 5" label="Medium Risk" />
                <ReferenceLine y={10} stroke="#ef4444" strokeDasharray="5 5" label="High Risk" />
                <ReferenceLine y={20} stroke="#dc2626" strokeDasharray="5 5" label="Critical Risk" />
              </AreaChart>
            )}
            
            {activeView === 'underwater' && (
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <YAxis 
                  tickFormatter={(value) => `${value}d`}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="underwater_days"
                  stroke="#f59e0b"
                  fill="#f59e0b"
                  fillOpacity={0.3}
                  name="Days Underwater"
                />
              </AreaChart>
            )}
            
            {activeView === 'recovery' && (
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <YAxis 
                  domain={[0.7, 1.05]}
                  tickFormatter={(value) => formatPercentage(value * 100)}
                  stroke="#6b7280"
                  fontSize={12}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="recovery_factor"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 2 }}
                  name="Recovery Factor"
                />
                <ReferenceLine y={1} stroke="#10b981" strokeDasharray="5 5" label="Full Recovery" />
                <ReferenceLine y={0.9} stroke="#f59e0b" strokeDasharray="3 3" label="90% Recovery" />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* Drawdown Periods Table */}
      {drawdownPeriods.length > 0 && (
        <div className="p-6 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Major Drawdown Periods
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Period
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Max Drawdown
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Duration
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Recovery
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Cause
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {drawdownPeriods.slice(0, 5).map((period, index) => (
                  <tr key={index}>
                    <td className="px-4 py-2 text-sm text-gray-900 dark:text-white">
                      {formatDate(period.start_date)} - {formatDate(period.end_date)}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`text-sm font-medium ${getRiskLevel(period.max_drawdown).color}`}>
                        -{formatPercentage(period.max_drawdown)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                      {period.duration_days} days
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                      {period.recovery_days ? `${period.recovery_days} days` : 'Ongoing'}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                      {period.cause}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Risk Assessment */}
      <div className="p-6 border-t border-gray-200 dark:border-gray-700">
        <div className={`border rounded-lg p-4 ${
          stats && stats.current_drawdown > 10 
            ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700'
            : stats && stats.current_drawdown > 5
            ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700'
            : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700'
        }`}>
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 mt-0.5" />
            <div>
              <h3 className="font-semibold mb-1">
                Risk Assessment
              </h3>
              <p className="text-sm">
                {stats && stats.current_drawdown > 10 ? (
                  <>
                    <strong>High Risk:</strong> Current drawdown of {formatPercentage(stats.current_drawdown)} 
                    exceeds normal levels. Consider reducing position sizes or reviewing strategy.
                  </>
                ) : stats && stats.current_drawdown > 5 ? (
                  <>
                    <strong>Medium Risk:</strong> Current drawdown of {formatPercentage(stats.current_drawdown)} 
                    is within acceptable range but requires monitoring.
                  </>
                ) : (
                  <>
                    <strong>Low Risk:</strong> Portfolio is performing well with minimal drawdown. 
                    Current exposure appears manageable.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 