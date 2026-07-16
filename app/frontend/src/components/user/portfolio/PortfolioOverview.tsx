import { useState, useEffect } from 'preact/hooks';

// Shape of GET /api/portfolio/virtual/overview (app/backend/api/v1/routes/portfolio.py)
interface VirtualPortfolioOverview {
  total_value: number;
  initial_balance: number;
  total_pnl: number;
  total_pnl_percentage: number;
  cash_balance: number;
  active_positions: number;
  closed_positions: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  win_rate_today: number;
  total_realized_pnl: number;
  last_updated: string;
}

// Item shape of GET /api/portfolio/virtual/closed (closed_positions[])
interface ClosedPosition {
  id: string;
  symbol: string;
  type: string;
  size: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  entry_time: string;
  exit_time: string | null;
  status: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
}

function formatSignedPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatRelativeTime(timestamp: string | null): string {
  if (!timestamp) return '—';
  const diffMs = Date.now() - new Date(timestamp).getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return `${Math.max(0, Math.floor(diffMs / 60000))}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export default function PortfolioOverview() {
  const [overview, setOverview] = useState<VirtualPortfolioOverview | null>(null);
  const [recentTrades, setRecentTrades] = useState<ClosedPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real virtual-portfolio data from backend - NO MOCKS!
  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token available');
      }
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const overviewRes = await fetch('/api/portfolio/virtual/overview', { headers });
      if (!overviewRes.ok) {
        throw new Error(`API error: ${overviewRes.status}`);
      }
      const overviewData: VirtualPortfolioOverview = await overviewRes.json();
      setOverview(overviewData);

      // Recent trades = most recent closed positions (real data; empty list is honest)
      const closedRes = await fetch('/api/portfolio/virtual/closed', { headers });
      if (closedRes.ok) {
        const closedData = await closedRes.json();
        const positions: ClosedPosition[] = closedData.closed_positions || [];
        positions.sort((a, b) =>
          new Date(b.exit_time || 0).getTime() - new Date(a.exit_time || 0).getTime()
        );
        setRecentTrades(positions);
      } else {
        setRecentTrades([]);
      }
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load portfolio data');
      // NO FALLBACKS - keep state empty to show error state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  if (loading) {
    return (
      <div class="animate-pulse space-y-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} class="bg-gray-200 dark:bg-gray-700 h-28 rounded-lg"></div>
          ))}
        </div>
        <div class="bg-gray-200 dark:bg-gray-700 h-48 rounded-lg"></div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div class="text-red-600 dark:text-red-400 text-sm font-medium">
          Unable to load portfolio data
        </div>
        {error && (
          <div class="mt-2 text-red-600 dark:text-red-400 text-xs">
            Error: {error}
          </div>
        )}
        <button
          onClick={fetchPortfolioData}
          class="mt-4 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const pnlPositive = overview.total_pnl >= 0;

  return (
    <div class="space-y-8">
      {/* Portfolio Stats */}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-6 rounded-lg text-white">
          <div class="text-blue-100 text-sm font-medium">Total Portfolio Value</div>
          <div class="text-3xl font-bold">{formatCurrency(overview.total_value)}</div>
          <div class="text-blue-100 text-sm mt-1">
            Cash: {formatCurrency(overview.cash_balance)} · Started: {formatCurrency(overview.initial_balance)}
          </div>
        </div>

        <div class={`bg-gradient-to-r ${pnlPositive ? 'from-green-500 to-green-600' : 'from-red-500 to-red-600'} p-6 rounded-lg text-white`}>
          <div class={`${pnlPositive ? 'text-green-100' : 'text-red-100'} text-sm font-medium`}>Total P&L</div>
          <div class="text-3xl font-bold">{formatCurrency(overview.total_pnl)}</div>
          <div class={`${pnlPositive ? 'text-green-100' : 'text-red-100'} text-sm mt-1`}>
            {formatSignedPercent(overview.total_pnl_percentage)} Return
          </div>
        </div>

        <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-6 rounded-lg text-white">
          <div class="text-purple-100 text-sm font-medium">Positions</div>
          <div class="text-3xl font-bold">{overview.active_positions} open</div>
          <div class="text-purple-100 text-sm mt-1">
            {overview.closed_positions} closed · Win rate {overview.win_rate_today.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div class="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Trades</h3>
        <div class="space-y-3">
          {recentTrades.length > 0 ? (
            recentTrades.slice(0, 5).map((trade) => {
              const tradePositive = trade.pnl >= 0;
              return (
                <div key={trade.id} class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-600 last:border-b-0">
                  <div>
                    <div class="text-sm font-medium text-gray-900 dark:text-white">{trade.symbol}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {trade.type} · size {trade.size} · entry {formatCurrency(trade.entry_price)}
                    </div>
                  </div>
                  <div class="text-right">
                    <div class={`text-sm font-semibold ${tradePositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {formatCurrency(trade.pnl)} ({formatSignedPercent(trade.pnl_percentage)})
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {formatRelativeTime(trade.exit_time)}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div class="text-center py-4">
              <div class="text-gray-500 dark:text-gray-400 text-sm">
                No closed trades yet — trades appear here after the paper bot closes a position.
              </div>
            </div>
          )}
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600 text-right text-xs text-gray-500 dark:text-gray-400">
          Updated: {new Date(overview.last_updated).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
