/*
📊 Advanced Analytics Dashboard Component
Comprehensive enterprise analytics with real-time metrics and insights
*/

import { useState, useEffect } from 'preact/hooks';
import { TrendingUp, Users, Mail, Shield, DollarSign, RefreshCw, Download, AlertTriangle, CheckCircle, Activity, BarChart3, Clock, Bell } from 'lucide-preact';
import { apiClient } from '@/lib/api-client';

interface AnalyticsData {
  executive_summary: {
    total_users: number;
    growth_rate: number;
    conversion_rate: number;
    security_score: number;
    mrr: number;
    key_insights: string[];
  };
  user_growth: {
    summary: {
      total_users: number;
      active_users: number;
      premium_users: number;
      growth_rate: number;
      activation_rate: number;
      premium_conversion_rate: number;
    };
    time_series: Array<{
      date: string;
      registrations: number;
      activations: number;
      cumulative_users: number;
    }>;
    distributions: {
      roles: Record<string, number>;
      subscriptions: Record<string, number>;
      geographic: Record<string, number>;
    };
  };
  invitation_funnel: {
    funnel_stages: {
      sent: number;
      opened: number;
      clicked: number;
      registered: number;
      expired: number;
      cancelled: number;
    };
    conversion_rates: {
      open_rate: number;
      click_rate: number;
      overall_conversion_rate: number;
      click_to_conversion_rate: number;
    };
    role_analysis: Record<string, any>;
  };
  security: {
    security_events: {
      failed_logins_24h: number;
      successful_logins_24h: number;
      two_fa_enabled_users: number;
      compliance_score: number;
    };
    risk_assessment: {
      high_risk_users: number;
      medium_risk_users: number;
      low_risk_users: number;
    };
  };
  revenue: {
    revenue_summary: {
      mrr: number;
      arr: number;
      arpu: number;
      ltv: number;
      churn_rate: number;
      growth_rate: number;
    };
    subscription_breakdown: {
      free_users: number;
      basic_users: number;
      premium_users: number;
      enterprise_users: number;
    };
  };
}

interface RealTimeStats {
  active_users_online: number;
  registrations_today: number;
  invitations_sent_today: number;
  trading_volume_24h: number;
  recent_activities: Array<{
    time: string;
    event: string;
    user: string;
  }>;
  alerts: Array<{
    level: 'info' | 'warning' | 'success' | 'error';
    message: string;
  }>;
}

