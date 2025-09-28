/*
📞 Communication Center Dashboard
Enterprise messaging, announcements, and notification management interface
*/

import { useState } from 'preact/hooks';
import { 
  MessageSquare, Send, Users, Bell, Settings, Edit, Trash2,
  Plus, Filter, Search, Clock, CheckCircle, AlertTriangle,
  Mail, Smartphone, Monitor, TrendingUp, BarChart3,
  FileText, Download, RefreshCw, Star, Flag
} from 'lucide-preact';

interface Message {
  id: string;
  type: 'direct_message' | 'announcement' | 'system_alert' | 'marketing';
  priority: 'low' | 'normal' | 'high' | 'urgent' | 'critical';
  subject: string;
  content: string;
  sender_id: string;
  recipients_count: number;
  delivery_stats: {
    delivered: number;
    read: number;
    failed: number;
  };
  created_at: string;
  status: string;
}

interface Announcement {
  id: string;
  title: string;
  content: string;
  category: string;
  priority: string;
  status: string;
  target_audience: {
    all_users: boolean;
    total_recipients: number;
  };
  stats: {
    views: number;
    acknowledgments: number;
    dismissals: number;
  };
  created_at: string;
  published_at?: string;
}

interface CommunicationAnalytics {
  summary: {
    total_messages_sent: number;
    total_announcements: number;
    avg_delivery_rate: number;
    avg_read_rate: number;
    active_subscribers: number;
  };
  delivery_performance: {
    [key: string]: {
      sent: number;
      delivered: number;
      read: number;
      rate: number;
    };
  };
}

