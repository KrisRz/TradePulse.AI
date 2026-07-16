import { useState } from 'preact/hooks';
import { 
  Activity, 
  Brain, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  Wifi,
  WifiOff,
  Clock,
  TrendingUp,
  Pulse,
  Server,
  Database,
  RefreshCw
} from 'lucide-preact';

interface ModelStatus {
  name: string;
  status: 'active' | 'warning' | 'error' | 'maintenance';
  confidence: number;
  lastPrediction: Date;
  predictions24h: number;
  accuracy: number;
  responseTime: number;
}

interface SignalSystemStatus {
  overall: 'healthy' | 'warning' | 'error';
  lastUpdate: Date;
  modelsOnline: number;
  totalModels: number;
  signalsGenerated24h: number;
  avgConfidence: number;
  systemLoad: number;
  uptime: number;
  dataFeedStatus: 'connected' | 'disconnected' | 'delayed';
  databaseStatus: 'connected' | 'slow' | 'error';
  apiStatus: 'operational' | 'degraded' | 'down';
}

interface LiveMetrics {
  currentSignals: number;
  activeStrategies: number;
  avgProcessingTime: number;
  successRate24h: number;
  totalPnL24h: number;
  lastSignalTime: Date;
  signalFrequency: number; // signals per hour
  peakHour: number;
  systemEfficiency: number;
}

interface LiveSignalStatusProps {
  refreshInterval?: number;
  showDetails?: boolean;
  showMetrics?: boolean;
  onStatusChange?: (status: SignalSystemStatus) => void;
  onAlert?: (message: string, type: 'warning' | 'error') => void;
}

