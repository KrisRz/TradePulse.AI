import { useState, useEffect } from 'preact/hooks';
import { BarChart3, TrendingUp, Calendar, Award, DollarSign, Activity } from 'lucide-preact';

interface PerformanceData {
  period: string;
  value: number;
  change: number;
  changePercent: number;
}

interface MonthlyData {
  month: string;
  pnl: number;
  trades: number;
  winRate: number;
}

export default function UserBasicAnalytics() {
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([
    { period: '24h', value: 125.50, change: 125.50, changePercent: 1.26 },
    { period: '7d', value: 892.30, change: 234.80, changePercent: 8.92 },
    { period: '30d', value: 1250.75, change: 358.25, changePercent: 12.51 },
    { period: '90d', value: 2847.60, change: 1597.85, changePercent: 28.48 }
  ]);

  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([
    { month: 'Jan', pnl: 450.25, trades: 24, winRate: 75.0 },
    { month: 'Feb', pnl: 623.80, trades: 31, winRate: 71.0 },
    { month: 'Mar', pnl: 389.15, trades: 28, winRate: 68.0 },
    { month: 'Apr', pnl: 587.95, trades: 33, winRate: 73.0 },
    { month: 'May', pnl: 796.45, trades: 29, winRate: 76.0 },
    { month: 'Jun', pnl: 1250.75, trades: 35, winRate: 72.3 }
  ]);

  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('30d');

  useEffect(() => {
    // Simulate loading real analytics data
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const totalTrades = monthlyData.reduce((sum, month) => sum + month.trades, 0);
  const avgWinRate = monthlyData.reduce((sum, month) => sum + month.winRate, 0) / monthlyData.length;
  const totalPnL = monthlyData.reduce((sum, month) => sum + month.pnl, 0);

  if (loading) {
    return (
      <div class="animate-pulse space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} class="bg-gray-200 dark:bg-gray-700 h-24 rounded-lg"></div>
          ))}
        </div>
        <div class="bg-gray-200 dark:bg-gray-700 h-96 rounded-lg"></div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      {/* Performance Overview */}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        {performanceData.map((data) => (
          <div 
            key={data.period}
            class={`p-4 rounded-lg cursor-pointer transition-all ${
              selectedPeriod === data.period
                ? 'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:shadow-md'
            }`}
            onClick={() => setSelectedPeriod(data.period)}
          >
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm text-gray-500 dark:text-gray-400 font-medium">
                  {data.period.toUpperCase()}
                </div>
                <div class="text-xl font-bold text-gray-900 dark:text-white">
                  ${data.value.toFixed(2)}
                </div>
                <div class={`text-sm flex items-center ${
                  data.changePercent >= 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                }`}>
                  <TrendingUp class="h-3 w-3 mr-1" />
                  {data.changePercent >= 0 ? '+' : ''}{data.changePercent.toFixed(2)}%
                </div>
              </div>
              <div class={`p-2 rounded-lg ${
                selectedPeriod === data.period
                  ? 'bg-blue-100 dark:bg-blue-800'
                  : 'bg-gray-100 dark:bg-gray-700'
              }`}>
                <Calendar class="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Key Metrics */}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <DollarSign class="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500 dark:text-gray-400">Total P&L</div>
              <div class="text-2xl font-bold text-gray-900 dark:text-white">
                ${totalPnL.toFixed(2)}
              </div>
              <div class="text-sm text-green-600 dark:text-green-400">
                +{((totalPnL / 10000) * 100).toFixed(2)}% ROI
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <Activity class="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500 dark:text-gray-400">Total Trades</div>
              <div class="text-2xl font-bold text-gray-900 dark:text-white">
                {totalTrades}
              </div>
              <div class="text-sm text-blue-600 dark:text-blue-400">
                {(totalTrades / 6).toFixed(1)} per month
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <Award class="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div class="ml-4">
              <div class="text-sm text-gray-500 dark:text-gray-400">Avg Win Rate</div>
              <div class="text-2xl font-bold text-gray-900 dark:text-white">
                {avgWinRate.toFixed(1)}%
              </div>
              <div class="text-sm text-purple-600 dark:text-purple-400">
                AI-Assisted Trading
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Monthly Performance Chart */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <BarChart3 class="h-5 w-5 mr-2" />
            Monthly Performance
          </h3>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            Last 6 months
          </div>
        </div>

        <div class="space-y-4">
          {monthlyData.map((month, index) => {
            const maxPnL = Math.max(...monthlyData.map(m => m.pnl));
            const barWidth = (month.pnl / maxPnL) * 100;
            
            return (
              <div key={month.month} class="flex items-center space-x-4">
                <div class="w-12 text-sm font-medium text-gray-900 dark:text-white">
                  {month.month}
                </div>
                
                <div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 relative">
                  <div 
                    class="bg-gradient-to-r from-green-500 to-green-600 h-6 rounded-full flex items-center justify-end pr-2"
                    style={{ width: `${barWidth}%` }}
                  >
                    <span class="text-white text-xs font-medium">
                      ${month.pnl.toFixed(0)}
                    </span>
                  </div>
                </div>
                
                <div class="w-16 text-right">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">
                    {month.trades}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    trades
                  </div>
                </div>
                
                <div class="w-16 text-right">
                  <div class="text-sm font-medium text-purple-600 dark:text-purple-400">
                    {month.winRate.toFixed(1)}%
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">
                    win rate
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trading Statistics */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Trading Statistics
        </h3>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-2xl font-bold text-green-600 dark:text-green-400">
              {Math.round(totalTrades * avgWinRate / 100)}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">Winning Trades</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-2xl font-bold text-red-600 dark:text-red-400">
              {totalTrades - Math.round(totalTrades * avgWinRate / 100)}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">Losing Trades</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
              ${(totalPnL / Math.round(totalTrades * avgWinRate / 100)).toFixed(0)}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">Avg Win</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
              2.4
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">Risk/Reward</div>
          </div>
        </div>
      </div>
    </div>
  );
}