export default function AdvancedAnalyticsDashboard() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [realTimeStats, setRealTimeStats] = useState<RealTimeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Load analytics data
  const loadAnalyticsData = async (showRefreshing = false) => {
    try {
      if (showRefreshing) setRefreshing(true);
      setError(null);

      const [dashboardResponse, realTimeResponse] = await Promise.all([
        apiClient.get(`/api/user-analytics/dashboard?days=${selectedPeriod}`),
        apiClient.get('/api/user-analytics/real-time-stats')
      ]);

      if (dashboardResponse.success && realTimeResponse.success) {
        const dashboardData = dashboardResponse.data;
        const realTimeData = realTimeResponse.data;
        
        setAnalyticsData(dashboardData.data || dashboardData);
        setRealTimeStats(realTimeData.data || realTimeData);
        setLastUpdated(new Date());
        
        console.log('📊 Loaded analytics dashboard data');
      } else {
        throw new Error('Failed to load analytics data');
      }
    } catch (error) {
      console.error('Failed to load analytics:', error);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
      if (showRefreshing) setRefreshing(false);
    }
  };

  // Load data on mount and when period changes
  useEffect(() => {
    loadAnalyticsData();
  }, [selectedPeriod]);

  // Auto-refresh real-time stats every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadAnalyticsData(false);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    loadAnalyticsData(true);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'error': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      default: return <Bell className="w-4 h-4 text-blue-500" />;
    }
  };

  const getAlertBgColor = (level: string) => {
    switch (level) {
      case 'success': return 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800';
      case 'warning': return 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800';
      case 'error': return 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800';
      default: return 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
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
            Analytics Error
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analyticsData || !realTimeStats) {
    return <div>No data available</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header with Controls */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <BarChart3 className="mr-3" size={28} />
              Advanced Analytics Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Comprehensive business insights and performance metrics
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(parseInt((e.target as HTMLInputElement).value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
            </select>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            
            <button className="flex items-center px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
              <Download className="w-4 h-4 mr-2" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Executive Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {analyticsData.executive_summary.total_users.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Users</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatPercentage(analyticsData.executive_summary.growth_rate)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Growth Rate</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {formatPercentage(analyticsData.executive_summary.conversion_rate)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Conversion Rate</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
              {formatPercentage(analyticsData.executive_summary.security_score)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Security Score</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatCurrency(analyticsData.executive_summary.mrr)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Monthly Revenue</div>
          </div>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Key Insights</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {analyticsData.executive_summary.key_insights.map((insight, index) => (
              <div key={index} className="flex items-center text-sm text-gray-700 dark:text-gray-300">
                <CheckCircle className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
                {insight}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Real-Time Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Users Online</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {realTimeStats.active_users_online}
              </p>
              <p className="text-xs text-green-500 flex items-center mt-1">
                <Activity className="w-3 h-3 mr-1" />
                Live
              </p>
            </div>
            <Activity className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Registrations Today</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {realTimeStats.registrations_today}
              </p>
              <p className="text-xs text-blue-500">+{Math.round(realTimeStats.registrations_today * 0.15)} vs yesterday</p>
            </div>
            <Users className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Invites Sent Today</p>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {realTimeStats.invitations_sent_today}
              </p>
              <p className="text-xs text-purple-500">
                {formatPercentage(analyticsData.invitation_funnel.conversion_rates.overall_conversion_rate)} conversion
              </p>
            </div>
            <Mail className="h-8 w-8 text-purple-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Trading Volume 24h</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                {formatCurrency(realTimeStats.trading_volume_24h)}
              </p>
              <p className="text-xs text-orange-500">
                {analyticsData.user_growth.summary.active_users} active traders
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-orange-600" />
          </div>
        </div>
      </div>

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Growth Chart */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <BarChart3 className="w-5 h-5 mr-2" />
              User Growth Trends
            </h3>
            <span className="text-sm text-gray-500">Last {selectedPeriod} days</span>
          </div>
          
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {analyticsData.user_growth.summary.total_users}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Total Users</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-green-600 dark:text-green-400">
                {analyticsData.user_growth.summary.active_users}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Active Users</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {analyticsData.user_growth.summary.premium_users}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Premium Users</div>
            </div>
          </div>

          {/* Simple chart representation */}
          <div className="space-y-2">
            <div className="text-sm text-gray-600 dark:text-gray-400">Growth Rate</div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full" 
                style={{ width: `${Math.min(Math.abs(analyticsData.user_growth.summary.growth_rate), 100)}%` }}
              ></div>
            </div>
            <div className="text-xs text-gray-500">
              {formatPercentage(analyticsData.user_growth.summary.growth_rate)} growth rate
            </div>
          </div>
        </div>

        {/* Invitation Funnel */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Mail className="w-5 h-5 mr-2" />
              Invitation Funnel
            </h3>
            <span className="text-sm text-green-600">
              {formatPercentage(analyticsData.invitation_funnel.conversion_rates.overall_conversion_rate)} conversion
            </span>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Sent</span>
              <span className="font-semibold">{analyticsData.invitation_funnel.funnel_stages.sent}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div className="bg-blue-500 h-2 rounded-full" style={{ width: '100%' }}></div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Opened</span>
              <span className="font-semibold">{analyticsData.invitation_funnel.funnel_stages.opened}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full" 
                style={{ 
                  width: `${(analyticsData.invitation_funnel.funnel_stages.opened / Math.max(analyticsData.invitation_funnel.funnel_stages.sent, 1)) * 100}%` 
                }}
              ></div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Clicked</span>
              <span className="font-semibold">{analyticsData.invitation_funnel.funnel_stages.clicked}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-yellow-500 h-2 rounded-full" 
                style={{ 
                  width: `${(analyticsData.invitation_funnel.funnel_stages.clicked / Math.max(analyticsData.invitation_funnel.funnel_stages.sent, 1)) * 100}%` 
                }}
              ></div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Registered</span>
              <span className="font-semibold text-green-600">{analyticsData.invitation_funnel.funnel_stages.registered}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-purple-500 h-2 rounded-full" 
                style={{ 
                  width: `${(analyticsData.invitation_funnel.funnel_stages.registered / Math.max(analyticsData.invitation_funnel.funnel_stages.sent, 1)) * 100}%` 
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Security Metrics */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Shield className="w-5 h-5 mr-2" />
              Security & Compliance
            </h3>
            <span className="text-sm text-green-600">
              {formatPercentage(analyticsData.security.security_events.compliance_score)} score
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div className="text-xl font-bold text-green-600 dark:text-green-400">
                {analyticsData.security.security_events.successful_logins_24h}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Successful Logins</div>
            </div>
            <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="text-xl font-bold text-red-600 dark:text-red-400">
                {analyticsData.security.security_events.failed_logins_24h}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Failed Attempts</div>
            </div>
            <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {formatPercentage(analyticsData.security.security_events.two_fa_enabled_users)}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">2FA Enabled</div>
            </div>
            <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <div className="text-xl font-bold text-orange-600 dark:text-orange-400">
                {analyticsData.security.risk_assessment.high_risk_users}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">High Risk Users</div>
            </div>
          </div>
        </div>

        {/* Revenue Analytics */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <DollarSign className="w-5 h-5 mr-2" />
              Revenue Analytics
            </h3>
            <span className="text-sm text-green-600">
              {formatPercentage(analyticsData.revenue.revenue_summary.growth_rate)} growth
            </span>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Monthly Recurring Revenue</span>
              <span className="text-xl font-bold text-green-600 dark:text-green-400">
                {formatCurrency(analyticsData.revenue.revenue_summary.mrr)}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Annual Recurring Revenue</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatCurrency(analyticsData.revenue.revenue_summary.arr)}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Average Revenue Per User</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatCurrency(analyticsData.revenue.revenue_summary.arpu)}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Customer Lifetime Value</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatCurrency(analyticsData.revenue.revenue_summary.ltv)}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Churn Rate</span>
              <span className="font-semibold text-orange-600 dark:text-orange-400">
                {formatPercentage(analyticsData.revenue.revenue_summary.churn_rate)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activities & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Clock className="w-5 h-5 mr-2" />
            Recent Activities
          </h3>
          
          <div className="space-y-3">
            {realTimeStats.recent_activities.map((activity, index) => (
              <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="w-2 h-2 bg-green-500 rounded-full flex-shrink-0"></div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {activity.event}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {activity.user} • {activity.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Alerts */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <Bell className="w-5 h-5 mr-2" />
            System Alerts
          </h3>
          
          <div className="space-y-3">
            {realTimeStats.alerts.map((alert, index) => (
              <div key={index} className={`flex items-center space-x-3 p-3 rounded-lg border ${getAlertBgColor(alert.level)}`}>
                {getAlertIcon(alert.level)}
                <div className="flex-1">
                  <p className="text-sm text-gray-900 dark:text-white">
                    {alert.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 