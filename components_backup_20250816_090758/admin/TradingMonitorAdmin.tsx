import { useState, useEffect } from 'preact/hooks';
import { useAdminData } from '../../hooks/admin-hooks';
import { Activity, TrendingUp, TrendingDown, AlertTriangle, Clock, DollarSign, Target, Zap, BarChart3, Eye } from 'lucide-preact';

interface Position {
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
  exit_layer_analysis: {
    layer_1_pnl: boolean;
    layer_2_technical: boolean;
    layer_3_reversal: boolean;
    layer_4_regime: boolean;
    layer_5_confidence: boolean;
    layer_6_time_risk: boolean;
  };
}

interface TradeExecutionStatus {
  layer_status: {
    position_monitor: { status: 'active' | 'inactive', last_check: string };
    exit_decision_engine: { status: 'active' | 'inactive', decisions_processed: number };
    live_data_integration: { status: 'active' | 'inactive', websocket_connected: boolean };
    trailing_stop_manager: { status: 'active' | 'inactive', active_stops: number };
    regime_adaptive_exit: { status: 'active' | 'inactive', current_regime: string };
    realtime_monitor: { status: 'active' | 'inactive', monitoring_frequency: string };
  };
  performance_metrics: {
    avg_position_duration: string;
    successful_exits: number;
    total_exits: number;
    avg_pnl: number;
    best_performing_layer: string;
  };
  system_health: {
    api_latency: number;
    websocket_uptime: number;
    error_rate: number;
    last_health_check: string;
  };
}

interface TradingMonitorData {
  active_positions_count: number;
  total_portfolio_value: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  open_trades_value: number;
  available_balance: number;
  risk_exposure: number;
  win_rate_today: number;
  avg_hold_time: string;
  total_signals_generated: number;
  signals_executed: number;
  execution_rate: number;
}

