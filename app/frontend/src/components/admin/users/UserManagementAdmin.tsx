import { useState } from 'preact/hooks';
import { 
  Users, 
  Filter, 
  MoreVertical, 
  Edit, 
  Ban, 
  CheckCircle, 
  XCircle,
  TrendingUp,
  DollarSign,
  UserPlus,
  Download,
  Mail,
  Shield,
  Activity,
  UserCheck,
  UserX,
  Key,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Send,
  Copy,
  Plus,
  Trash2,
  Settings
} from 'lucide-preact';
import { useAdminData, useAdminUserActions } from '../../../hooks/admin-hooks';
import AnalyticsAdmin from '../../shared/analytics/AnalyticsAdmin';

// Define the filters type here since it's no longer imported
interface UserManagementFilters {
  role?: string;
  status?: string;
  subscription_type?: string;
  kyc_status?: string;
  search?: string;
}

type FilterValue = string | undefined;
type UserActionArg = string | undefined;

interface Invitation {
  id: string;
  email: string;
  role: string;
  status: 'sent' | 'opened' | 'clicked' | 'registered' | 'expired' | 'cancelled';
  invited_by: string;
  created_at: string;
  sent_at: string;
  expires_at: string;
  custom_message?: string;
  tracking_data: {
    sent_count: number;
    last_sent: string;
    opened_at?: string;
    clicked_at?: string;
  };
}

