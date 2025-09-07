import { useState } from 'preact/hooks';
import { 
  Activity, 
  Brain, 
  Database, 
  Wifi, 
  WifiOff, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Clock,
  TrendingUp
} from 'lucide-preact';

interface SystemStatus {
  overall: 'healthy' | 'warning' | 'error';
  lastUpdate: Date;
  components: {
    aiModels: {
      status: 'active' | 'loading' | 'error';
      lstm1h: boolean;
      lstm4h: boolean;
      lstm24h: boolean;
      lastPrediction: Date;
    };
    dataFeed: {
      status: 'connected' | 'disconnected' | 'error';
      latency: number;
      messagesReceived: number;
      lastMessage: Date;
    };
    database: {
      status: 'connected' | 'disconnected' | 'error';
      responseTime: number;
      lastWrite: Date;
    };
    trading: {
      status: 'active' | 'paused' | 'error';
      mode: 'virtual' | 'real';
      activePositions: number;
      todayTrades: number;
    };
  };
}

interface TradingStatusIndicatorProps {
  className?: string;
  showDetails?: boolean;
  refreshInterval?: number;
}

export function TradingStatusIndicator({ 
  className = '',
  showDetails = true,
  refreshInterval = 5000
}: TradingStatusIndicatorProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Mock system status data
  const mockStatus: SystemStatus = {
    overall: 'healthy',
    lastUpdate: new Date(),
    components: {
      aiModels: {
        status: 'active',
        lstm1h: true,
        lstm4h: true,
        lstm24h: true,
        lastPrediction: new Date(Date.now() - 30000) // 30 seconds ago
      },
      dataFeed: {
        status: 'connected',
        latency: 45,
        messagesReceived: 1440,
        lastMessage: new Date(Date.now() - 1000) // 1 second ago
      },
      database: {
        status: 'connected',
        responseTime: 23,
        lastWrite: new Date(Date.now() - 2000) // 2 seconds ago
      },
      trading: {
        status: 'active',
        mode: 'virtual',
        activePositions: 3,
        todayTrades: 12
      }
    }
  };

  const fetchSystemStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Replace with real API call
      // const response = await fetch('/api/system/status');
      // const data = await response.json();
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Use real data from backend or show disconnected state
      const realStatus: TradingStatus = data.status || {
        overall: 'disconnected',
        lastUpdate: new Date(),
        components: {
          dataFeed: {
            status: 'disconnected',
            latency: 0,
            messagesReceived: 0,
            lastMessage: new Date(0)
          },
          database: {
            status: 'disconnected',
            responseTime: 0,
            lastWrite: new Date(0)
          },
          aiModels: {
            status: 'inactive',
            modelsOnline: 0,
            totalModels: 3,
            lastPrediction: new Date(0)
          }
        }
      };
      
      setStatus(realStatus);
    } catch (err) {
      setError('Failed to fetch system status');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'connected':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
      case 'loading':
      case 'paused':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'error':
      case 'disconnected':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'connected':
        return 'bg-green-50 dark:bg-green-900/20';
      case 'warning':
      case 'loading':
      case 'paused':
        return 'bg-yellow-50 dark:bg-yellow-900/20';
      case 'error':
      case 'disconnected':
        return 'bg-red-50 dark:bg-red-900/20';
      default:
        return 'bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const getStatusIcon = (status: string, size: number = 16) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'connected':
        return <CheckCircle size={size} />;
      case 'warning':
      case 'loading':
      case 'paused':
        return <AlertTriangle size={size} />;
      case 'error':
      case 'disconnected':
        return <XCircle size={size} />;
      default:
        return <Activity size={size} />;
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  useEffect(() => {
    const interval = setInterval(fetchSystemStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading && !status) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 ${className}`}>
        <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
          <XCircle size={16} />
          <span className="text-sm">System Status Error</span>
        </div>
      </div>
    );
  }

  if (!status) return null;

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`${getStatusColor(status.overall)}`}>
              {getStatusIcon(status.overall, 20)}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                System Status
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Last updated: {formatTimeAgo(status.lastUpdate)}
              </p>
            </div>
          </div>
          
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBgColor(status.overall)} ${getStatusColor(status.overall)}`}>
            {status.overall.charAt(0).toUpperCase() + status.overall.slice(1)}
          </div>
        </div>
      </div>

      {/* Status Overview */}
      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className={`${getStatusColor(status.components.aiModels.status)} mb-1`}>
            <Brain size={20} className="mx-auto" />
          </div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">AI Models</div>
          <div className={`text-xs ${getStatusColor(status.components.aiModels.status)}`}>
            {status.components.aiModels.status}
          </div>
        </div>
        
        <div className="text-center">
          <div className={`${getStatusColor(status.components.dataFeed.status)} mb-1`}>
            {status.components.dataFeed.status === 'connected' ? 
              <Wifi size={20} className="mx-auto" /> : 
              <WifiOff size={20} className="mx-auto" />
            }
          </div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">Data Feed</div>
          <div className={`text-xs ${getStatusColor(status.components.dataFeed.status)}`}>
            {status.components.dataFeed.latency}ms
          </div>
        </div>
        
        <div className="text-center">
          <div className={`${getStatusColor(status.components.database.status)} mb-1`}>
            <Database size={20} className="mx-auto" />
          </div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">Database</div>
          <div className={`text-xs ${getStatusColor(status.components.database.status)}`}>
            {status.components.database.responseTime}ms
          </div>
        </div>
        
        <div className="text-center">
          <div className={`${getStatusColor(status.components.trading.status)} mb-1`}>
            <TrendingUp size={20} className="mx-auto" />
          </div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">Trading</div>
          <div className={`text-xs ${getStatusColor(status.components.trading.status)}`}>
            {status.components.trading.activePositions} active
          </div>
        </div>
      </div>

      {/* Detailed Status */}
      {showDetails && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
          {/* AI Models */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">AI Models</h4>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">1h LSTM</span>
                <div className={`w-2 h-2 rounded-full ${
                  status.components.aiModels.lstm1h ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">4h LSTM</span>
                <div className={`w-2 h-2 rounded-full ${
                  status.components.aiModels.lstm4h ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">24h LSTM</span>
                <div className={`w-2 h-2 rounded-full ${
                  status.components.aiModels.lstm24h ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
              </div>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Last prediction: {formatTimeAgo(status.components.aiModels.lastPrediction)}
            </div>
          </div>

          {/* Trading Info */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Trading Activity</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600 dark:text-gray-400">Mode</div>
                <div className="font-medium text-gray-900 dark:text-white capitalize">
                  {status.components.trading.mode} Trading
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400">Today's Trades</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {status.components.trading.todayTrades}
                </div>
              </div>
            </div>
          </div>

          {/* Performance Stats */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Performance</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600 dark:text-gray-400">Data Messages</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {status.components.dataFeed.messagesReceived.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400">Last DB Write</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {formatTimeAgo(status.components.database.lastWrite)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 