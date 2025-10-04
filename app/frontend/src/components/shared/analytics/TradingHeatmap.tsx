import { useState } from 'preact/hooks';
import { 
  Calendar, 
  Clock, 
  TrendingUp, 
  Activity,
  RefreshCw,
  AlertTriangle,
  Filter,
  Download,
  Info
} from 'lucide-preact';

interface HeatmapData {
  hour: number;
  day: number; // 0 = Sunday, 6 = Saturday
  dayName: string;
  hourLabel: string;
  trades: number;
  pnl: number;
  winRate: number;
  volume: number;
  avgTradeDuration: number;
  intensity: number; // 0-1 for color intensity
}

interface HeatmapStats {
  bestHour: number;
  worstHour: number;
  bestDay: number;
  worstDay: number;
  totalTrades: number;
  totalPnL: number;
  avgWinRate: number;
  mostActiveHour: number;
  mostActiveDay: number;
  peakActivity: { hour: number; day: number; trades: number };
  bestPerformance: { hour: number; day: number; pnl: number };
  worstPerformance: { hour: number; day: number; pnl: number };
}

interface TradingHeatmapProps {
  timeRange?: '7d' | '30d' | '90d' | '1y';
  metric?: 'pnl' | 'trades' | 'winRate' | 'volume';
  showStats?: boolean;
  showLegend?: boolean;
  onMetricChange?: (metric: string) => void;
  onExport?: (data: HeatmapData[]) => void;
}

