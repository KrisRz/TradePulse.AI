import { useState, useEffect } from 'preact/hooks';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Database, 
  Brain, 
  TrendingUp, 
  Wifi,
  Server,
  Clock,
  Zap,
  RefreshCw,
  HardDrive,
  Users,
  Cpu,
  MemoryStick
} from 'lucide-preact';
import { useSystemStatus } from '../../hooks/admin-hooks';

export default function SystemStatusAdmin() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { data: systemStatus, loading, error, refetch: refresh } = useSystemStatus();

  // Safety check for undefined data
  if (!systemStatus || !systemStatus.components) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading system status...</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 dark:text-green-400';
      case 'warning': return 'text-yellow-600 dark:text-yellow-400';
      case 'error': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 dark:bg-green-900/30';
      case 'warning': return 'bg-yellow-100 dark:bg-yellow-900/30';
      case 'error': return 'bg-red-100 dark:bg-red-900/30';
      default: return 'bg-gray-100 dark:bg-gray-900/30';
    }
  };

  const getStatusIcon = (status: string | boolean) => {
    if (typeof status === 'boolean') {
      return status ? <CheckCircle size={20} /> : <XCircle size={20} />;
    }
    switch (status) {
      case 'healthy': return <CheckCircle size={20} />;
      case 'warning': return <AlertTriangle size={20} />;
      case 'error': return <XCircle size={20} />;
      default: return <Activity size={20} />;
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const formatPercentage = (value: number) => {
    return `${Math.round(value * 100)}%`;
  };

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
  };

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refresh();
      }, 10000); // 10 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refresh]);

  if (loading && !systemStatus) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
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
          <XCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            System Status Error
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

  if (!systemStatus) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${getStatusBg(systemStatus.status)} ${getStatusColor(systemStatus.status)}`}>
              {getStatusIcon(systemStatus.status)}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                System Status Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Last updated: {new Date(systemStatus.server_time).toLocaleString()}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Version {systemStatus.version} • {systemStatus.active_users} active users
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">Auto-refresh</span>
            </label>
            <button
              onClick={refresh}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* Overall Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className={`p-3 rounded-full ${getStatusBg(systemStatus.status)} ${getStatusColor(systemStatus.status)} mr-4`}>
              {getStatusIcon(systemStatus.status)}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Overall Status</h3>
              <p className={`text-sm font-medium ${getStatusColor(systemStatus.status)}`}>
                {systemStatus.status.charAt(0).toUpperCase() + systemStatus.status.slice(1)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mr-4">
              <TrendingUp size={24} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Today's Trades</h3>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {systemStatus.total_trades_today}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 mr-4">
              <Activity size={24} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">System Load</h3>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {systemStatus.system_load.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* System Metrics */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
          System Performance Metrics
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <Clock className="mx-auto h-8 w-8 text-blue-500 mb-2" />
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatUptime(systemStatus.uptime)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Uptime</div>
          </div>
          
          <div className="text-center">
            <Cpu className="mx-auto h-8 w-8 text-green-500 mb-2" />
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatPercentage(systemStatus.cpu_usage)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">CPU Usage</div>
          </div>
          
          <div className="text-center">
            <MemoryStick className="mx-auto h-8 w-8 text-purple-500 mb-2" />
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatPercentage(systemStatus.memory_usage)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Memory Usage</div>
          </div>
          
          <div className="text-center">
            <HardDrive className="mx-auto h-8 w-8 text-orange-500 mb-2" />
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatPercentage(systemStatus.disk_usage)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Disk Usage</div>
          </div>
        </div>
      </div>

      {/* Component Status */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
          Component Health Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Database */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Database size={20} className="text-blue-500" />
                <span className="font-medium text-gray-900 dark:text-white">Database</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.services.database === 'healthy' ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.services.database === 'healthy')}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.services.database === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.services.database === 'healthy' ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {systemStatus.components.database.latency && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Latency</span>
                  <span className="font-medium">{systemStatus.components.database.latency}ms</span>
                </div>
              )}
            </div>
          </div>

          {/* AI Models */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Brain size={20} className="text-purple-500" />
                <span className="font-medium text-gray-900 dark:text-white">AI Models</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.components.ai_models.status ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.components.ai_models.status)}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.components.ai_models.status ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.components.ai_models.status ? 'Operational' : 'Error'}
                </span>
              </div>
              {systemStatus.components.ai_models.accuracy && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Accuracy</span>
                  <span className="font-medium">{formatPercentage(systemStatus.components.ai_models.accuracy)}</span>
                </div>
              )}
              {systemStatus.components.ai_models.last_prediction && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Last Prediction</span>
                  <span className="font-medium">
                    {new Date(systemStatus.components.ai_models.last_prediction).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Data Feed */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Wifi size={20} className="text-green-500" />
                <span className="font-medium text-gray-900 dark:text-white">Data Feed</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.components.data_feed.status ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.components.data_feed.status)}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.components.data_feed.status ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.components.data_feed.status ? 'Streaming' : 'Disconnected'}
                </span>
              </div>
              {systemStatus.components.data_feed.last_update && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Last Update</span>
                  <span className="font-medium">
                    {new Date(systemStatus.components.data_feed.last_update).toLocaleTimeString()}
                  </span>
                </div>
              )}
              {systemStatus.components.data_feed.source && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Source</span>
                  <span className="font-medium">{systemStatus.components.data_feed.source}</span>
                </div>
              )}
            </div>
          </div>

          {/* Trading Engine */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <TrendingUp size={20} className="text-orange-500" />
                <span className="font-medium text-gray-900 dark:text-white">Trading Engine</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.components.trading_engine.status ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.components.trading_engine.status)}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.components.trading_engine.status ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.components.trading_engine.status ? 'Running' : 'Stopped'}
                </span>
              </div>
              {systemStatus.components.trading_engine.active_positions && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Active Positions</span>
                  <span className="font-medium">{systemStatus.components.trading_engine.active_positions}</span>
                </div>
              )}
            </div>
          </div>

          {/* WebSocket */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Wifi size={20} className="text-blue-500" />
                <span className="font-medium text-gray-900 dark:text-white">WebSocket</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.components.websocket.status ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.components.websocket.status)}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.components.websocket.status ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.components.websocket.status ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {systemStatus.components.websocket.connections && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Connections</span>
                  <span className="font-medium">{systemStatus.components.websocket.connections}</span>
                </div>
              )}
            </div>
          </div>

          {/* Cache */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Server size={20} className="text-gray-500" />
                <span className="font-medium text-gray-900 dark:text-white">Cache</span>
              </div>
              <div className={`p-1 rounded-full ${systemStatus.components.cache.status ? 'text-green-500' : 'text-red-500'}`}>
                {getStatusIcon(systemStatus.components.cache.status)}
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Status</span>
                <span className={`font-medium ${systemStatus.components.cache.status ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.components.cache.status ? 'Operational' : 'Error'}
                </span>
              </div>
              {systemStatus.components.cache.hit_rate && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Hit Rate</span>
                  <span className="font-medium">{formatPercentage(systemStatus.components.cache.hit_rate)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 