export default function LiveSignalStatus({
  refreshInterval = 5000,
  showDetails = true,
  showMetrics = true,
  onStatusChange,
  onAlert
}: LiveSignalStatusProps) {
  const [systemStatus, setSystemStatus] = useState<SignalSystemStatus | null>(null);
  const [modelStatuses, setModelStatuses] = useState<ModelStatus[]>([]);
  const [liveMetrics, setLiveMetrics] = useState<LiveMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    fetchLiveStatus();
    
    // Set up real-time updates
    const interval = setInterval(fetchLiveStatus, refreshInterval);
    
    return () => clearInterval(interval);
  }, [refreshInterval]);

  useEffect(() => {
    if (systemStatus) {
      onStatusChange?.(systemStatus);
      
      // Check for alerts
      if (systemStatus.overall === 'warning') {
        onAlert?.('Signal system performance degraded', 'warning');
      } else if (systemStatus.overall === 'error') {
        onAlert?.('Signal system critical error detected', 'error');
      }
    }
  }, [systemStatus, onStatusChange, onAlert]);

  const fetchLiveStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      setIsConnected(true);
      
      // PRODUCTION: Fetch real brain status (engines_status router, /api/v1 prefix)
      const response = await fetch('/api/v1/brain/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch signal status: ${response.status}`);
      }

      const data = await response.json();
      
      const realSystemStatus: SignalSystemStatus = data.systemStatus || {
        overall: 'healthy',
        lastUpdate: new Date(),
        modelsOnline: 3,
        totalModels: 3,
        signalsGenerated24h: 0,
        avgConfidence: 0,
        systemLoad: 0,
        uptime: 0,
        dataFeedStatus: 'disconnected',
        databaseStatus: 'disconnected',
        apiStatus: 'disconnected'
      };

      const realModelStatuses: ModelStatus[] = data.modelStatuses || [
        {
          name: 'LSTM 1H',
          status: 'inactive',
          confidence: 0,
          lastPrediction: new Date(0),
          predictions24h: 0,
          accuracy: 0,
          responseTime: 0
        },
        {
          name: 'LSTM 4H',
          status: 'inactive',
          confidence: 0,
          lastPrediction: new Date(0),
          predictions24h: 0,
          accuracy: 0,
          responseTime: 0
        },
        {
          name: 'LSTM 24H',
          status: 'inactive',
          confidence: 0,
          lastPrediction: new Date(0),
          predictions24h: 0,
          accuracy: 0,
          responseTime: 0
        }
      ];

      const realLiveMetrics: LiveMetrics = data.liveMetrics || {
        currentSignals: 0,
        activeStrategies: 0,
        avgProcessingTime: 0,
        successRate24h: 0,
        totalPnL24h: 0,
        lastSignalTime: new Date(0),
        signalFrequency: 0,
        peakHour: 0,
        systemEfficiency: 0
      };

      setTimeout(() => {
        setSystemStatus(realSystemStatus);
        setModelStatuses(realModelStatuses);
        setLiveMetrics(realLiveMetrics);
        setLastUpdate(new Date());
        setLoading(false);
      }, 300);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch live status');
      setIsConnected(false);
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'operational':
      case 'connected':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
      case 'degraded':
      case 'slow':
      case 'delayed':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'error':
      case 'down':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'operational':
      case 'connected':
        return CheckCircle;
      case 'warning':
      case 'degraded':
      case 'slow':
      case 'delayed':
        return AlertTriangle;
      case 'error':
      case 'down':
        return XCircle;
      default:
        return Activity;
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  const formatUptime = (uptime: number) => {
    return `${uptime.toFixed(2)}%`;
  };

  if (loading && !systemStatus) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center py-4">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-500 mr-2" />
          <span className="text-gray-600 dark:text-gray-400">Connecting to signal system...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Main Status Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              {isConnected ? (
                <Wifi className="w-6 h-6 text-green-500" />
              ) : (
                <WifiOff className="w-6 h-6 text-red-500" />
              )}
              {systemStatus?.overall === 'healthy' && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              )}
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Signal System Status
              </h3>
              <div className="flex items-center space-x-2">
                <span className={`text-sm font-medium ${getStatusColor(systemStatus?.overall || 'error')}`}>
                  {systemStatus?.overall === 'healthy' ? 'All Systems Operational' :
                   systemStatus?.overall === 'warning' ? 'Minor Issues Detected' :
                   'System Errors Present'}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  • Updated {formatTimeAgo(lastUpdate)}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {systemStatus && (
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900 dark:text-white">
                  {systemStatus.modelsOnline}/{systemStatus.totalModels} Models
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {formatUptime(systemStatus.uptime)} uptime
                </div>
              </div>
            )}
            
            <button
              onClick={fetchLiveStatus}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              title="Refresh status"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* System Components Status */}
      {showDetails && systemStatus && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Data Feed */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Activity className={`w-5 h-5 ${getStatusColor(systemStatus.dataFeedStatus)}`} />
                <span className="font-medium text-gray-900 dark:text-white">Data Feed</span>
              </div>
              <span className={`text-sm font-medium ${getStatusColor(systemStatus.dataFeedStatus)}`}>
                {systemStatus.dataFeedStatus}
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Real-time market data
            </div>
          </div>

          {/* Database */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Database className={`w-5 h-5 ${getStatusColor(systemStatus.databaseStatus)}`} />
                <span className="font-medium text-gray-900 dark:text-white">Database</span>
              </div>
              <span className={`text-sm font-medium ${getStatusColor(systemStatus.databaseStatus)}`}>
                {systemStatus.databaseStatus}
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Signal storage & retrieval
            </div>
          </div>

          {/* API */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className={`w-5 h-5 ${getStatusColor(systemStatus.apiStatus)}`} />
                <span className="font-medium text-gray-900 dark:text-white">API</span>
              </div>
              <span className={`text-sm font-medium ${getStatusColor(systemStatus.apiStatus)}`}>
                {systemStatus.apiStatus}
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Signal generation API
            </div>
          </div>
        </div>
      )}

      {/* AI Models Status */}
      {showDetails && modelStatuses.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            AI Model Status
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {modelStatuses.map((model, index) => {
              const StatusIcon = getStatusIcon(model.status);
              return (
                <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <StatusIcon className={`w-5 h-5 ${getStatusColor(model.status)}`} />
                      <span className="font-medium text-gray-900 dark:text-white">
                        {model.name}
                      </span>
                    </div>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                      model.status === 'active' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : model.status === 'warning'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {model.status}
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Confidence:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {model.confidence.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Accuracy:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {model.accuracy.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Response:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {model.responseTime.toFixed(0)}ms
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Last Signal:</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTimeAgo(model.lastPrediction)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Live Metrics */}
      {showMetrics && liveMetrics && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Live Metrics (24h)
          </h4>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <Pulse className="w-5 h-5 text-blue-500 animate-pulse" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {liveMetrics.currentSignals}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Active Signals</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <Target className="w-5 h-5 text-green-500" />
              </div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {liveMetrics.successRate24h.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Success Rate</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <TrendingUp className="w-5 h-5 text-purple-500" />
              </div>
              <div className={`text-2xl font-bold ${
                liveMetrics.totalPnL24h >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              }`}>
                ${liveMetrics.totalPnL24h.toFixed(0)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Total P&L</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <Zap className="w-5 h-5 text-yellow-500" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {liveMetrics.signalFrequency.toFixed(1)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Signals/Hour</div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Processing Time:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {liveMetrics.avgProcessingTime.toFixed(1)}s
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">System Efficiency:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {liveMetrics.systemEfficiency.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Last Signal:</span>
                <span className="text-gray-500 dark:text-gray-400">
                  {formatTimeAgo(liveMetrics.lastSignalTime)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <XCircle className="w-5 h-5 text-red-500 mr-2" />
            <div>
              <div className="font-medium text-red-900 dark:text-red-200">
                Connection Error
              </div>
              <div className="text-sm text-red-700 dark:text-red-300">
                {error}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Load Indicator */}
      {systemStatus && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">System Load:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {systemStatus.systemLoad.toFixed(1)}%
            </span>
          </div>
          <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                systemStatus.systemLoad < 60 
                  ? 'bg-green-500'
                  : systemStatus.systemLoad < 80
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${Math.min(100, systemStatus.systemLoad)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
} 