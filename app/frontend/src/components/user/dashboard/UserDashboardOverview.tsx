import { useState, useEffect } from 'preact/hooks';
import { DollarSign, TrendingUp, Activity, Award } from 'lucide-preact';

interface UserStats {
  portfolioValue: number;
  dailyPnL: number;
  dailyPnLPercentage: number;
  activeSignals: number;
  winRate: number;
}

export default function UserDashboardOverview() {
  const [stats, setStats] = useState<UserStats>({
    portfolioValue: 10000,
    dailyPnL: 125.50,
    dailyPnLPercentage: 1.26,
    activeSignals: 3,
    winRate: 72.3
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading real user data
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div class="animate-pulse">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} class="bg-gray-200 dark:bg-gray-700 h-24 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      {/* Quick Stats */}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <DollarSign class="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <div class="ml-4">
              <div class="text-blue-600 dark:text-blue-400 text-sm font-medium">Portfolio Value</div>
              <div class="text-2xl font-bold text-blue-900 dark:text-blue-100">
                ${stats.portfolioValue.toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <TrendingUp class="h-8 w-8 text-green-600 dark:text-green-400" />
            <div class="ml-4">
              <div class="text-green-600 dark:text-green-400 text-sm font-medium">Today's P&L</div>
              <div class="text-2xl font-bold text-green-900 dark:text-green-100">
                +${stats.dailyPnL.toFixed(2)}
              </div>
              <div class="text-green-600 dark:text-green-400 text-xs">
                +{stats.dailyPnLPercentage.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>

        <div class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Activity class="h-8 w-8 text-purple-600 dark:text-purple-400" />
            <div class="ml-4">
              <div class="text-purple-600 dark:text-purple-400 text-sm font-medium">Active Signals</div>
              <div class="text-2xl font-bold text-purple-900 dark:text-purple-100">
                {stats.activeSignals}
              </div>
              <div class="text-purple-600 dark:text-purple-400 text-xs">
                AI Generated
              </div>
            </div>
          </div>
        </div>

        <div class="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Award class="h-8 w-8 text-orange-600 dark:text-orange-400" />
            <div class="ml-4">
              <div class="text-orange-600 dark:text-orange-400 text-sm font-medium">Win Rate</div>
              <div class="text-2xl font-bold text-orange-900 dark:text-orange-100">
                {stats.winRate.toFixed(1)}%
              </div>
              <div class="text-orange-600 dark:text-orange-400 text-xs">
                Last 30 days
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center">
              <div class="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-900 dark:text-white">New BUY signal for BTC/USDT</span>
            </div>
            <span class="text-xs text-gray-500 dark:text-gray-400">2 min ago</span>
          </div>
          <div class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center">
              <div class="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-900 dark:text-white">Portfolio updated with latest prices</span>
            </div>
            <span class="text-xs text-gray-500 dark:text-gray-400">5 min ago</span>
          </div>
          <div class="flex items-center justify-between py-2">
            <div class="flex items-center">
              <div class="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-900 dark:text-white">AI model confidence: 87%</span>
            </div>
            <span class="text-xs text-gray-500 dark:text-gray-400">10 min ago</span>
          </div>
        </div>
      </div>
    </div>
  );
}
