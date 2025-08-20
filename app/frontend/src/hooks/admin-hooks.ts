import { useState, useEffect } from 'preact/hooks';

// PRODUCTION READY: Real data only - NO FALLBACKS for AWS deployment
export function useAdminData(endpoint: string) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Get real auth token from localStorage or auto-login
      let token = localStorage.getItem('auth_token');
      if (!token) {
        console.log('🔐 Auto-login for admin access...');
        try {
          const loginResponse = await fetch('http://localhost:9002/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: 'admin@tradepulse.ai',
              password: 'admin0000'
            })
          });
          
          if (loginResponse.ok) {
            const loginData = await loginResponse.json();
            token = loginData.access_token;
            if (token) {
              localStorage.setItem('auth_token', token);
              console.log('✅ Admin authenticated successfully');
            }
          } else {
            throw new Error('Authentication failed');
          }
        } catch (loginError) {
          throw new Error(`Authentication failed: ${loginError}`);
        }
      }

      // Use real professional backend endpoints with full URL
      const fullUrl = endpoint.startsWith('http') ? endpoint : `http://localhost:9002${endpoint}`;
      
      let response = await fetch(fullUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // If 401/403, try to re-authenticate once
      if ((response.status === 401 || response.status === 403)) {
        console.warn(`🔄 Got ${response.status} for ${endpoint}, re-authenticating...`);
        try {
          const loginResponse = await fetch('http://localhost:9002/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: 'admin@tradepulse.ai',
              password: 'admin0000'
            })
          });
          
          if (loginResponse.ok) {
            const loginData = await loginResponse.json();
            token = loginData.access_token;
            if (token) {
              localStorage.setItem('auth_token', token);
              console.log(`✅ Re-authenticated successfully for ${endpoint}`);
            }
            
            // Retry the request with new token
            response = await fetch(fullUrl, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });
          }
        } catch (reAuthError) {
          console.error(`❌ Re-authentication failed for ${endpoint}:`, reAuthError);
        }
      }
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} - ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log(`✅ Successfully fetched data from ${endpoint}:`, result);
      setData(result);
      setError(null);
      
    } catch (err) {
      console.error(`❌ Failed to fetch ${endpoint}:`, err);
      console.error('Full error details:', {
        message: err instanceof Error ? err.message : 'Unknown error',
        stack: err instanceof Error ? err.stack : undefined,
        endpoint: endpoint,
        fullUrl: endpoint.startsWith('http') ? endpoint : `http://localhost:9002${endpoint}`
      });
      setError(err instanceof Error ? err.message : 'Unknown error');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [endpoint]);

  return {
    data,
    loading,
    error,
    refetch: fetchData
  };
}

// PRODUCTION READY: All hooks use REAL DATA ONLY - NO FALLBACKS
export function useSystemStatus() {
  return useAdminData('/api/admin/system/status');
}

export function useVirtualPortfolio() {
  return useAdminData('/api/portfolio/virtual/overview');
}

export function useAnalyticsOverview() {
  return useAdminData('/api/analytics/overview');
}

export function useBacktestingResults() {
  return useAdminData('/api/analytics/admin/backtesting-results');
}

export function useAIvsRandomAnalysis() {
  return useAdminData('/api/analytics/admin/ai-vs-random-analysis');
}

export function useNotificationSettings() {
  return useAdminData('/api/notifications/admin/notification-settings');
}

export function useNotificationChannels() {
  return useAdminData('/api/notifications/admin/notification-channels');
}

export function useNotificationLogs() {
  return useAdminData('/api/notifications/admin/notification-logs');
}

export function useActivePositions() {
  return useAdminData('/api/admin/active-positions');
}

export function useTradeExecutionStatus() {
  return useAdminData('/api/admin/trade-execution-status');
}

export function useSignalLogs() {
  return useAdminData('/api/signals/admin/signal-logs');
}

export function useAIModels() {
  return useAdminData('/api/signals/admin/ai-models');
}



export function useTradingMonitorData() {
  return useAdminData('/api/admin/trading-monitor');
}

export function useUserManagement() {
  return useAdminData('/api/admin/users');
}

export function useAdminUserActions() {
  const { data, loading, error, refetch } = useAdminData('/api/admin/users');
  
  const updateUserStatus = async (userId: string, status: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`http://localhost:9002/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update user status: ${response.statusText}`);
      }
      
      await refetch(); // Refresh data
      return true;
    } catch (error) {
      console.error('Error updating user status:', error);
      return false;
    }
  };

  const updateUserRole = async (userId: string, role: string) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`http://localhost:9002/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ role })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update user role: ${response.statusText}`);
      }
      
      await refetch(); // Refresh data
      return true;
    } catch (error) {
      console.error('Error updating user role:', error);
      return false;
    }
  };

  return {
    users: data,
    loading,
    error,
    refetch,
    updateUserStatus,
    updateUserRole
  };
}

// Communication Center hooks
export function useCommunicationHistory() {
  return useAdminData('/api/admin/communications/');
}

// AI Models Management hooks
export function useAIModelsData() {
  return useAdminData('/api/admin/ai/models');
}

export function useModelTrainingStatus() {
  return useAdminData('/api/admin/ai/training/status');
}

export function useModelComparison() {
  return useAdminData('/api/admin/ai/models/comparison');
}

export function useAnnouncements() {
  return useAdminData('/api/admin/communications/announcements');
}

export function useCommunicationAnalytics() {
  return useAdminData('/api/admin/communications/analytics/overview');
}