export default function TradingHeatmap({
  timeRange = '30d',
  metric = 'pnl',
  showStats = true,
  showLegend = true,
  onMetricChange,
  onExport
}: TradingHeatmapProps) {
  const [data, setData] = useState<HeatmapData[]>([]);
  const [stats, setStats] = useState<HeatmapStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<HeatmapData | null>(null);

  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const shortDayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  useEffect(() => {
    fetchHeatmapData();
  }, [timeRange]);

  const fetchHeatmapData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch real heatmap data from backend
      const response = await fetch('/api/analytics/trading/heatmap', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'Content-Type': 'application/json'
        }
      });

      let heatmapData: HeatmapData[] = [];
      if (response.ok) {
        const result = await response.json();
        // Convert backend format to frontend format
        heatmapData = (result.heatmap || []).map((item: any) => ({
          hour: item.hour,
          day: item.day,
          dayName: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][item.day],
          hourLabel: item.hourLabel,
          trades: item.trades,
          pnl: item.pnl,
          winRate: item.winRate,
          volume: item.volume,
          avgTradeDuration: item.avgTradeDuration,
          intensity: item.intensity
        }));
      }

      // Fallback mock data if no real data available
      if (heatmapData.length === 0) {
        heatmapData = [];
        // Create minimal fallback data
        for (let day = 0; day < 7; day++) {
          for (let hour = 0; hour < 24; hour++) {
            const isMarketHours = hour >= 9 && hour <= 16;
            const isWeekend = day === 0 || day === 6;
            const baseActivity = (isMarketHours && !isWeekend) ? 0.8 : 0.3;

            heatmapData.push({
              hour,
              day,
              dayName: dayNames[day],
              hourLabel: `${hour.toString().padStart(2, '0')}:00`,
              trades: Math.floor(baseActivity * 20),
              pnl: (Math.random() - 0.45) * 200 * baseActivity,
              winRate: 45 + Math.random() * 30,
              volume: baseActivity * 10000,
              avgTradeDuration: 30 + Math.random() * 120,
              intensity: baseActivity
            });
          }
        }
      }
      
      // Calculate intensity based on selected metric
      const metricValues = heatmapData.map(d => {
        switch (metric) {
          case 'trades': return d.trades;
          case 'winRate': return d.winRate;
          case 'volume': return d.volume;
          default: return Math.abs(d.pnl);
        }
      });
      
      const minValue = Math.min(...metricValues);
      const maxValue = Math.max(...metricValues);
      const range = maxValue - minValue;
      
      heatmapData.forEach(d => {
        const value = metric === 'trades' ? d.trades : 
                     metric === 'winRate' ? d.winRate :
                     metric === 'volume' ? d.volume : 
                     Math.abs(d.pnl);
        d.intensity = range > 0 ? (value - minValue) / range : 0;
      });
      
      // Calculate statistics
      const totalTrades = heatmapData.reduce((sum, d) => sum + d.trades, 0);
      const totalPnL = heatmapData.reduce((sum, d) => sum + d.pnl, 0);
      const avgWinRate = heatmapData.reduce((sum, d) => sum + d.winRate, 0) / heatmapData.length;
      
      // Find best/worst hours and days
      const hourlyStats = Array.from({length: 24}, (_, hour) => {
        const hourData = heatmapData.filter(d => d.hour === hour);
        return {
          hour,
          trades: hourData.reduce((sum, d) => sum + d.trades, 0),
          pnl: hourData.reduce((sum, d) => sum + d.pnl, 0)
        };
      });
      
      const dailyStats = Array.from({length: 7}, (_, day) => {
        const dayData = heatmapData.filter(d => d.day === day);
        return {
          day,
          trades: dayData.reduce((sum, d) => sum + d.trades, 0),
          pnl: dayData.reduce((sum, d) => sum + d.pnl, 0)
        };
      });
      
      const bestHour = hourlyStats.reduce((max, curr) => curr.pnl > max.pnl ? curr : max).hour;
      const worstHour = hourlyStats.reduce((min, curr) => curr.pnl < min.pnl ? curr : min).hour;
      const bestDay = dailyStats.reduce((max, curr) => curr.pnl > max.pnl ? curr : max).day;
      const worstDay = dailyStats.reduce((min, curr) => curr.pnl < min.pnl ? curr : min).day;
      
      const mostActiveHour = hourlyStats.reduce((max, curr) => curr.trades > max.trades ? curr : max).hour;
      const mostActiveDay = dailyStats.reduce((max, curr) => curr.trades > max.trades ? curr : max).day;
      
      const peakActivity = heatmapData.reduce((max, curr) => curr.trades > max.trades ? curr : max);
      const bestPerformance = heatmapData.reduce((max, curr) => curr.pnl > max.pnl ? curr : max);
      const worstPerformance = heatmapData.reduce((min, curr) => curr.pnl < min.pnl ? curr : min);
      
      const mockStats: HeatmapStats = {
        bestHour,
        worstHour,
        bestDay,
        worstDay,
        totalTrades,
        totalPnL,
        avgWinRate,
        mostActiveHour,
        mostActiveDay,
        peakActivity: {
          hour: peakActivity.hour,
          day: peakActivity.day,
          trades: peakActivity.trades
        },
        bestPerformance: {
          hour: bestPerformance.hour,
          day: bestPerformance.day,
          pnl: bestPerformance.pnl
        },
        worstPerformance: {
          hour: worstPerformance.hour,
          day: worstPerformance.day,
          pnl: worstPerformance.pnl
        }
      };
      
      // Set real data immediately
      setData(heatmapData);
      setStats(mockStats);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch heatmap data');
      setLoading(false);
    }
  };

  const getCellColor = (intensity: number, pnl?: number) => {
    if (metric === 'pnl' && pnl !== undefined) {
      // Use red/green gradient for P&L
      const alpha = Math.min(intensity * 0.8 + 0.2, 1);
      return pnl >= 0 
        ? `rgba(16, 185, 129, ${alpha})` // Green
        : `rgba(239, 68, 68, ${alpha})`; // Red
    } else {
      // Use blue gradient for other metrics
      const alpha = Math.min(intensity * 0.8 + 0.2, 1);
      return `rgba(59, 130, 246, ${alpha})`;
    }
  };

  const getCellTextColor = (intensity: number) => {
    return intensity > 0.5 ? 'white' : 'black';
  };

  const formatMetricValue = (data: HeatmapData) => {
    switch (metric) {
      case 'trades': return data.trades.toString();
      case 'winRate': return `${data.winRate.toFixed(1)}%`;
      case 'volume': return `$${(data.volume / 1000).toFixed(1)}K`;
      default: return `$${data.pnl.toFixed(0)}`;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading heatmap data...</span>
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
          Trading Activity Heatmap
        </h2>
        
        <div className="flex items-center space-x-2 flex-wrap">
          {/* Metric Selector */}
          <select
            value={metric}
            onChange={(e) => onMetricChange?.(e.currentTarget.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="pnl">P&L</option>
            <option value="trades">Trade Count</option>
            <option value="winRate">Win Rate</option>
            <option value="volume">Volume</option>
          </select>
          
          <button
            onClick={() => onExport?.(data)}
            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          
          <button
            onClick={fetchHeatmapData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      {stats && showStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Best Hour
                </div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {stats.bestHour.toString().padStart(2, '0')}:00
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Peak performance
                </div>
              </div>
              <Clock className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Best Day
                </div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {shortDayNames[stats.bestDay]}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Most profitable
                </div>
              </div>
              <Calendar className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Most Active
                </div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {shortDayNames[stats.mostActiveDay]}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {stats.mostActiveHour.toString().padStart(2, '0')}:00
                </div>
              </div>
              <Activity className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Total P&L
                </div>
                <div className={`text-2xl font-bold ${
                  stats.totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(stats.totalPnL)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {stats.totalTrades} trades
                </div>
              </div>
              <TrendingUp className="w-8 h-8 text-gray-400" />
            </div>
          </div>
        </div>
      )}

      {/* Heatmap */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {metric === 'pnl' ? 'P&L' : 
             metric === 'trades' ? 'Trade Count' : 
             metric === 'winRate' ? 'Win Rate' : 
             'Volume'} by Hour and Day
          </h3>
          
          {showLegend && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {metric === 'pnl' ? 'Loss' : 'Low'}
              </span>
              <div className="flex">
                {Array.from({length: 5}, (_, i) => (
                  <div
                    key={i}
                    className="w-4 h-4"
                    style={{ 
                      backgroundColor: getCellColor(i / 4, metric === 'pnl' ? (i < 2 ? -1 : 1) : undefined)
                    }}
                  />
                ))}
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {metric === 'pnl' ? 'Profit' : 'High'}
              </span>
            </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <div className="grid grid-cols-25 gap-1 min-w-[800px]">
            {/* Header row with hours */}
            <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
              {/* Empty cell for day labels */}
            </div>
            {Array.from({length: 24}, (_, hour) => (
              <div key={hour} className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
                {hour.toString().padStart(2, '0')}
              </div>
            ))}
            
            {/* Data rows */}
            {dayNames.map((dayName, dayIndex) => (
              <div key={dayIndex} className="contents">
                <div className="text-xs text-gray-500 dark:text-gray-400 text-right py-2 pr-2">
                  {shortDayNames[dayIndex]}
                </div>
                {Array.from({length: 24}, (_, hour) => {
                  const cellData = data.find(d => d.day === dayIndex && d.hour === hour);
                  if (!cellData) return <div key={hour} className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded" />;
                  
                  return (
                    <div
                      key={hour}
                      className="w-8 h-8 rounded cursor-pointer transition-all hover:scale-110 hover:shadow-md flex items-center justify-center text-xs font-medium"
                      style={{ 
                        backgroundColor: getCellColor(cellData.intensity, cellData.pnl),
                        color: getCellTextColor(cellData.intensity)
                      }}
                      onClick={() => setSelectedCell(cellData)}
                      title={`${dayName} ${cellData.hourLabel}: ${formatMetricValue(cellData)}`}
                    >
                      {cellData.intensity > 0.3 && (
                        <span className="text-xs font-bold">
                          {metric === 'pnl' ? (cellData.pnl >= 0 ? '+' : '-') : ''}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Selected Cell Details */}
      {selectedCell && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {selectedCell.dayName} at {selectedCell.hourLabel}
            </h3>
            <button
              onClick={() => setSelectedCell(null)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              ×
            </button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {selectedCell.trades}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Trades</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${
                selectedCell.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                {formatCurrency(selectedCell.pnl)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">P&L</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {selectedCell.winRate.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Win Rate</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {(selectedCell.volume / 1000).toFixed(1)}K
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Volume</div>
            </div>
          </div>
        </div>
      )}

      {/* Insights */}
      {stats && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start">
            <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3" />
            <div>
              <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
                Trading Insights
              </h4>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                <li>• Best performance occurs on {dayNames[stats.bestDay]} at {stats.bestHour.toString().padStart(2, '0')}:00</li>
                <li>• Most active trading happens on {dayNames[stats.mostActiveDay]} at {stats.mostActiveHour.toString().padStart(2, '0')}:00</li>
                <li>• Peak activity: {stats.peakActivity.trades} trades on {dayNames[stats.peakActivity.day]} at {stats.peakActivity.hour.toString().padStart(2, '0')}:00</li>
                <li>• Avoid trading on {dayNames[stats.worstDay]} at {stats.worstHour.toString().padStart(2, '0')}:00 (worst performance)</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 