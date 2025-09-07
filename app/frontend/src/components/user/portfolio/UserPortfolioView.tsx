import { useState } from 'preact/hooks';
import { BarChart3, TrendingUp, DollarSign, Activity } from 'lucide-preact';
import { TradingViewChart } from '../../shared/charts';

interface Asset {
  symbol: string;
  name: string;
  value: number;
  percentage: number;
  change24h: number;
  color: string;
}

interface Trade {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  amount: number;
  price: number;
  pnl: number;
  timestamp: string;
  source: 'AI Signal' | 'Manual';
}

export default function UserPortfolioView() {
  const [assets, setAssets] = useState<Asset[]>([
    { symbol: 'BTC', name: 'DollarSign', value: 7500, percentage: 75, change24h: 2.5, color: 'bg-orange-500' },
    { symbol: 'ETH', name: 'Ethereum', value: 2000, percentage: 20, change24h: -1.2, color: 'bg-blue-500' },
    { symbol: 'USDT', name: 'Tether', value: 500, percentage: 5, change24h: 0.0, color: 'bg-green-500' }
  ]);

  const [recentTrades, setRecentTrades] = useState<Trade[]>([
    {
      id: '1',
      symbol: 'BTC/USDT',
      type: 'BUY',
      amount: 0.1,
      price: 45000,
      pnl: 125.50,
      timestamp: '2h ago',
      source: 'AI Signal'
    },
    {
      id: '2',
      symbol: 'ETH/USDT',
      type: 'SELL',
      amount: 1.5,
      price: 2800,
      pnl: 89.25,
      timestamp: '1d ago',
      source: 'Manual'
    },
    {
      id: '3',
      symbol: 'BTC/USDT',
      type: 'BUY',
      amount: 0.05,
      price: 44500,
      pnl: -45.30,
      timestamp: '2d ago',
      source: 'AI Signal'
    }
  ]);

  const [loading, setLoading] = useState(true);
  const totalValue = assets.reduce((sum, asset) => sum + asset.value, 0);

  useEffect(() => {
    // Simulate loading real portfolio data
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div class="animate-pulse space-y-6">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="bg-gray-200 dark:bg-gray-700 h-64 rounded-lg"></div>
          <div class="bg-gray-200 dark:bg-gray-700 h-64 rounded-lg"></div>
        </div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      {/* Portfolio Overview */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Portfolio Overview</h2>
          <div class="text-right">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">
              ${totalValue.toLocaleString()}
            </div>
            <div class="text-sm text-green-600 dark:text-green-400">
              +$1,250.75 (+12.51%)
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Asset Allocation */}
          <div class="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <BarChart3 class="h-5 w-5 mr-2" />
              Asset Allocation
            </h3>
            <div class="space-y-4">
              {assets.map((asset) => (
                <div key={asset.symbol} class="flex items-center justify-between">
                  <div class="flex items-center">
                    <div class={`w-4 h-4 ${asset.color} rounded mr-3`}></div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {asset.name} ({asset.symbol})
                      </div>
                      <div class={`text-xs ${asset.change24h >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {asset.change24h >= 0 ? '+' : ''}{asset.change24h.toFixed(2)}% 24h
                      </div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-semibold text-gray-900 dark:text-white">
                      ${asset.value.toLocaleString()}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {asset.percentage}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Trades */}
          <div class="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Activity class="h-5 w-5 mr-2" />
              Recent Trades
            </h3>
            <div class="space-y-3">
              {recentTrades.map((trade) => (
                <div key={trade.id} class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-600 last:border-b-0">
                  <div>
                    <div class="text-sm font-medium text-gray-900 dark:text-white">
                      {trade.symbol}
                    </div>
                    <div class="flex items-center space-x-2">
                      <span class={`text-xs px-2 py-1 rounded ${
                        trade.type === 'BUY' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {trade.type}
                      </span>
                      <span class={`text-xs px-2 py-1 rounded ${
                        trade.source === 'AI Signal'
                          ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                          : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                      }`}>
                        {trade.source}
                      </span>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class={`text-sm font-semibold ${
                      trade.pnl >= 0 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {trade.timestamp}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Live Market Chart */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div class="p-6 border-b border-gray-200 dark:border-gray-700">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <TrendingUp class="h-5 w-5 mr-2" />
                Live Market Analysis
              </h3>
              <p class="text-sm text-gray-600 dark:text-gray-400">Real-time BTC/USDT market data</p>
            </div>
            <div class="flex items-center space-x-2">
              <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span class="text-xs text-green-600 dark:text-green-400 font-medium">LIVE</span>
            </div>
          </div>
        </div>
        <TradingViewChart 
          symbol="BTCUSDT" 
          defaultInterval="1h" 
          height={400} 
          showToolbar={true} 
        />
      </div>
    </div>
  );
}
