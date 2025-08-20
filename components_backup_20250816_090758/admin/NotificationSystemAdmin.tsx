import { useState, useEffect } from 'preact/hooks';
import { useNotificationSettings, useNotificationChannels, useNotificationLogs } from "../../hooks/admin-hooks";
import { Bell, Mail, MessageCircle, Hash, Settings, AlertTriangle, CheckCircle, Clock, Send, Volume2, VolumeX } from 'lucide-preact';

interface NotificationChannel {
  id: string;
  type: 'email' | 'telegram' | 'discord';
  name: string;
  status: 'active' | 'inactive' | 'error' | 'testing';
  config: {
    webhook_url?: string;
    chat_id?: string;
    bot_token?: string;
    email_smtp?: {
      host: string;
      port: number;
      username: string;
      encryption: 'tls' | 'ssl' | 'none';
    };
  };
  last_test: string;
  success_rate: number;
  total_sent: number;
  last_error?: string;
}

interface AlertRule {
  id: string;
  name: string;
  type: 'system' | 'trading' | 'performance' | 'security';
  enabled: boolean;
  conditions: {
    metric: string;
    operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
    value: number;
    timeframe: '1m' | '5m' | '15m' | '30m' | '1h' | '24h';
  }[];
  channels: string[];
  cooldown_minutes: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  last_triggered?: string;
  trigger_count: number;
}

interface NotificationLog {
  id: string;
  timestamp: string;
  rule_name: string;
  channel_type: 'email' | 'telegram' | 'discord';
  channel_name: string;
  status: 'sent' | 'failed' | 'pending';
  message: string;
  error_details?: string;
  response_time_ms?: number;
}

