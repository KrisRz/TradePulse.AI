import { useState, useEffect } from 'preact/hooks';
import { Settings, Power, Database, Trash2, RefreshCw, Server, Shield, AlertTriangle, CheckCircle, Clock, Download } from 'lucide-preact';

interface SystemStatus {
  maintenance_mode: boolean;
  uptime_seconds: number;
  memory_usage: number;
  cpu_usage: number;
  disk_usage: number;
  active_connections: number;
  cache_size_mb: number;
  background_jobs: number;
}

interface SystemSettings {
  trading_enabled: boolean;
  api_rate_limit: number;
  max_positions: number;
  risk_limit_percent: number;
  notification_cooldown: number;
  auto_backup_enabled: boolean;
  debug_mode: boolean;
  log_level: string;
}

interface CacheStats {
  redis_cache: {
    size_mb: number;
    hit_rate: number;
    keys_count: number;
    memory_usage: number;
  };
  application_cache: {
    size_mb: number;
    entries: number;
    last_cleared: string;
  };
  database_cache: {
    query_cache_size: number;
    buffer_pool_size: number;
    cache_hit_ratio: number;
  };
}

export default function SystemControlAdmin() {
  const [activeTab, setActiveTab] = useState('overview');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [systemSettings, setSystemSettings] = useState<SystemSettings | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Mock data for demonstration
  const mockSystemStatus: SystemStatus = {
    maintenance_mode: false,
    uptime_seconds: 86400 * 7, // 7 days
    memory_usage: 67.5,
    cpu_usage: 23.8,
    disk_usage: 45.2,
    active_connections: 156,
    cache_size_mb: 512.7,
    background_jobs: 8
  };

  const mockSystemSettings: SystemSettings = {
    trading_enabled: true,
    api_rate_limit: 1200,
    max_positions: 10,
    risk_limit_percent: 5.0,
    notification_cooldown: 300,
    auto_backup_enabled: true,
    debug_mode: false,
    log_level: 'INFO'
  };

  const mockCacheStats: CacheStats = {
    redis_cache: {
      size_mb: 256.3,
      hit_rate: 94.7,
      keys_count: 15234,
      memory_usage: 78.2
    },
    application_cache: {
      size_mb: 128.5,
      entries: 5672,
      last_cleared: '2024-01-20T06:00:00Z'
    },
    database_cache: {
      query_cache_size: 512,
      buffer_pool_size: 1024,
      cache_hit_ratio: 97.3
    }
  };

  useEffect(() => {
    // Simulate loading system data
    const loadSystemData = async () => {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSystemStatus(mockSystemStatus);
      setSystemSettings(mockSystemSettings);
      setCacheStats(mockCacheStats);
      setLoading(false);
    };

    loadSystemData();
  }, []);

  const handleSystemAction = async (action: string) => {
    setActionLoading(action);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    if (action === 'toggle_maintenance' && systemStatus) {
      setSystemStatus(prev => prev ? {
        ...prev,
        maintenance_mode: !prev.maintenance_mode
      } : null);
    }
    
    setActionLoading(null);
  };

  const updateSystemSetting = (key: keyof SystemSettings, value: any) => {
    setSystemSettings(prev => prev ? { ...prev, [key]: value } : null);
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / (24 * 3600));
    const hours = Math.floor((seconds % (24 * 3600)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const tabs = [
    { id: 'overview', name: 'Overview', icon: Server },
    { id: 'maintenance', name: 'Maintenance', icon: Settings },
    { id: 'cache', name: 'Cache Management', icon: Database },
    { id: 'configuration', name: 'Configuration', icon: Shield }
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">System Control Panel</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const OverviewTab = () => (
    <div className="space-y-6">
      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Server className="h-8 w-8 text-blue-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">System Status</dt>
                  <dd className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {systemStatus?.maintenance_mode ? 'Maintenance' : 'Online'}
                  </dd>
                </dl>
              </div>
            </div>
            <div className={`w-3 h-3 rounded-full ${
              systemStatus?.maintenance_mode ? 'bg-yellow-500' : 'bg-green-500'
            }`}></div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Uptime</dt>
                <dd className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {systemStatus ? formatUptime(systemStatus.uptime_seconds) : '--'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Database className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Cache Size</dt>
                <dd className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {systemStatus?.cache_size_mb.toFixed(1)} MB
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Shield className="h-8 w-8 text-orange-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">Active Connections</dt>
                <dd className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {systemStatus?.active_connections}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Resource Usage */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Resource Usage</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">CPU Usage</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {systemStatus?.cpu_usage.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-600 h-3 rounded-full" 
                  style={{ width: `${systemStatus?.cpu_usage}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Memory Usage</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {systemStatus?.memory_usage.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-green-600 h-3 rounded-full" 
                  style={{ width: `${systemStatus?.memory_usage}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Disk Usage</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {systemStatus?.disk_usage.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-purple-600 h-3 rounded-full" 
                  style={{ width: `${systemStatus?.disk_usage}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Background Jobs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Background Jobs</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Active Jobs:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {systemStatus?.background_jobs}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Queue Status:</span>
              <span className="font-semibold text-green-600">Healthy</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const MaintenanceTab = () => (
    <div className="space-y-6">
      {/* Maintenance Mode */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Maintenance Mode</h3>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center">
                {systemStatus?.maintenance_mode ? (
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
                ) : (
                  <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                )}
                <span className="text-lg font-medium text-gray-900 dark:text-white">
                  {systemStatus?.maintenance_mode ? 'Maintenance Mode Active' : 'System Online'}
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {systemStatus?.maintenance_mode 
                  ? 'Trading is disabled and system is in maintenance mode'
                  : 'All systems operational and trading enabled'
                }
              </p>
            </div>
            <button
              onClick={() => handleSystemAction('toggle_maintenance')}
              disabled={actionLoading === 'toggle_maintenance'}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                systemStatus?.maintenance_mode
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-yellow-600 hover:bg-yellow-700 text-white'
              } disabled:opacity-50`}
            >
              {actionLoading === 'toggle_maintenance' ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                systemStatus?.maintenance_mode ? 'Exit Maintenance' : 'Enter Maintenance'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* System Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">System Actions</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => handleSystemAction('restart_services')}
              disabled={actionLoading === 'restart_services'}
              className="flex items-center justify-center px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'restart_services' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Power className="h-4 w-4 mr-2" />
              )}
              Restart Services
            </button>

            <button
              onClick={() => handleSystemAction('backup_system')}
              disabled={actionLoading === 'backup_system'}
              className="flex items-center justify-center px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'backup_system' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Create Backup
            </button>

            <button
              onClick={() => handleSystemAction('clear_logs')}
              disabled={actionLoading === 'clear_logs'}
              className="flex items-center justify-center px-4 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'clear_logs' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Clear Logs
            </button>

            <button
              onClick={() => handleSystemAction('optimize_database')}
              disabled={actionLoading === 'optimize_database'}
              className="flex items-center justify-center px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'optimize_database' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Database className="h-4 w-4 mr-2" />
              )}
              Optimize Database
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const CacheTab = () => (
    <div className="space-y-6">
      {/* Cache Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Redis Cache</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Size:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.redis_cache.size_mb.toFixed(1)} MB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Hit Rate:</span>
              <span className="font-semibold text-green-600">
                {cacheStats?.redis_cache.hit_rate.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Keys:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.redis_cache.keys_count.toLocaleString()}
              </span>
            </div>
          </div>
          <button
            onClick={() => handleSystemAction('clear_redis_cache')}
            disabled={actionLoading === 'clear_redis_cache'}
            className="w-full mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {actionLoading === 'clear_redis_cache' ? 'Clearing...' : 'Clear Cache'}
          </button>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Application Cache</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Size:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.application_cache.size_mb.toFixed(1)} MB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Entries:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.application_cache.entries.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Last Cleared:</span>
              <span className="font-semibold text-gray-900 dark:text-white text-xs">
                {new Date(cacheStats?.application_cache.last_cleared || '').toLocaleDateString()}
              </span>
            </div>
          </div>
          <button
            onClick={() => handleSystemAction('clear_app_cache')}
            disabled={actionLoading === 'clear_app_cache'}
            className="w-full mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {actionLoading === 'clear_app_cache' ? 'Clearing...' : 'Clear Cache'}
          </button>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Database Cache</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Query Cache:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.database_cache.query_cache_size} MB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Hit Ratio:</span>
              <span className="font-semibold text-green-600">
                {cacheStats?.database_cache.cache_hit_ratio.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Buffer Pool:</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {cacheStats?.database_cache.buffer_pool_size} MB
              </span>
            </div>
          </div>
          <button
            onClick={() => handleSystemAction('optimize_db_cache')}
            disabled={actionLoading === 'optimize_db_cache'}
            className="w-full mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {actionLoading === 'optimize_db_cache' ? 'Optimizing...' : 'Optimize Cache'}
          </button>
        </div>
      </div>

      {/* Bulk Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Bulk Cache Operations</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => handleSystemAction('clear_all_caches')}
              disabled={actionLoading === 'clear_all_caches'}
              className="flex items-center justify-center px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'clear_all_caches' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Clear All Caches
            </button>

            <button
              onClick={() => handleSystemAction('optimize_all_caches')}
              disabled={actionLoading === 'optimize_all_caches'}
              className="flex items-center justify-center px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'optimize_all_caches' ? (
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Optimize All Caches
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const ConfigurationTab = () => (
    <div className="space-y-6">
      {/* Trading Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Trading Configuration</h3>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-white">Trading Enabled</label>
              <p className="text-sm text-gray-600 dark:text-gray-400">Enable or disable all trading activities</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={systemSettings?.trading_enabled || false}
                onChange={(e) => updateSystemSetting('trading_enabled', (e.target as HTMLInputElement).checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              API Rate Limit (requests/minute)
            </label>
            <input
              type="number"
              value={systemSettings?.api_rate_limit || 0}
              onChange={(e) => updateSystemSetting('api_rate_limit', parseInt((e.target as HTMLInputElement).value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Maximum Positions
            </label>
            <input
              type="number"
              value={systemSettings?.max_positions || 0}
              onChange={(e) => updateSystemSetting('max_positions', parseInt((e.target as HTMLInputElement).value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Risk Limit (% of portfolio)
            </label>
            <input
              type="number"
              step="0.1"
              value={systemSettings?.risk_limit_percent || 0}
              onChange={(e) => updateSystemSetting('risk_limit_percent', parseFloat((e.target as HTMLInputElement).value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* System Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">System Settings</h3>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-white">Auto Backup</label>
              <p className="text-sm text-gray-600 dark:text-gray-400">Automatically backup system data daily</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={systemSettings?.auto_backup_enabled || false}
                onChange={(e) => updateSystemSetting('auto_backup_enabled', (e.target as HTMLInputElement).checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-900 dark:text-white">Debug Mode</label>
              <p className="text-sm text-gray-600 dark:text-gray-400">Enable detailed logging for debugging</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={systemSettings?.debug_mode || false}
                onChange={(e) => updateSystemSetting('debug_mode', (e.target as HTMLInputElement).checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Log Level
            </label>
            <select
              value={systemSettings?.log_level || 'INFO'}
              onChange={(e) => updateSystemSetting('log_level', (e.target as HTMLSelectElement).value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Notification Cooldown (seconds)
            </label>
            <input
              type="number"
              value={systemSettings?.notification_cooldown || 0}
              onChange={(e) => updateSystemSetting('notification_cooldown', parseInt((e.target as HTMLInputElement).value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Save Configuration */}
      <div className="flex justify-end">
        <button
          onClick={() => handleSystemAction('save_configuration')}
          disabled={actionLoading === 'save_configuration'}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {actionLoading === 'save_configuration' ? (
            <RefreshCw className="h-4 w-4 animate-spin mr-2 inline" />
          ) : null}
          Save Configuration
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">System Control Panel</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Manage system maintenance, cache, and configuration settings
          </p>
        </div>
        {systemStatus?.maintenance_mode && (
          <div className="flex items-center px-3 py-2 bg-yellow-100 text-yellow-800 rounded-lg">
            <AlertTriangle className="h-4 w-4 mr-2" />
            <span className="text-sm font-medium">Maintenance Mode Active</span>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'maintenance' && <MaintenanceTab />}
        {activeTab === 'cache' && <CacheTab />}
        {activeTab === 'configuration' && <ConfigurationTab />}
      </div>
    </div>
  );
} 