import { useState, useEffect } from 'preact/hooks';
import { Portfolio, PortfolioSummary } from '../../types';

interface PortfolioOverviewProps {
  portfolioId?: string;
}

export default function PortfolioOverview({ portfolioId }: PortfolioOverviewProps) {
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPortfolioSummary();
    
    // Set up real-time updates
    const interval = setInterval(fetchPortfolioSummary, 10000); // Every 10 seconds
    
    // Listen for portfolio updates
    document.addEventListener('portfolio-update', handlePortfolioUpdate);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('portfolio-update', handlePortfolioUpdate);
    };
  }, [portfolioId]);

  const fetchPortfolioSummary = async () => {
    try {
      setLoading(true);
      
      // Mock data for now - will be replaced with API call
      const mockSummary: PortfolioSummary = {
        portfolio: {
          id: '1',
          user_id: 'user1',
          name: 'Main Portfolio',
          balance: 12456.78,
          initial_balance: 10000.00,
          realized_pnl: 1234.56,
          unrealized_pnl: 1222.22,
          total_pnl: 2456.78,
          total_trades: 143,
          winning_trades: 98,
          losing_trades: 45,
          win_rate: 68.5,
          profit_factor: 2.34,
          max_drawdown: -456.78,
          current_drawdown: -123.45,
          positions: [],
          created_at: '2024-01-01T00:00:00Z',
          updated_at: new Date().toISOString()
        },
        daily_pnl: 156.78,
        daily_pnl_percentage: 1.28,
        weekly_pnl: 456.78,
        weekly_pnl_percentage: 3.82,
        monthly_pnl: 1234.56,
        monthly_pnl_percentage: 11.23,
        total_trades_today: 8,
        open_positions_count: 3,
      };

      setTimeout(() => {
        setPortfolioSummary(mockSummary);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError('Failed to fetch portfolio data');
      setLoading(false);
    }
  };

  const handlePortfolioUpdate = (event: any) => {
    const { portfolio } = event.detail;
    if (portfolio && (!portfolioId || portfolio.id === portfolioId)) {
      setPortfolioSummary(prev => prev ? { ...prev, portfolio } : null);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const getPnLColor = (value: number) => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  if (loading) {
    return (
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="p-6">
          <div class="animate-pulse">
            <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} class="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
            <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-red-200 dark:border-red-700 p-6">
        <div class="flex items-center space-x-3">
          <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <h3 class="text-lg font-semibold text-red-900 dark:text-red-100">Error Loading Portfolio</h3>
            <p class="text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
        <button
          onClick={fetchPortfolioSummary}
          class="mt-4 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!portfolioSummary) return null;

  const { portfolio } = portfolioSummary;

  return (
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="p-6 border-b border-gray-200 dark:border-gray-700">
        <div class="flex justify-between items-center">
          <div>
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Portfolio Overview</h2>
            <p class="text-gray-600 dark:text-gray-400 mt-1">{portfolio.name}</p>
          </div>
          
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span class="text-sm text-gray-600 dark:text-gray-400">Live</span>
          </div>
        </div>
      </div>

      <div class="p-6">
        {/* Main Portfolio Value */}
        <div class="mb-6">
          <div class="text-center">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(portfolio.balance)}
            </div>
            <div class={`text-lg font-semibold ${getPnLColor(portfolio.total_pnl)}`}>
              {formatCurrency(portfolio.total_pnl)} ({formatPercentage((portfolio.total_pnl / portfolio.initial_balance) * 100)})
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Total Portfolio Value
            </div>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class={`text-lg font-semibold ${getPnLColor(portfolioSummary.daily_pnl)}`}>
              {formatCurrency(portfolioSummary.daily_pnl)}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">Today</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class={`text-lg font-semibold ${getPnLColor(portfolioSummary.weekly_pnl)}`}>
              {formatCurrency(portfolioSummary.weekly_pnl)}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">This Week</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-lg font-semibold text-blue-600 dark:text-blue-400">
              {portfolio.win_rate.toFixed(1)}%
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">Win Rate</div>
          </div>
          
          <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div class="text-lg font-semibold text-purple-600 dark:text-purple-400">
              {portfolioSummary.open_positions_count}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400">Open Positions</div>
          </div>
        </div>

        {/* Detailed Metrics */}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-3">P&L Breakdown</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Realized P&L:</span>
                <span class={getPnLColor(portfolio.realized_pnl)}>
                  {formatCurrency(portfolio.realized_pnl)}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Unrealized P&L:</span>
                <span class={getPnLColor(portfolio.unrealized_pnl)}>
                  {formatCurrency(portfolio.unrealized_pnl)}
                </span>
              </div>
              <div class="flex justify-between font-semibold">
                <span class="text-gray-900 dark:text-white">Total P&L:</span>
                <span class={getPnLColor(portfolio.total_pnl)}>
                  {formatCurrency(portfolio.total_pnl)}
                </span>
              </div>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-3">Trading Stats</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Total Trades:</span>
                <span class="text-gray-900 dark:text-white">{portfolio.total_trades}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Winning Trades:</span>
                <span class="text-green-600 dark:text-green-400">{portfolio.winning_trades}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Profit Factor:</span>
                <span class="text-blue-600 dark:text-blue-400">{portfolio.profit_factor.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div class="mt-6">
          <div class="flex justify-between text-sm mb-2">
            <span class="text-gray-600 dark:text-gray-400">Portfolio Growth</span>
            <span class="text-gray-900 dark:text-white">
              {formatPercentage((portfolio.total_pnl / portfolio.initial_balance) * 100)}
            </span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div 
              class={`h-2 rounded-full ${
                portfolio.total_pnl >= 0 
                  ? 'bg-green-500' 
                  : 'bg-red-500'
              }`}
              style={{ 
                width: `${Math.min(Math.abs((portfolio.total_pnl / portfolio.initial_balance) * 100), 100)}%` 
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
} 