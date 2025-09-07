import { useState } from 'preact/hooks';
import { Eye, Download, Filter, Search, RefreshCw, TrendingUp, Activity, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-preact';
import { useSignalLogs } from '../../../hooks/admin-hooks';

// Define the filters type here since it's no longer imported
interface SignalLogsFilters {
  symbol?: string;
  signal_type?: string;
  min_confidence?: number;
  execution_status?: string;
  date_from?: string;
  date_to?: string;
}

type SignalFilterValue = string | number | undefined;

export default function SignalLogsAdmin() {
  const [filters, setFilters] = useState<SignalLogsFilters>({
    symbol: 'BTCUSDT',
    signal_type: undefined,
    min_confidence: 0.5,
    execution_status: undefined,
    date_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
    page: 1,
    limit: 50
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: signalData, loading, error, refetch: refresh } = useSignalLogs();

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refresh();
      }, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refresh]);

  const handleFilterChange = (key: keyof SignalLogsFilters, value: SignalFilterValue) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1 // Reset to first page when filters change
    }));
  };

  const handlePageChange = (newPage: number) => {
    setFilters(prev => ({ ...prev, page: newPage }));
  };

  const getSignalTypeIcon = (type: string) => {
    switch (type) {
      case 'BUY': return <TrendingUp size={16} className="text-green-500" />;
      case 'SELL': return <TrendingDown size={16} className="text-red-500" />;
      case 'HOLD': return <Activity size={16} className="text-gray-500" />;
      default: return <Activity size={16} className="text-gray-500" />;
    }
  };

  const getExecutionStatusBadge = (status: string) => {
    const badges = {
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      executed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[status] || badges.pending}`}>
        {status}
      </span>
    );
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const exportToCSV = () => {
    if (!signalData?.signals) return;
    
    const csvContent = [
      ['Timestamp', 'Symbol', 'Signal Type', 'Confidence', 'Price', 'Execution Status', 'User ID', 'P&L'],
      ...signalData.signals.map(signal => [
        signal.timestamp,
        signal.symbol,
        signal.signal_type,
        signal.confidence.toString(),
        signal.price.toString(),
        signal.execution_status,
        signal.user_id || '',
        signal.profit_loss?.toString() || ''
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `signal-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading && !signalData) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="space-y-3">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Signal Logs Error
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error.message}
          </p>
          <button
            onClick={refresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Controls */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Signal Logs
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Monitor and analyze trading signals from the AI system
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh((e.target as HTMLInputElement).checked)}
                className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">Auto-refresh</span>
            </label>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Filter size={16} />
              <span className="text-sm">Filters</span>
              {showFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            
            <button
              onClick={exportToCSV}
              className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Download size={16} />
              <span className="text-sm">Export</span>
            </button>
            
            <button
              onClick={refresh}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        {signalData?.summary && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Signals</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {signalData.summary.total_signals}
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="text-sm text-green-600 dark:text-green-400">Buy Signals</div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {signalData.summary.buy_signals}
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
              <div className="text-sm text-red-600 dark:text-red-400">Sell Signals</div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {signalData.summary.sell_signals}
              </div>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="text-sm text-blue-600 dark:text-blue-400">Avg Confidence</div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {formatPercentage(signalData.summary.avg_confidence)}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <div className="text-sm text-purple-600 dark:text-purple-400">Execution Rate</div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {formatPercentage(signalData.summary.execution_rate)}
              </div>
            </div>
          </div>
        )}

        {/* Filters Panel */}
        {showFilters && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Symbol
                </label>
                <input
                  type="text"
                  value={filters.symbol || ''}
                  onChange={(e) => handleFilterChange('symbol', (e.target as HTMLInputElement).value)}
                  placeholder="e.g., BTCUSDT"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Signal Type
                </label>
                <select
                  value={filters.signal_type || 'all'}
                  onChange={(e) => handleFilterChange('signal_type', (e.target as HTMLInputElement).value === 'all' ? undefined : (e.target as HTMLInputElement).value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="all">All Types</option>
                  <option value="BUY">Buy</option>
                  <option value="SELL">Sell</option>
                  <option value="HOLD">Hold</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Min Confidence
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={filters.min_confidence || 0}
                  onChange={(e) => handleFilterChange('min_confidence', parseFloat((e.target as HTMLInputElement).value))}
                  className="w-full"
                />
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {formatPercentage(filters.min_confidence || 0)}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Status
                </label>
                <select
                  value={filters.execution_status || 'all'}
                  onChange={(e) => handleFilterChange('execution_status', (e.target as HTMLInputElement).value === 'all' ? undefined : (e.target as HTMLInputElement).value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="executed">Executed</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => handleFilterChange('date_from', (e.target as HTMLInputElement).value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => handleFilterChange('date_to', (e.target as HTMLInputElement).value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Signal Logs Table */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Time & Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Signal & Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Confidence & Models
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Execution
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {signalData?.signals.map((signal) => (
                <>
                  <tr key={`${signal.id}-main`} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {new Date(signal.timestamp).toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                      {signal.symbol}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      {getSignalTypeIcon(signal.signal_type)}
                      <span className={`text-sm font-medium ${
                        signal.signal_type === 'BUY' ? 'text-green-600 dark:text-green-400' :
                        signal.signal_type === 'SELL' ? 'text-red-600 dark:text-red-400' :
                        'text-gray-600 dark:text-gray-400'
                      }`}>
                        {signal.signal_type}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                      {formatCurrency(signal.price)}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className={`text-sm font-semibold ${getConfidenceColor(signal.confidence)}`}>
                      {formatPercentage(signal.confidence)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Ensemble: {formatPercentage(signal.model_predictions.ensemble_score)}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getExecutionStatusBadge(signal.execution_status)}
                    {signal.user_id && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        User: {signal.user_id.slice(0, 8)}...
                      </div>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    {signal.profit_loss !== undefined ? (
                      <div className={`text-sm font-medium ${
                        signal.profit_loss > 0 ? 'text-green-600 dark:text-green-400' :
                        signal.profit_loss < 0 ? 'text-red-600 dark:text-red-400' :
                        'text-gray-600 dark:text-gray-400'
                      }`}>
                        {signal.profit_loss > 0 ? '+' : ''}{formatCurrency(signal.profit_loss)}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => setSelectedSignal(selectedSignal === signal.id ? null : signal.id)}
                      className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
                
                {/* Expanded Details */}
                {selectedSignal === signal.id && (
                  <tr key={`${signal.id}-expanded`}>
                    <td colSpan={6} className="px-6 py-4 bg-gray-50 dark:bg-gray-800">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Technical Indicators
                          </h4>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">RSI:</span>
                              <span className="font-mono">{signal.indicators.rsi.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">MACD:</span>
                              <span className="font-mono">{signal.indicators.macd.toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">Volume Ratio:</span>
                              <span className="font-mono">{signal.indicators.volume_ratio.toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Model Predictions
                          </h4>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">LSTM 1h:</span>
                              <span className="font-mono">{signal.model_predictions.lstm_1h.toFixed(3)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">LSTM 4h:</span>
                              <span className="font-mono">{signal.model_predictions.lstm_4h.toFixed(3)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400">LSTM 24h:</span>
                              <span className="font-mono">{signal.model_predictions.lstm_24h.toFixed(3)}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Additional Info
                          </h4>
                          <div className="space-y-1 text-sm">
                            {signal.trade_id && (
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Trade ID:</span>
                                <span className="font-mono text-xs">{signal.trade_id.slice(0, 12)}...</span>
                              </div>
                            )}
                            {signal.notes && (
                              <div>
                                <span className="text-gray-600 dark:text-gray-400">Notes:</span>
                                <p className="text-xs mt-1 text-gray-500 dark:text-gray-400">{signal.notes}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                </>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {signalData && signalData.total > signalData.limit && (
          <div className="bg-white dark:bg-gray-900 px-6 py-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Showing {((signalData.page - 1) * signalData.limit) + 1} to{' '}
                {Math.min(signalData.page * signalData.limit, signalData.total)} of{' '}
                {signalData.total} results
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePageChange(signalData.page - 1)}
                  disabled={signalData.page <= 1}
                  className="px-3 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Page {signalData.page}
                </span>
                
                <button
                  onClick={() => handlePageChange(signalData.page + 1)}
                  disabled={!signalData.has_next}
                  className="px-3 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 