export default function UserManagementAdmin() {
  // Existing state
  const [filters, setFilters] = useState<UserManagementFilters>({
    role: undefined,
    status: undefined,
    subscription_type: undefined,
    kyc_status: undefined,
    search: '',
    sort_by: 'created_at',
    sort_order: 'desc',
    page: 1,
    limit: 20
  });

  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // NEW: Tab management state
  const [activeTab, setActiveTab] = useState<'users' | 'invitations' | 'analytics'>('users');

  // NEW: Invitation management state
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [invitationFilters, setInvitationFilters] = useState({
    status: '',
    invited_by: '',
    page: 1,
    limit: 20
  });
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    email: '',
    emails: [] as string[],
    role: 'user',
    custom_message: '',
    expires_in_days: 7,
    bulk_mode: false
  });
  const [inviteLoading, setInviteLoading] = useState(false);
  const [selectedInvitations, setSelectedInvitations] = useState<string[]>([]);

  // REAL API: Construct URL with query parameters from filters
  const buildUserDataUrl = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.append(key, String(value));
      }
    });
    return `/api/admin/users?${params.toString()}`;
  };

  const { data: userData, loading, error, refresh } = useAdminData(buildUserDataUrl());
  const { updateUserStatus, updateUserRole, resetUserPassword, loading: actionLoadingState, error: actionError } = useAdminUserActions();

  // REAL API: Load invitations from professional backend
  const loadInvitations = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const params = new URLSearchParams();
      Object.entries(invitationFilters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') {
          params.append(key, String(value));
        }
      });

      // REAL API: Call actual invitation endpoint
      const response = await fetch(`/api/admin/invitations?${  params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setInvitations(data.invitations || []);
        console.log('📧 Loaded real invitations:', data.invitations?.length || 0);
      } else {
        console.error('Failed to load invitations:', response.status);
        setInvitations([]);
      }
    } catch (error) {
      console.error('Failed to load invitations:', error);
      setInvitations([]);
    }
  };

  // Load invitations when tab changes or filters change
  useEffect(() => {
    if (activeTab === 'invitations') {
      loadInvitations();
    }
  }, [activeTab, invitationFilters]);

  const handleFilterChange = (key: keyof UserManagementFilters, value: FilterValue) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1 // Reset to first page when filters change
    }));
  };

  const handlePageChange = (newPage: number) => {
    setFilters(prev => ({ ...prev, page: newPage }));
  };

  const handleUserAction = async (userId: string, action: string, ...args: UserActionArg[]) => {
    try {
      setActionLoading(userId);
      
      switch (action) {
        case 'suspend':
          await updateUserStatus(userId, 'suspended', 'Suspended by admin');
          break;
        case 'activate':
          await updateUserStatus(userId, 'active');
          break;
        case 'ban':
          await updateUserStatus(userId, 'banned', args[0] || 'Banned by admin');
          break;
        case 'promote':
          await updateUserRole(userId, args[0] || 'premium');
          break;
        case 'reset_password':
          await resetUserPassword(userId);
          break;
      }
      
      // Refresh data after action
      refresh();
      
    } catch (error) {
      console.error(`Failed to perform action ${action}:`, error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleBulkAction = async (action: string) => {
    if (selectedUsers.length === 0) return;
    
    for (const userId of selectedUsers) {
      await handleUserAction(userId, action);
    }
    
    setSelectedUsers([]);
  };

  // NEW: Invitation actions
  const handleSendInvitation = async () => {
    try {
      setInviteLoading(true);

      if (inviteForm.bulk_mode && inviteForm.emails.length > 0) {
        // Send bulk invitations
        const response = await fetch('/api/user-management/invitations/bulk', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            emails: inviteForm.emails,
            role: inviteForm.role,
            custom_message: inviteForm.custom_message,
            expires_in_days: inviteForm.expires_in_days
          })
        });

        if (response.ok) {
          const data = await response.json();
          console.log('✅ Sent bulk invitations:', data.data.summary);
          setShowInviteModal(false);
          setInviteForm({
            email: '',
            emails: [],
            role: 'user',
            custom_message: '',
            expires_in_days: 7,
            bulk_mode: false
          });
          loadInvitations();
        }
      } else if (!inviteForm.bulk_mode && inviteForm.email) {
        // Send single invitation
        const response = await fetch('/api/user-management/invitations', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: inviteForm.email,
            role: inviteForm.role,
            custom_message: inviteForm.custom_message,
            expires_in_days: inviteForm.expires_in_days
          })
        });

        if (response.ok) {
          const data = await response.json();
          console.log('✅ Sent invitation:', data.data);
          setShowInviteModal(false);
          setInviteForm({
            email: '',
            emails: [],
            role: 'user',
            custom_message: '',
            expires_in_days: 7,
            bulk_mode: false
          });
          loadInvitations();
        }
      }
    } catch (error) {
      console.error('Failed to send invitation:', error);
    } finally {
      setInviteLoading(false);
    }
  };

  const handleResendInvitation = async (invitationId: string) => {
    try {
      const response = await fetch(`/api/user-management/invitations/${invitationId}/resend`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        console.log('✅ Resent invitation:', invitationId);
        loadInvitations();
      }
    } catch (error) {
      console.error('Failed to resend invitation:', error);
    }
  };

  const handleCancelInvitation = async (invitationId: string) => {
    try {
      const response = await fetch(`/api/user-management/invitations/${invitationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        console.log('❌ Cancelled invitation:', invitationId);
        loadInvitations();
      }
    } catch (error) {
      console.error('Failed to cancel invitation:', error);
    }
  };

  const addEmailToBulkList = () => {
    if (inviteForm.email && !inviteForm.emails.includes(inviteForm.email)) {
      setInviteForm(prev => ({
        ...prev,
        emails: [...prev.emails, prev.email],
        email: ''
      }));
    }
  };

  const removeEmailFromBulkList = (emailToRemove: string) => {
    setInviteForm(prev => ({
      ...prev,
      emails: prev.emails.filter(email => email !== emailToRemove)
    }));
  };

  const getInvitationStatusBadge = (status: string) => {
    const badges = {
      sent: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      opened: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      clicked: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      registered: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      expired: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[status] || badges.sent}`}>
        {status}
      </span>
    );
  };

  const getUserStatusBadge = (status: string) => {
    const badges = {
      active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      suspended: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      banned: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[status] || badges.pending}`}>
        {status}
      </span>
    );
  };

  const getRoleBadge = (role: string) => {
    const badges = {
      admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      premium: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      user: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[role] || badges.user}`}>
        {role}
      </span>
    );
  };

  const getSubscriptionBadge = (type: string) => {
    const badges = {
      enterprise: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      premium: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      basic: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      free: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badges[type] || badges.free}`}>
        {type}
      </span>
    );
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

  const exportToCSV = () => {
    if (!userData?.users || !Array.isArray(userData.users)) return;
    
    const csvContent = [
      ['ID', 'Username', 'Email', 'Role', 'Status', 'Portfolio Value', 'Total Trades', 'P&L', 'Created', 'Last Login'],
      ...userData.users.map(user => [
        user.id,
        user.username,
        user.email,
        user.role,
        user.status,
        user.portfolio_value.toString(),
        user.total_trades.toString(),
        user.total_profit_loss.toString(),
        user.created_at,
        user.last_login
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `users-export-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading && !userData) {
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
            User Management Error
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
      {/* Header with Tab Navigation */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <Users className="mr-3" size={28} />
              Enterprise User Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Comprehensive user lifecycle management with invitation system
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
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
              <Activity size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('users')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              User Directory
            </button>
            <button
              onClick={() => setActiveTab('invitations')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'invitations'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Mail className="w-4 h-4 inline mr-2" />
              Invitation Center
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'analytics'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <TrendingUp className="w-4 h-4 inline mr-2" />
              Analytics
            </button>
          </nav>
        </div>

        {/* Summary Stats */}
        {userData?.summary && activeTab === 'users' && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Users</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {userData.summary.total_users}
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="text-sm text-green-600 dark:text-green-400">Active Users</div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {userData.summary.active_users}
              </div>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="text-sm text-blue-600 dark:text-blue-400">Premium Users</div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {userData.summary.premium_users}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <div className="text-sm text-purple-600 dark:text-purple-400">Total Portfolio</div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {formatCurrency(userData.summary.total_portfolio_value)}
              </div>
            </div>
            <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
              <div className="text-sm text-orange-600 dark:text-orange-400">Avg P&L</div>
              <div className={`text-2xl font-bold ${
                userData.summary.avg_profit_loss >= 0 
                  ? 'text-green-600 dark:text-green-400' 
                  : 'text-red-600 dark:text-red-400'
              }`}>
                {formatCurrency(userData.summary.avg_profit_loss)}
              </div>
            </div>
          </div>
        )}

        {/* Content based on active tab */}
        {activeTab === 'users' && (
          <>
            {/* Filters Panel */}
            {showFilters && (
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Search
                    </label>
                    <input
                      type="text"
                      value={filters.search || ''}
                      onChange={(e) => handleFilterChange('search', (e.target as HTMLInputElement).value)}
                      placeholder="Username, email..."
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Role
                    </label>
                    <select
                      value={filters.role || 'all'}
                      onChange={(e) => handleFilterChange('role', (e.target as HTMLInputElement).value === 'all' ? undefined : (e.target as HTMLInputElement).value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="all">All Roles</option>
                      <option value="admin">Admin</option>
                      <option value="premium">Premium</option>
                      <option value="user">User</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Status
                    </label>
                    <select
                      value={filters.status || 'all'}
                      onChange={(e) => handleFilterChange('status', (e.target as HTMLInputElement).value === 'all' ? undefined : (e.target as HTMLInputElement).value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="all">All Status</option>
                      <option value="active">Active</option>
                      <option value="suspended">Suspended</option>
                      <option value="pending">Pending</option>
                      <option value="banned">Banned</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Subscription
                    </label>
                    <select
                      value={filters.subscription_type || 'all'}
                      onChange={(e) => handleFilterChange('subscription_type', (e.target as HTMLInputElement).value === 'all' ? undefined : (e.target as HTMLInputElement).value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="all">All Plans</option>
                      <option value="enterprise">Enterprise</option>
                      <option value="premium">Premium</option>
                      <option value="basic">Basic</option>
                      <option value="free">Free</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Sort By
                    </label>
                    <select
                      value={filters.sort_by || 'created_at'}
                      onChange={(e) => handleFilterChange('sort_by', (e.target as HTMLInputElement).value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="created_at">Registration Date</option>
                      <option value="last_login">Last Login</option>
                      <option value="portfolio_value">Portfolio Value</option>
                      <option value="total_trades">Total Trades</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Order
                    </label>
                    <select
                      value={filters.sort_order || 'desc'}
                      onChange={(e) => handleFilterChange('sort_order', (e.target as HTMLInputElement).value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="desc">Descending</option>
                      <option value="asc">Ascending</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Bulk Actions */}
            {selectedUsers.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-6">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {selectedUsers.length} user(s) selected
                  </span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleBulkAction('activate')}
                      className="px-3 py-1 text-sm bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/40 transition-colors"
                    >
                      Activate
                    </button>
                    <button
                      onClick={() => handleBulkAction('suspend')}
                      className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded-lg hover:bg-yellow-200 dark:hover:bg-yellow-900/40 transition-colors"
                    >
                      Suspend
                    </button>
                    <button
                      onClick={() => setSelectedUsers([])}
                      className="px-3 py-1 text-sm bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'invitations' && (
          <div className="mt-6">
            {/* Invitation Header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Invitation Center
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Send and manage user invitations with role pre-assignment
                </p>
              </div>
              <button
                onClick={() => setShowInviteModal(true)}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Send Invitation
              </button>
            </div>

            {/* Invitation Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div className="text-sm text-blue-600 dark:text-blue-400">Total Sent</div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {invitations.length}
                </div>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <div className="text-sm text-green-600 dark:text-green-400">Registered</div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {invitations.filter(i => i.status === 'registered').length}
                </div>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                <div className="text-sm text-yellow-600 dark:text-yellow-400">Pending</div>
                <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {invitations.filter(i => ['sent', 'opened', 'clicked'].includes(i.status)).length}
                </div>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <div className="text-sm text-red-600 dark:text-red-400">Expired</div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {invitations.filter(i => i.status === 'expired').length}
                </div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <div className="text-sm text-purple-600 dark:text-purple-400">Conversion Rate</div>
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {invitations.length > 0 
                    ? ((invitations.filter(i => i.status === 'registered').length / invitations.length) * 100).toFixed(1)
                    : 0
                  }%
                </div>
              </div>
            </div>

            {/* Invitation Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Status Filter
                </label>
                <select
                  value={invitationFilters.status}
                  onChange={(e) => setInvitationFilters(prev => ({ ...prev, status: (e.target as HTMLInputElement).value, page: 1 }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="">All Status</option>
                  <option value="sent">Sent</option>
                  <option value="opened">Opened</option>
                  <option value="clicked">Clicked</option>
                  <option value="registered">Registered</option>
                  <option value="expired">Expired</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Invited By
                </label>
                <select
                  value={invitationFilters.invited_by}
                  onChange={(e) => setInvitationFilters(prev => ({ ...prev, invited_by: (e.target as HTMLInputElement).value, page: 1 }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="">All Admins</option>
                  <option value="enterprise_admin">Enterprise Admin</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={loadInvitations}
                  className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors flex items-center justify-center"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Content Sections */}
      {activeTab === 'users' && (
        /* Users Table - Keep existing user table implementation here */
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Users className="w-5 h-5 mr-2" />
              User Directory ({userData?.users?.length || 0})
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    <input
                      type="checkbox"
                      checked={selectedUsers.length === (userData?.users?.length || 0)}
                      onChange={(e) => {
                        if ((e.target as HTMLInputElement).checked) {
                          setSelectedUsers(userData?.users?.map(u => u.id) || []);
                        } else {
                          setSelectedUsers([]);
                        }
                      }}
                      className="rounded border-gray-300 dark:border-gray-600"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Role & Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Portfolio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Trading Stats
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Last Activity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {Array.isArray(userData?.users) && userData.users.length > 0 ? (
                  userData.users.map((user) => (
                  <>
                    <tr key={`${user.id}-main`} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={selectedUsers.includes(user.id)}
                        onChange={(e) => {
                          if ((e.target as HTMLInputElement).checked) {
                            setSelectedUsers([...selectedUsers, user.id]);
                          } else {
                            setSelectedUsers(selectedUsers.filter(id => id !== user.id));
                          }
                        }}
                        className="rounded border-gray-300 dark:border-gray-600"
                      />
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-10 w-10 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                          <Users size={16} className="text-gray-600 dark:text-gray-400" />
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {user.username}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="space-y-1">
                        {getRoleBadge(user.role)}
                        {getUserStatusBadge(user.status)}
                        {getSubscriptionBadge(user.subscription_type)}
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {formatCurrency(user.portfolio_value)}
                      </div>
                      <div className={`text-sm ${
                        user.total_profit_loss >= 0 
                          ? 'text-green-600 dark:text-green-400' 
                          : 'text-red-600 dark:text-red-400'
                      }`}>
                        {user.total_profit_loss >= 0 ? '+' : ''}{formatCurrency(user.total_profit_loss)}
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {user.total_trades} trades
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Risk: {user.risk_score ? user.risk_score.toFixed(1) : 'N/A'}/10
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(user.last_login).toLocaleDateString()}
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {user.status === 'active' ? (
                          <button
                            onClick={() => handleUserAction(user.id, 'suspend')}
                            disabled={actionLoading === user.id}
                            className="p-1 text-yellow-600 hover:text-yellow-700 dark:text-yellow-400 dark:hover:text-yellow-300"
                            title="Suspend User"
                          >
                            <UserX size={16} />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUserAction(user.id, 'activate')}
                            disabled={actionLoading === user.id}
                            className="p-1 text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                            title="Activate User"
                          >
                            <UserCheck size={16} />
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleUserAction(user.id, 'reset_password')}
                          disabled={actionLoading === user.id}
                          className="p-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                          title="Reset Password"
                        >
                          <Key size={16} />
                        </button>
                        
                        <button
                          onClick={() => setSelectedUser(selectedUser === user.id ? null : user.id)}
                          className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                          title="View Details"
                        >
                          <Eye size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  
                  {/* Expanded User Details */}
                  {selectedUser === user.id && (
                    <tr key={`${user.id}-expanded`}>
                      <td colSpan={7} className="px-6 py-4 bg-gray-50 dark:bg-gray-800">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                              Account Details
                            </h4>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">User ID:</span>
                                <span className="font-mono text-xs">{user.id}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Created:</span>
                                <span>{new Date(user.created_at).toLocaleDateString()}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Email Verified:</span>
                                <span className={user.verified_email ? 'text-green-600' : 'text-red-600'}>
                                  {user.verified_email ? 'Yes' : 'No'}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">KYC Status:</span>
                                <span className={
                                  user.kyc_status === 'approved' ? 'text-green-600' :
                                  user.kyc_status === 'rejected' ? 'text-red-600' : 'text-yellow-600'
                                }>
                                  {user.kyc_status}
                                </span>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                              Trading Permissions
                            </h4>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Virtual Trading:</span>
                                <span className={user.trading_permissions.virtual_trading ? 'text-green-600' : 'text-red-600'}>
                                  {user.trading_permissions.virtual_trading ? 'Enabled' : 'Disabled'}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Live Trading:</span>
                                <span className={user.trading_permissions.live_trading ? 'text-green-600' : 'text-red-600'}>
                                  {user.trading_permissions.live_trading ? 'Enabled' : 'Disabled'}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">API Access:</span>
                                <span className={user.trading_permissions.api_access ? 'text-green-600' : 'text-red-600'}>
                                  {user.trading_permissions.api_access ? 'Enabled' : 'Disabled'}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Max Position:</span>
                                <span>{formatCurrency(user.trading_permissions.max_position_size)}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                              Subscription
                            </h4>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Plan:</span>
                                <span>{user.subscription_type}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600 dark:text-gray-400">Expires:</span>
                                <span>
                                  {user.subscription_expires 
                                    ? new Date(user.subscription_expires).toLocaleDateString()
                                    : 'Never'
                                  }
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                  </>
                ))
                ) : (
                  <tr>
                    <td colSpan={10} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                      {userData?.users ? 'No users found' : 'Loading users...'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {userData && userData.total > userData.limit && (
            <div className="bg-white dark:bg-gray-900 px-6 py-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  Showing {((userData.page - 1) * userData.limit) + 1} to{' '}
                  {Math.min(userData.page * userData.limit, userData.total)} of{' '}
                  {userData.total} results
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePageChange(userData.page - 1)}
                    disabled={userData.page <= 1}
                    className="px-3 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Page {userData.page}
                  </span>
                  
                  <button
                    onClick={() => handlePageChange(userData.page + 1)}
                    disabled={!userData.has_next}
                    className="px-3 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'invitations' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Mail className="w-5 h-5 mr-2" />
              Invitation Management ({invitations.length})
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Sent
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Expires
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tracking
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {invitations.length > 0 ? (
                  invitations.map((invitation) => (
                    <tr key={invitation.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {invitation.email}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          ID: {invitation.id}
                        </div>
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getRoleBadge(invitation.role)}
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getInvitationStatusBadge(invitation.status)}
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(invitation.sent_at).toLocaleDateString()}
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(invitation.expires_at).toLocaleDateString()}
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-xs space-y-1">
                          <div>Sent: {invitation.tracking_data.sent_count}x</div>
                          {invitation.tracking_data.opened_at && (
                            <div className="text-green-600">Opened ✓</div>
                          )}
                          {invitation.tracking_data.clicked_at && (
                            <div className="text-blue-600">Clicked ✓</div>
                          )}
                        </div>
                      </td>
                      
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {invitation.status === 'sent' && (
                            <>
                              <button
                                onClick={() => handleResendInvitation(invitation.id)}
                                className="p-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                                title="Resend Invitation"
                              >
                                <Send size={16} />
                              </button>
                              <button
                                onClick={() => handleCancelInvitation(invitation.id)}
                                className="p-1 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                                title="Cancel Invitation"
                              >
                                <Trash2 size={16} />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`https://tradepulse.ai/register?token=${invitation.id}`)
                            }}
                            className="p-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                            title="Copy Invitation Link"
                          >
                            <Copy size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                      No invitations found. Send your first invitation to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'analytics' && (
        <AnalyticsAdmin />
      )}

      {/* Invitation Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Send User Invitation
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <XCircle size={24} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Mode Toggle */}
              <div className="flex space-x-2">
                <button
                  onClick={() => setInviteForm(prev => ({ ...prev, bulk_mode: false }))}
                  className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                    !inviteForm.bulk_mode
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                  }`}
                >
                  Single Invite
                </button>
                <button
                  onClick={() => setInviteForm(prev => ({ ...prev, bulk_mode: true }))}
                  className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                    inviteForm.bulk_mode
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                  }`}
                >
                  Bulk Invite
                </button>
              </div>

              {/* Email Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email Address
                </label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    value={inviteForm.email}
                    onChange={(e) => setInviteForm(prev => ({ ...prev, email: (e.target as HTMLInputElement).value }))}
                    placeholder="user@company.com"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                  {inviteForm.bulk_mode && (
                    <button
                      onClick={addEmailToBulkList}
                      className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <Plus size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Bulk Email List */}
              {inviteForm.bulk_mode && inviteForm.emails.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email List ({inviteForm.emails.length})
                  </label>
                  <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-2 max-h-32 overflow-y-auto">
                    {inviteForm.emails.map((email, index) => (
                      <div key={index} className="flex items-center justify-between py-1">
                        <span className="text-sm text-gray-700 dark:text-gray-300">{email}</span>
                        <button
                          onClick={() => removeEmailFromBulkList(email)}
                          className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                        >
                          <XCircle size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Role Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  User Role
                </label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm(prev => ({ ...prev, role: (e.target as HTMLInputElement).value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value="user">User (Basic access)</option>
                  <option value="premium">Premium (Live trading)</option>
                  <option value="admin">Admin (Full access)</option>
                </select>
              </div>

              {/* Custom Message */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Custom Message (Optional)
                </label>
                <textarea
                  value={inviteForm.custom_message}
                  onChange={(e) => setInviteForm(prev => ({ ...prev, custom_message: (e.target as HTMLInputElement).value }))}
                  placeholder="Add a personal welcome message..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>

              {/* Expiry */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Expires In
                </label>
                <select
                  value={inviteForm.expires_in_days}
                  onChange={(e) => setInviteForm(prev => ({ ...prev, expires_in_days: parseInt((e.target as HTMLInputElement).value) }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  <option value={7}>7 days</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                </select>
              </div>

              {/* Actions */}
              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSendInvitation}
                  disabled={inviteLoading || (!inviteForm.email && inviteForm.emails.length === 0)}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                >
                  {inviteLoading ? (
                    <Activity className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Send {inviteForm.bulk_mode ? `${inviteForm.emails.length} ` : ''}Invitation{inviteForm.bulk_mode && inviteForm.emails.length !== 1 ? 's' : ''}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 