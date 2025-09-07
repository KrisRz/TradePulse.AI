import { useState } from 'preact/hooks';
import { DollarSign, TrendingUp, Activity, Award } from 'lucide-preact';

interface UserStats {
  portfolioValue: number;
  dailyPnL: number;
  dailyPnLPercentage: number;
  activeSignals: number;
  winRate: number;
}

interface UserDashboardData {
  portfolioValue: number;
  dailyPnL: number;
  dailyPnLPercentage: number;
  activeSignals: number;
  winRate: number;
  recentActivity: Array<{
    type: 'signal' | 'portfolio' | 'ai' | 'trade';
    message: string;
    timestamp: string;
  }>;
}

export default function UserDashboardOverview() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<UserDashboardData['recentActivity']>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real user dashboard data from backend - NO MOCKS!
  const fetchUserDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Fetch real user dashboard overview
      const response = await fetch('http://localhost:9002/api/user/dashboard/overview', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data: UserDashboardData = await response.json();

      // Update state with real data
      setStats({
        portfolioValue: data.portfolioValue,
        dailyPnL: data.dailyPnL,
        dailyPnLPercentage: data.dailyPnLPercentage,
        activeSignals: data.activeSignals,
        winRate: data.winRate
      });

      setRecentActivity(data.recentActivity || []);
      console.log('✅ Loaded real user dashboard data:', data);

    } catch (err) {
      console.error('❌ Error fetching user dashboard data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
      // NO FALLBACKS - keep stats as null to show error state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserDashboardData();
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

  if (error || !stats) {
    return (
      <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div class="flex items-center">
          <div class="text-red-600 dark:text-red-400 text-sm font-medium">
            ❌ Unable to load user dashboard data
          </div>
        </div>
        {error && (
          <div class="mt-2 text-red-600 dark:text-red-400 text-xs">
            Error: {error}
          </div>
        )}
        <button
          onClick={fetchUserDashboardData}
          class="mt-4 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
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
          {recentActivity.length > 0 ? (
            recentActivity.slice(0, 5).map((activity, index) => {
              const getActivityColor = (type: string) => {
                switch (type) {
                  case 'signal': return 'bg-green-500';
                  case 'portfolio': return 'bg-blue-500';
                  case 'ai': return 'bg-purple-500';
                  case 'trade': return 'bg-orange-500';
                  default: return 'bg-gray-500';
                }
              };

              const getActivityIcon = (type: string) => {
                switch (type) {
                  case 'signal': return '📈';
                  case 'portfolio': return '💰';
                  case 'ai': return '🤖';
                  case 'trade': return '⚡';
                  default: return '📝';
                }
              };

              return (
                <div key={index} class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0">
                  <div class="flex items-center">
                    <div class={`w-2 h-2 rounded-full mr-3 ${getActivityColor(activity.type)}`}></div>
                    <span class="text-sm text-gray-900 dark:text-white">
                      {getActivityIcon(activity.type)} {activity.message}
                    </span>
                  </div>
                  <span class="text-xs text-gray-500 dark:text-gray-400">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              );
            })
          ) : (
            <div class="text-center py-4">
              <div class="text-gray-500 dark:text-gray-400 text-sm">
                No recent activity available
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