export default function TradingMonitorAdmin() {
  const [refreshInterval, setRefreshInterval] = useState(15); // 15 seconds for real trading
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'ACTIVE' | 'PENDING_EXIT' | 'MONITORING'>('ALL');
  const [sortBy, setSortBy] = useState<'pnl' | 'entry_time' | 'confidence' | 'duration'>('pnl');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'execution'>('overview');
  const [filters, setFilters] = useState({
    status: 'all',
    sortBy: 'pnl',
    sortOrder: 'desc' as 'asc' | 'desc'
  });

  // Use simple admin hooks for data fetching
  const { data: monitorData, loading: monitorLoading, error: monitorError, refetch: refetchMonitor } = useAdminData('/api/admin/trading-monitor');
  const { data: positionsData, loading: positionsLoading, error: positionsError, refetch: refetchPositions } = useAdminData('/api/admin/active-positions');
  const { data: executionData, loading: executionLoading, error: executionError, refetch: refetchExecution } = useAdminData('/api/admin/trade-execution-status');

  const handleManualRefresh = () => {
    refetchMonitor();
    refetchPositions();
    refetchExecution();
  };

  const getStatusColor = (status: 'active' | 'inactive') => {
    return status === 'active' 
      ? 'text-green-600 dark:text-green-400' 
      : 'text-red-600 dark:text-red-400';
  };

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600 dark:text-green-400';
    if (pnl < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const filteredPositions = positionsData?.filter(position => 
    filterStatus === 'ALL' || position.status === filterStatus
  ) || [];

  const sortedPositions = [...filteredPositions].sort((a, b) => {
    switch (sortBy) {
      case 'pnl':
        return b.pnl - a.pnl;
      case 'entry_time':
        return new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime();
      case 'confidence':
        return b.confidence - a.confidence;
      case 'duration':
        return parseInt(b.hold_duration) - parseInt(a.hold_duration);
      default:
        return 0;
    }
  });

  const selectedPositionData = selectedPosition 
    ? positionsData?.find(p => p.id === selectedPosition) 
    : null;

  if (monitorLoading || positionsLoading || executionLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Activity className="h-8 w-8 mr-3 text-blue-600" />
            Real Trading
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

  if (monitorError || positionsError || executionError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Activity className="h-8 w-8 mr-3 text-blue-600" />
            Real Trading
          </h2>
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 mr-2" />
            <span className="text-red-800 dark:text-red-200">
              Error loading real trading data. Please check system status.
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
          <Activity className="h-8 w-8 mr-3 text-blue-600" />
          Real Trading
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
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
          </div>
          
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            disabled={!autoRefresh}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800"
          >
            <option value={5}>5s</option>
            <option value={15}>15s</option>
            <option value={30}>30s</option>
            <option value={60}>1m</option>
          </select>
          
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
          >
            <Activity className="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Portfolio Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Portfolio Value</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${monitorData?.total_portfolio_value?.toLocaleString() || '0'}
              </p>
            </div>
            <DollarSign className="h-8 w-8 text-green-600" />
          </div>
          <div className="mt-2">
            <span className={`text-sm font-medium ${getPnLColor(monitorData?.daily_pnl || 0)}`}>
              {monitorData?.daily_pnl_percentage >= 0 ? '+' : ''}
              {monitorData?.daily_pnl_percentage?.toFixed(2)}% today
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Positions</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {monitorData?.active_positions_count || 0}
              </p>
            </div>
            <Target className="h-8 w-8 text-blue-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              ${monitorData?.open_trades_value?.toLocaleString() || '0'} exposure
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Win Rate Today</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {monitorData?.win_rate_today?.toFixed(1) || '0'}%
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Avg hold: {monitorData?.avg_hold_time || 'N/A'}
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Execution Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {monitorData?.execution_rate?.toFixed(1) || '0'}%
              </p>
            </div>
            <Zap className="h-8 w-8 text-yellow-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {monitorData?.signals_executed || 0}/{monitorData?.total_signals_generated || 0} signals
            </span>
          </div>
        </div>
      </div>

      {/* Trade Execution Layer Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Zap className="h-5 w-5 mr-2 text-yellow-600" />
            Trade Execution Layer Status
          </h3>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(executionData?.layer_status || {}).map(([layer, status]) => (
              <div key={layer} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                    {layer.replace(/_/g, ' ')}
                  </h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    status.status === 'active' 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}>
                    {status.status}
                  </span>
                </div>
                
                <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                  {status.last_check && (
                    <p>Last check: {new Date(status.last_check).toLocaleTimeString()}</p>
                  )}
                  {status.decisions_processed !== undefined && (
                    <p>Decisions: {status.decisions_processed}</p>
                  )}
                  {status.websocket_connected !== undefined && (
                    <p>WebSocket: {status.websocket_connected ? 'Connected' : 'Disconnected'}</p>
                  )}
                  {status.active_stops !== undefined && (
                    <p>Active stops: {status.active_stops}</p>
                  )}
                  {status.current_regime && (
                    <p>Regime: {status.current_regime}</p>
                  )}
                  {status.monitoring_frequency && (
                    <p>Frequency: {status.monitoring_frequency}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {/* Performance Metrics */}
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-4">Performance Metrics</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {executionData?.performance_metrics?.avg_position_duration || 'N/A'}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Duration</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {executionData?.performance_metrics?.successful_exits || 0}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Successful Exits</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {executionData?.performance_metrics?.total_exits || 0}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Exits</p>
              </div>
              <div className="text-center">
                <p className={`text-2xl font-bold ${getPnLColor(executionData?.performance_metrics?.avg_pnl || 0)}`}>
                  {executionData?.performance_metrics?.avg_pnl >= 0 ? '+' : ''}
                  {executionData?.performance_metrics?.avg_pnl?.toFixed(2) || '0'}%
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg P&L</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {executionData?.performance_metrics?.best_performing_layer || 'N/A'}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Best Layer</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Positions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <BarChart3 className="h-5 w-5 mr-2 text-blue-600" />
              Active Positions ({filteredPositions.length})
            </h3>
            
            <div className="flex items-center space-x-4">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800"
              >
                <option value="ALL">All Status</option>
                <option value="ACTIVE">Active</option>
                <option value="PENDING_EXIT">Pending Exit</option>
                <option value="MONITORING">Monitoring</option>
              </select>
              
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800"
              >
                <option value="pnl">Sort by P&L</option>
                <option value="entry_time">Sort by Entry Time</option>
                <option value="confidence">Sort by Confidence</option>
                <option value="duration">Sort by Duration</option>
              </select>
            </div>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Position
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Confidence
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Exit Layers
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {sortedPositions.map((position) => (
                <tr key={position.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="flex items-center">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {position.symbol}
                        </span>
                        <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
                          position.side === 'BUY' 
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        }`}>
                          {position.side}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {position.quantity} @ ${position.entry_price}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className={`text-sm font-medium ${getPnLColor(position.pnl)}`}>
                      ${position.pnl.toFixed(2)}
                    </div>
                    <div className={`text-xs ${getPnLColor(position.pnl_percentage)}`}>
                      ({position.pnl_percentage >= 0 ? '+' : ''}{position.pnl_percentage.toFixed(2)}%)
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {position.hold_duration}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2 mr-2">
                        <div 
                          className={`h-2 rounded-full ${
                            position.confidence >= 80 ? 'bg-green-600' :
                            position.confidence >= 60 ? 'bg-yellow-600' : 'bg-red-600'
                          }`}
                          style={{ width: `${position.confidence}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {position.confidence}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex space-x-1">
                      {Object.entries(position.exit_layer_analysis).map(([layer, active]) => (
                        <div
                          key={layer}
                          className={`w-3 h-3 rounded-full ${
                            active ? 'bg-green-600' : 'bg-gray-300 dark:bg-gray-600'
                          }`}
                          title={`Layer ${layer.split('_')[1]}: ${active ? 'Active' : 'Inactive'}`}
                        ></div>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      position.status === 'ACTIVE' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : position.status === 'PENDING_EXIT'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    }`}>
                      {position.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => setSelectedPosition(
                        selectedPosition === position.id ? null : position.id
                      )}
                      className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 flex items-center"
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {sortedPositions.length === 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">No active positions found.</p>
            </div>
          )}
        </div>
      </div>

      {/* Position Details Modal */}
      {selectedPositionData && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Position Details: {selectedPositionData.symbol}
              </h3>
              <button
                onClick={() => setSelectedPosition(null)}
                className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900 dark:text-white">Position Information</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Side:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{selectedPositionData.side}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Quantity:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{selectedPositionData.quantity}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Entry Price:</span>
                    <span className="font-medium text-gray-900 dark:text-white">${selectedPositionData.entry_price}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Current Price:</span>
                    <span className="font-medium text-gray-900 dark:text-white">${selectedPositionData.current_price}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Stop Loss:</span>
                    <span className="font-medium text-gray-900 dark:text-white">${selectedPositionData.stop_loss}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Take Profit:</span>
                    <span className="font-medium text-gray-900 dark:text-white">${selectedPositionData.take_profit}</span>
                  </div>
                </div>
              </div>
              
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900 dark:text-white">6-Layer Exit Analysis</h4>
                <div className="space-y-2">
                  {Object.entries(selectedPositionData.exit_layer_analysis).map(([layer, active]) => (
                    <div key={layer} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                        {layer.replace(/_/g, ' ')}:
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        active 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                      }`}>
                        {active ? 'Triggered' : 'Inactive'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 