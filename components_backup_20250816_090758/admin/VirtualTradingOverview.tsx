import { useState, useEffect } from 'preact/hooks';
import { useAdminData } from '../../hooks/admin-hooks';
import { Activity, TrendingUp, TrendingDown, AlertTriangle, Clock, DollarSign, Target, Zap, BarChart3, Eye, Wallet, Signal } from 'lucide-preact';
import SignalLogsAdmin from './SignalLogsAdmin';

interface VirtualPosition {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  confidence: number;
  entry_time: string;
  hold_duration: string;
  stop_loss: number;
  take_profit: number;
  status: 'ACTIVE' | 'PENDING_EXIT' | 'MONITORING';
  virtual_trade: boolean; // Mark as virtual
}

interface VirtualTradingStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_profit: number;
  avg_loss: number;
  total_pnl: number;
  best_trade: number;
  worst_trade: number;
  avg_hold_time: string;
  sharpe_ratio: number;
  max_drawdown: number;
}

export default function VirtualTradingOverview() {
  const [refreshInterval, setRefreshInterval] = useState(30); // 30 seconds for virtual trading
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('trading'); // 'trading' or 'signals'

  // Use admin data hooks for virtual portfolio trading data
  const { 
    data: tradingData, 
    loading: tradingLoading, 
    error: tradingError 
  } = useAdminData('/api/admin/virtual-portfolio');

  const { 
    data: positionsData, 
    loading: positionsLoading, 
    error: positionsError 
  } = useAdminData('/api/admin/active-positions');

  const handleManualRefresh = () => {
    window.location.reload();
  };

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      // Trigger data refresh
      window.dispatchEvent(new CustomEvent('refreshAdminData'));
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  const selectedPositionData = selectedPosition 
    ? positionsData?.find((p: VirtualPosition) => p.id === selectedPosition) 
    : null;

  // Virtual trading stats (mock data for now)
  const virtualStats: VirtualTradingStats = {
    total_trades: tradingData?.stats?.total_trades || 127,
    winning_trades: tradingData?.stats?.winning_trades || 87,
    losing_trades: tradingData?.stats?.losing_trades || 40,
    win_rate: tradingData?.stats?.win_rate || 68.5,
    avg_profit: tradingData?.stats?.avg_profit || 245.67,
    avg_loss: tradingData?.stats?.avg_loss || -123.45,
    total_pnl: tradingData?.stats?.total_pnl || 755.32,
    best_trade: tradingData?.stats?.best_trade || 892.14,
    worst_trade: tradingData?.stats?.worst_trade || -234.78,
    avg_hold_time: tradingData?.stats?.avg_hold_time || "4h 23m",
    sharpe_ratio: tradingData?.stats?.sharpe_ratio || 2.11,
    max_drawdown: tradingData?.stats?.max_drawdown || -2.01
  };

  if (tradingLoading || positionsLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Wallet className="h-8 w-8 mr-3 text-green-600" />
            Virtual Trading Overview
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (tradingError || positionsError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Wallet className="h-8 w-8 mr-3 text-green-600" />
            Virtual Trading Overview
          </h2>
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Retry
          </button>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 mr-2" />
            <span className="text-red-800 dark:text-red-200">
              Error loading virtual trading data. Please check system status.
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <Wallet className="h-8 w-8 mr-3 text-green-600" />
          Virtual Trading Overview
        </h2>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Auto-refresh:
            </label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
          </div>
          
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md px-3 py-1 text-sm"
          >
            <option value={15}>15s</option>
            <option value={30}>30s</option>
            <option value={60}>1m</option>
            <option value={300}>5m</option>
          </select>
          
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'trading' 
                ? 'border-green-500 text-green-600 dark:text-green-400' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('trading')}
          >
            <div className="flex items-center">
              <BarChart3 className="w-4 h-4 mr-2" />
              Trading
            </div>
          </button>
          <button
            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'signals' 
                ? 'border-green-500 text-green-600 dark:text-green-400' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('signals')}
          >
            <div className="flex items-center">
              <Signal className="w-4 h-4 mr-2" />
              Signal Logs
            </div>
          </button>
        </nav>
      </div>

      {/* Trading Tab */}
      {activeTab === 'trading' && (
        <div className="space-y-6">
          {/* Virtual Trading Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Total Trades */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Trades</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{virtualStats.total_trades}</p>
                  <p className="text-xs text-gray-500 mt-1">Virtual Portfolio</p>
                </div>
                <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </div>

            {/* Win Rate */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Win Rate</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">{virtualStats.win_rate}%</p>
                  <p className="text-xs text-gray-500 mt-1">AI Performance</p>
                </div>
                <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
                  <Target className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
              </div>
            </div>

            {/* Total P&L */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total P&L</p>
                  <p className={`text-2xl font-bold ${virtualStats.total_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    ${virtualStats.total_pnl.toFixed(2)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Virtual Trading</p>
                </div>
                <div className={`p-3 rounded-lg ${virtualStats.total_pnl >= 0 ? 'bg-green-100 dark:bg-green-900/20' : 'bg-red-100 dark:bg-red-900/20'}`}>
                  {virtualStats.total_pnl >= 0 ? (
                    <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
                  ) : (
                    <TrendingDown className="h-6 w-6 text-red-600 dark:text-red-400" />
                  )}
                </div>
              </div>
            </div>

            {/* Sharpe Ratio */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sharpe Ratio</p>
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{virtualStats.sharpe_ratio}</p>
                  <p className="text-xs text-gray-500 mt-1">Risk-Adjusted</p>
                </div>
                <div className="p-3 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                  <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Average Profit */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Profit</p>
                  <p className="text-xl font-bold text-green-600 dark:text-green-400">
                    ${virtualStats.avg_profit.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>

            {/* Average Loss */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Loss</p>
                  <p className="text-xl font-bold text-red-600 dark:text-red-400">
                    ${virtualStats.avg_loss.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>

            {/* Average Hold Time */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                  <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Hold Time</p>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">
                    {virtualStats.avg_hold_time}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Virtual Trading Status */}
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-400 rounded-full mr-3 animate-pulse"></div>
              <div>
                <p className="text-sm font-medium text-green-800 dark:text-green-200">
                  Virtual Trading Active
                </p>
                <p className="text-xs text-green-600 dark:text-green-300 mt-1">
                  AI models are actively generating trading signals for virtual portfolio
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Signal Logs Tab */}
      {activeTab === 'signals' && (
        <div className="space-y-6">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center">
              <Signal className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-3" />
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Virtual Portfolio Signal Logs
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                  Real-time AI trading signals for virtual portfolio management
                </p>
              </div>
            </div>
          </div>
          
          <SignalLogsAdmin />
        </div>
      )}
    </div>
  );
} 