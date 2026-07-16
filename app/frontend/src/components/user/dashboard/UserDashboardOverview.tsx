import { useState, useEffect } from 'preact/hooks';
import { DollarSign, TrendingUp, Activity, Award } from 'lucide-preact';

// Shape of GET /api/user/dashboard/overview (app/backend/api/v1/routes/user_portfolio.py)
interface UserDashboardData {
  user_profile: {
    user_id: string;
    email: string;
    account_type: string;
    member_since: string;
  };
  portfolio_snapshot: {
    total_value: number;
    cash_balance: number;
    invested_amount: number;
    daily_pnl: number;
    daily_pnl_percentage: number;
    total_pnl: number;
    total_pnl_percentage: number;
  };
  trading_activity: {
    active_positions: number;
    closed_positions: number;
    total_trades: number;
    win_rate: number;
    trades_today: number;
    pnl_today: number;
  };
  market_context: {
    btc_price: number;
    market_status: string;
    last_signal: string;
  };
  last_updated: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
}

function formatSigned(amount: number): string {
  return `${amount >= 0 ? '+' : ''}${formatCurrency(amount)}`;
}

function formatSignedPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export default function UserDashboardOverview() {
  const [data, setData] = useState<UserDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real user dashboard data from backend - NO MOCKS!
  const fetchUserDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch('/api/user/dashboard/overview', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const payload: UserDashboardData = await response.json();
      setData(payload);
    } catch (err) {
      console.error('Error fetching user dashboard data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
      // NO FALLBACKS - keep data as null to show error state
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

  if (error || !data) {
    return (
      <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div class="flex items-center">
          <div class="text-red-600 dark:text-red-400 text-sm font-medium">
            Unable to load user dashboard data
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

  const snapshot = data.portfolio_snapshot;
  const activity = data.trading_activity;
  const dailyPositive = snapshot.daily_pnl >= 0;

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
                {formatCurrency(snapshot.total_value)}
              </div>
              <div class="text-blue-600 dark:text-blue-400 text-xs">
                Cash: {formatCurrency(snapshot.cash_balance)}
              </div>
            </div>
          </div>
        </div>

        <div class={`${dailyPositive ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'} p-4 rounded-lg`}>
          <div class="flex items-center">
            <TrendingUp class={`h-8 w-8 ${dailyPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`} />
            <div class="ml-4">
              <div class={`text-sm font-medium ${dailyPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>Today's P&L</div>
              <div class={`text-2xl font-bold ${dailyPositive ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'}`}>
                {formatSigned(snapshot.daily_pnl)}
              </div>
              <div class={`text-xs ${dailyPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatSignedPercent(snapshot.daily_pnl_percentage)}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Activity class="h-8 w-8 text-purple-600 dark:text-purple-400" />
            <div class="ml-4">
              <div class="text-purple-600 dark:text-purple-400 text-sm font-medium">Active Positions</div>
              <div class="text-2xl font-bold text-purple-900 dark:text-purple-100">
                {activity.active_positions}
              </div>
              <div class="text-purple-600 dark:text-purple-400 text-xs">
                Open trades
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
                {activity.win_rate.toFixed(1)}%
              </div>
              <div class="text-orange-600 dark:text-orange-400 text-xs">
                {activity.closed_positions} closed trades
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Activity */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Trading Activity</h3>
        {activity.total_trades === 0 ? (
          <div class="text-center py-4">
            <div class="text-gray-500 dark:text-gray-400 text-sm">
              No trades yet — the paper bot opens positions when its strategy signals an entry.
            </div>
          </div>
        ) : (
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">Trades today</div>
              <div class="text-xl font-bold text-gray-900 dark:text-white">{activity.trades_today}</div>
            </div>
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">P&L today</div>
              <div class={`text-xl font-bold ${activity.pnl_today >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatSigned(activity.pnl_today)}
              </div>
            </div>
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">Total trades</div>
              <div class="text-xl font-bold text-gray-900 dark:text-white">{activity.total_trades}</div>
            </div>
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">Total P&L</div>
              <div class={`text-xl font-bold ${snapshot.total_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatSigned(snapshot.total_pnl)} ({formatSignedPercent(snapshot.total_pnl_percentage)})
              </div>
            </div>
          </div>
        )}
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>BTC price: {formatCurrency(data.market_context.btc_price)}</span>
          <span>Updated: {new Date(data.last_updated).toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