export default function CommunicationCenter() {
  const [activeTab, setActiveTab] = useState<'messages' | 'announcements' | 'analytics' | 'templates'>('messages');
  const [messages, setMessages] = useState<Message[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [analytics, setAnalytics] = useState<CommunicationAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Message composition
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [messageForm, setMessageForm] = useState({
    type: 'direct_message',
    priority: 'normal',
    subject: '',
    content: '',
    recipients: [] as string[],
    target_roles: [] as string[],
    channels: ['in_app']
  });
  
  const [announcementForm, setAnnouncementForm] = useState({
    title: '',
    content: '',
    category: 'general',
    priority: 'normal',
    target_all_users: true,
    target_roles: [] as string[],
    channels: ['in_app'],
    show_popup: false,
    pin_to_top: false,
    require_acknowledgment: false
  });

  // Load data
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get auth token
      // Use enterprise_admin_token for development like other components
      const token = 'enterprise_admin_token';

      const [messagesResponse, announcementsResponse, analyticsResponse] = await Promise.all([
        fetch('/api/admin/communications/messages/sent', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }),
        fetch('/api/admin/communications/announcements', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }),
        fetch('/api/admin/communications/analytics/overview', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
      ]);

      if (messagesResponse.ok && announcementsResponse.ok && analyticsResponse.ok) {
        const messagesData = await messagesResponse.json();
        const announcementsData = await announcementsResponse.json();
        const analyticsData = await analyticsResponse.json();
        
        setMessages(messagesData.messages || messagesData.data?.messages || []);
        setAnnouncements(announcementsData.announcements || announcementsData.data?.announcements || []);
        setAnalytics(analyticsData.analytics || analyticsData.data || analyticsData);
        
        console.log('📞 Loaded communication center data');
      } else {
        throw new Error('Failed to load communication data');
      }
    } catch (error) {
      console.error('Failed to load communication data:', error);
      setError('Failed to load communication data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSendMessage = async () => {
    try {
      const response = await fetch('/api/communication/messages/send', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(messageForm)
      });

      if (response.ok) {
        setShowMessageModal(false);
        setMessageForm({
          type: 'direct_message',
          priority: 'normal',
          subject: '',
          content: '',
          recipients: [],
          target_roles: [],
          channels: ['in_app']
        });
        loadData();
        console.log('✅ Message sent successfully');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleCreateAnnouncement = async () => {
    try {
      const response = await fetch('/api/communication/announcements', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(announcementForm)
      });

      if (response.ok) {
        setShowAnnouncementModal(false);
        setAnnouncementForm({
          title: '',
          content: '',
          category: 'general',
          priority: 'normal',
          target_all_users: true,
          target_roles: [],
          channels: ['in_app'],
          show_popup: false,
          pin_to_top: false,
          require_acknowledgment: false
        });
        loadData();
        console.log('✅ Announcement created successfully');
      }
    } catch (error) {
      console.error('Failed to create announcement:', error);
    }
  };

  const getPriorityBadge = (priority: string) => {
    const badges = {
      low: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
      normal: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
      urgent: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      critical: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-300'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[priority] || badges.normal}`}>
        {priority}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      sent: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      scheduled: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      draft: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
      published: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[status] || badges.draft}`}>
        {status}
      </span>
    );
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
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
            Communication Center Error
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={loadData}
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
      {/* Header */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <MessageSquare className="mr-3" size={28} />
              Communication Center
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Enterprise messaging, announcements, and notification management
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowMessageModal(true)}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Send className="w-4 h-4 mr-2" />
              Send Message
            </button>
            
            <button
              onClick={() => setShowAnnouncementModal(true)}
              className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <Bell className="w-4 h-4 mr-2" />
              Create Announcement
            </button>
            
            <button
              onClick={loadData}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700 mt-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('messages')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'messages'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-2" />
              Messages ({messages.length})
            </button>
            <button
              onClick={() => setActiveTab('announcements')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'announcements'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Bell className="w-4 h-4 inline mr-2" />
              Announcements ({announcements.length})
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'analytics'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              Analytics
            </button>
            <button
              onClick={() => setActiveTab('templates')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'templates'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />
              Templates
            </button>
          </nav>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'messages' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <MessageSquare className="w-5 h-5 mr-2" />
              Sent Messages
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Message
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type & Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Recipients
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Delivery Stats
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Sent
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {messages.map((message) => (
                  <tr key={message.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {message.subject}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                          {message.content}
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <span className="inline-block px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                          {message.type}
                        </span>
                        {getPriorityBadge(message.priority)}
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {message.recipients_count} recipients
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Delivered:</span>
                          <span className="text-green-600 dark:text-green-400">{message.delivery_stats?.delivered || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Read:</span>
                          <span className="text-blue-600 dark:text-blue-400">{message.delivery_stats?.read || 0}</span>
                        </div>
                        {(message.delivery_stats?.failed || 0) > 0 && (
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Failed:</span>
                            <span className="text-red-600 dark:text-red-400">{message.delivery_stats?.failed || 0}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {formatDateTime(message.created_at)}
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <button className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <Eye size={16} />
                        </button>
                        <button className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <BarChart3 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'announcements' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Bell className="w-5 h-5 mr-2" />
              System Announcements
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Announcement
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Audience
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Engagement
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {announcements.map((announcement) => (
                  <tr key={announcement.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {announcement.title}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                          {announcement.content}
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <span className="inline-block px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400">
                          {announcement.category}
                        </span>
                        {getPriorityBadge(announcement.priority)}
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        <div className="font-medium text-gray-900 dark:text-white">
                          {announcement.target_audience.all_users ? 'All Users' : 'Targeted'}
                        </div>
                        <div className="text-gray-500 dark:text-gray-400">
                          {announcement.target_audience.total_recipients} recipients
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Views:</span>
                          <span>{announcement.stats.views}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Acknowledged:</span>
                          <span>{announcement.stats.acknowledgments}</span>
                        </div>
                        <div className="text-xs text-gray-500">
                          {((announcement.stats.views / announcement.target_audience.total_recipients) * 100).toFixed(1)}% reach
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4">
                      {getStatusBadge(announcement.status)}
                    </td>
                    
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <button className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <Eye size={16} />
                        </button>
                        <button className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <Edit size={16} />
                        </button>
                        <button className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <BarChart3 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'analytics' && analytics && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Messages Sent</p>
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {analytics.summary.total_messages_sent}
                  </p>
                </div>
                <MessageSquare className="h-8 w-8 text-blue-600" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Announcements</p>
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {analytics.summary.total_announcements}
                  </p>
                </div>
                <Bell className="h-8 w-8 text-purple-600" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Delivery Rate</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {analytics.summary.avg_delivery_rate.toFixed(1)}%
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Read Rate</p>
                  <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                    {analytics.summary.avg_read_rate.toFixed(1)}%
                  </p>
                </div>
                <Eye className="h-8 w-8 text-orange-600" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Active Subscribers</p>
                  <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                    {analytics.summary.active_subscribers}
                  </p>
                </div>
                <Users className="h-8 w-8 text-indigo-600" />
              </div>
            </div>
          </div>

          {/* Channel Performance */}
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Channel Performance
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {Object.entries(analytics.delivery_performance).map(([channel, stats]) => (
                <div key={channel} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                      {channel.replace('_', ' ')}
                    </h4>
                    {channel === 'in_app' && <Monitor className="w-5 h-5 text-gray-500" />}
                    {channel === 'email' && <Mail className="w-5 h-5 text-gray-500" />}
                    {channel === 'sms' && <Smartphone className="w-5 h-5 text-gray-500" />}
                    {channel === 'push' && <Bell className="w-5 h-5 text-gray-500" />}
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Sent:</span>
                      <span>{stats.sent}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Delivered:</span>
                      <span className="text-green-600 dark:text-green-400">{stats?.delivered || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Read:</span>
                      <span className="text-blue-600 dark:text-blue-400">{stats?.read || 0}</span>
                    </div>
                    <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                      <div className="flex justify-between font-medium">
                        <span>Success Rate:</span>
                        <span className="text-green-600 dark:text-green-400">{(stats?.rate || 0).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'templates' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="text-center py-12">
            <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500 dark:text-gray-400 text-lg">
              Template management coming soon...
            </p>
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
              Pre-built message templates for consistent communication
            </p>
          </div>
        </div>
      )}

      {/* Message Modal */}
      {showMessageModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Send Message
              </h3>
              <button
                onClick={() => setShowMessageModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <Trash2 size={24} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Message Type
                  </label>
                  <select
                    value={messageForm.type}
                    onChange={(e) => setMessageForm(prev => ({ ...prev, type: (e.target as HTMLInputElement).value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="direct_message">Direct Message</option>
                    <option value="announcement">Announcement</option>
                    <option value="system_alert">System Alert</option>
                    <option value="marketing">Marketing</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Priority
                  </label>
                  <select
                    value={messageForm.priority}
                    onChange={(e) => setMessageForm(prev => ({ ...prev, priority: (e.target as HTMLInputElement).value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Subject
                </label>
                <input
                  type="text"
                  value={messageForm.subject}
                  onChange={(e) => setMessageForm(prev => ({ ...prev, subject: (e.target as HTMLInputElement).value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  placeholder="Message subject..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Content
                </label>
                <textarea
                  value={messageForm.content}
                  onChange={(e) => setMessageForm(prev => ({ ...prev, content: (e.target as HTMLInputElement).value }))}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  placeholder="Message content..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Delivery Channels
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {['in_app', 'email', 'sms', 'push'].map((channel) => (
                    <label key={channel} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={messageForm.channels.includes(channel)}
                        onChange={(e) => {
                          if ((e.target as HTMLInputElement).checked) {
                            setMessageForm(prev => ({ ...prev, channels: [...prev.channels, channel] }));
                          } else {
                            setMessageForm(prev => ({ ...prev, channels: prev.channels.filter(c => c !== channel) }));
                          }
                        }}
                        className="mr-2"
                      />
                      <span className="text-sm capitalize">{channel.replace('_', ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowMessageModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSendMessage}
                  disabled={!messageForm.subject || !messageForm.content}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Send Message
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 