export default function NotificationSystemAdmin() {
  const [refreshInterval, setRefreshInterval] = useState(60); // 1 minute
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [selectedRule, setSelectedRule] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'channels' | 'rules' | 'logs' | 'testing'>('overview');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showNewRuleForm, setShowNewRuleForm] = useState(false);
  const [showNewChannelForm, setShowNewChannelForm] = useState(false);
  const [testingChannel, setTestingChannel] = useState<string | null>(null);

  const { 
    data: settingsData, 
    loading: settingsLoading, 
    error: settingsError, 
    refetch: refetchSettings 
  } = useNotificationSettings(autoRefresh ? refreshInterval : null);

  const { 
    data: channelsData, 
    loading: channelsLoading, 
    error: channelsError, 
    refetch: refetchChannels 
  } = useNotificationChannels(autoRefresh ? refreshInterval : null);

  const { 
    data: logsData, 
    loading: logsLoading, 
    error: logsError, 
    refetch: refetchLogs 
  } = useNotificationLogs(autoRefresh ? refreshInterval : null);

  const handleManualRefresh = () => {
    refetchSettings();
    refetchChannels();
    refetchLogs();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'sent':
        return 'text-green-600 dark:text-green-400';
      case 'testing':
      case 'pending':
        return 'text-blue-600 dark:text-blue-400';
      case 'inactive':
        return 'text-gray-600 dark:text-gray-400';
      case 'error':
      case 'failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'email':
        return Mail;
      case 'telegram':
        return MessageCircle;
      case 'discord':
        return Hash;
      default:
        return Bell;
    }
  };

  const handleTestChannel = async (channelId: string) => {
    setTestingChannel(channelId);
    // TODO: Implement test channel API call
    setTimeout(() => {
      setTestingChannel(null);
    }, 3000);
  };

  if (settingsLoading || channelsLoading || logsLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Bell className="h-8 w-8 mr-3 text-blue-600" />
            Notification System
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

  if (settingsError || channelsError || logsError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Bell className="h-8 w-8 mr-3 text-blue-600" />
            Notification System
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
              Error loading notification system data. Please check system status.
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
          <Bell className="h-8 w-8 mr-3 text-blue-600" />
          Notification System
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
            <option value={30}>30s</option>
            <option value={60}>1m</option>
            <option value={300}>5m</option>
          </select>
          
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
          >
            <Bell className="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* System Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Channels</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {channelsData?.channels?.filter(c => c.status === 'active').length || 0}
              </p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {channelsData?.channels?.length || 0} total configured
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Alert Rules</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {settingsData?.alert_rules?.filter(r => r.enabled).length || 0}
              </p>
            </div>
            <Settings className="h-8 w-8 text-blue-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {settingsData?.alert_rules?.length || 0} total rules
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Today's Notifications</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {logsData?.today_count || 0}
              </p>
            </div>
            <Send className="h-8 w-8 text-purple-600" />
          </div>
          <div className="mt-2">
            <span className={`text-sm ${
              logsData?.success_rate >= 95 ? 'text-green-600 dark:text-green-400' :
              logsData?.success_rate >= 85 ? 'text-yellow-600 dark:text-yellow-400' :
              'text-red-600 dark:text-red-400'
            }`}>
              {logsData?.success_rate || 0}% success rate
            </span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Response Time</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {logsData?.avg_response_time || 0}ms
              </p>
            </div>
            <Clock className="h-8 w-8 text-orange-600" />
          </div>
          <div className="mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Last 24 hours
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Overview', icon: Bell },
            { id: 'channels', name: 'Channels', icon: MessageCircle },
            { id: 'rules', name: 'Alert Rules', icon: Settings },
            { id: 'logs', name: 'Logs', icon: Clock },
            { id: 'testing', name: 'Testing', icon: Clock }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Recent Alerts */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Alerts</h3>
            <div className="space-y-3">
              {logsData?.recent_logs?.slice(0, 5).map((log: NotificationLog) => (
                <div key={log.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center">
                    <div className={`w-3 h-3 rounded-full mr-3 ${
                      log.status === 'sent' ? 'bg-green-500' :
                      log.status === 'pending' ? 'bg-blue-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">{log.rule_name}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        via {log.channel_name} • {new Date(log.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(log.status)} bg-opacity-10`}>
                    {log.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Channel Performance</h3>
              <div className="space-y-3">
                {channelsData?.channels?.map((channel: NotificationChannel) => (
                  <div key={channel.id} className="flex items-center justify-between">
                    <div className="flex items-center">
                      {(() => {
                        const IconComponent = getChannelIcon(channel.type);
                        return <IconComponent className="h-4 w-4 mr-2 text-gray-600" />;
                      })()}
                      <span className="text-sm text-gray-900 dark:text-white">{channel.name}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {channel.success_rate}%
                      </span>
                      <div className={`w-3 h-3 rounded-full ${
                        channel.status === 'active' ? 'bg-green-500' :
                        channel.status === 'testing' ? 'bg-blue-500' : 'bg-red-500'
                      }`}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Active Alert Rules</h3>
              <div className="space-y-3">
                {settingsData?.alert_rules?.filter(r => r.enabled).slice(0, 5).map((rule: AlertRule) => (
                  <div key={rule.id} className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">{rule.name}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {rule.channels.length} channels • Last: {rule.last_triggered ? new Date(rule.last_triggered).toLocaleDateString() : 'Never'}
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(rule.priority)}`}>
                      {rule.priority.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'channels' && (
        <div className="space-y-6">
          {/* Channels Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Notification Channels</h3>
            <button
              onClick={() => setShowNewChannelForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Add Channel
            </button>
          </div>

          {/* Channels Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {channelsData?.channels?.map((channel: NotificationChannel) => (
              <div key={channel.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center">
                    {(() => {
                      const IconComponent = getChannelIcon(channel.type);
                      return <IconComponent className="h-6 w-6 mr-3 text-gray-600" />;
                    })()}
                    <div>
                      <h4 className="font-semibold text-gray-900 dark:text-white">{channel.name}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 capitalize">{channel.type}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    channel.status === 'active' 
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : channel.status === 'testing'
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}>
                    {channel.status}
                  </span>
                </div>
                
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Success Rate:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{channel.success_rate}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Total Sent:</span>
                    <span className="font-medium text-gray-900 dark:text-white">{channel.total_sent}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Last Test:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {new Date(channel.last_test).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleTestChannel(channel.id)}
                    disabled={testingChannel === channel.id}
                    className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm flex items-center justify-center disabled:opacity-50"
                  >
                    {testingChannel === channel.id ? (
                      <>
                        <Clock className="h-4 w-4 mr-1 animate-spin" />
                        Testing...
                      </>
                    ) : (
                      <>
                        <Clock className="h-4 w-4 mr-1" />
                        Test
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setSelectedChannel(selectedChannel === channel.id ? null : channel.id)}
                    className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
                  >
                    Edit
                  </button>
                </div>
                
                {channel.last_error && (
                  <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-600 dark:text-red-400">
                    Error: {channel.last_error}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'rules' && (
        <div className="space-y-6">
          {/* Rules Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Alert Rules</h3>
            <button
              onClick={() => setShowNewRuleForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Add Rule
            </button>
          </div>

          {/* Rules Table */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Rule
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Channels
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
                {settingsData?.alert_rules?.map((rule: AlertRule) => (
                  <tr key={rule.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">{rule.name}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Triggered {rule.trigger_count} times
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900 dark:text-white capitalize">{rule.type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(rule.priority)}`}>
                        {rule.priority.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900 dark:text-white">{rule.channels.length} channels</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {rule.enabled ? (
                          <Volume2 className="h-4 w-4 text-green-600 mr-1" />
                        ) : (
                          <VolumeX className="h-4 w-4 text-gray-400 mr-1" />
                        )}
                        <span className="text-sm text-gray-900 dark:text-white">
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => setSelectedRule(selectedRule === rule.id ? null : rule.id)}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="space-y-6">
          {/* Logs Table */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Notification Logs</h3>
            </div>
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Rule
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Channel
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Response Time
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {logsData?.recent_logs?.map((log: NotificationLog) => (
                  <tr key={log.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">{log.rule_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {(() => {
                          const IconComponent = getChannelIcon(log.channel_type);
                          return <IconComponent className="h-4 w-4 mr-2 text-gray-600" />;
                        })()}
                        <span className="text-sm text-gray-900 dark:text-white">{log.channel_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        log.status === 'sent' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : log.status === 'pending'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {log.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {log.response_time_ms ? `${log.response_time_ms}ms` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'testing' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Test Notification Channels</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Send test notifications to verify your channels are working correctly.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {channelsData?.channels?.map((channel: NotificationChannel) => (
                <div key={channel.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center">
                      {(() => {
                        const IconComponent = getChannelIcon(channel.type);
                        return <IconComponent className="h-5 w-5 mr-2 text-gray-600" />;
                      })()}
                      <span className="font-medium text-gray-900 dark:text-white">{channel.name}</span>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      channel.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 
                      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {channel.status}
                    </span>
                  </div>
                  
                  <button
                    onClick={() => handleTestChannel(channel.id)}
                    disabled={testingChannel === channel.id || channel.status !== 'active'}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    {testingChannel === channel.id ? (
                      <>
                        <Clock className="h-4 w-4 mr-2 animate-spin" />
                        Testing...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Send Test
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 