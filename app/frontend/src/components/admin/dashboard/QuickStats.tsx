import { useState } from 'preact/hooks';

interface QuickStat {
  label: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: string;
}

export default function QuickStats() {
  const [stats, setStats] = useState<QuickStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuickStats();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchQuickStats, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchQuickStats = async () => {
    try {
      setLoading(true);
      
      // PRODUCTION: Fetch real quick stats from backend/DynamoDB
      const token = localStorage.getItem('auth_token') || 'enterprise_admin_token';
      const response = await fetch('http://localhost:9002/api/portfolio/quick-stats', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        
        // Map real data to QuickStat format
        const realStats: QuickStat[] = [
          {
            label: 'Portfolio Value',
            value: `$${(data.total_value || 0).toLocaleString()}`,
            change: `${data.daily_change >= 0 ? '+' : ''}${(data.daily_change || 0).toFixed(2)}%`,
            changeType: (data.daily_change || 0) >= 0 ? 'positive' : 'negative',
            icon: 'wallet'
          },
          {
            label: 'Today\'s P&L',
            value: `$${(data.daily_pnl || 0).toLocaleString()}`,
            change: `${data.daily_pnl_percentage >= 0 ? '+' : ''}${(data.daily_pnl_percentage || 0).toFixed(2)}%`,
            changeType: (data.daily_pnl || 0) >= 0 ? 'positive' : 'negative',
            icon: 'trending-up'
          },
          {
            label: 'AI Confidence',
            value: `${(data.ai_confidence || 0).toFixed(1)}%`,
            change: `${data.confidence_change >= 0 ? '+' : ''}${(data.confidence_change || 0).toFixed(1)}%`,
            changeType: (data.confidence_change || 0) >= 0 ? 'positive' : 'negative',
            icon: 'brain'
          },
          {
            label: 'Active Signals',
            value: `${data.active_signals || 0}`,
            change: `New: ${data.new_signals || 0}`,
            changeType: 'neutral',
            icon: 'zap'
          }
        ];

        setStats(realStats);
        console.log('✅ Real quick stats loaded:', realStats);
      } else {
        console.error('Failed to fetch quick stats:', response.status);
        setStats([]);
      }
      
      setLoading(false);
      
    } catch (error) {
      console.error('Failed to fetch quick stats:', error);
      setStats([]);
      setLoading(false);
    }
  };

  const getIcon = (iconName: string) => {
    const icons: Record<string, string> = {
      wallet: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z M8 5a2 2 0 012-2h4a2 2 0 012 2v6a2 2 0 01-2 2H10a2 2 0 01-2-2V5z',
      'trending-up': 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
      brain: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
      zap: 'M13 10V3L4 14h7v7l9-11h-7z'
    };
    return icons[iconName] || icons.wallet;
  };

  const getChangeColor = (changeType: string) => {
    switch (changeType) {
      case 'positive':
        return 'text-green-600 dark:text-green-400';
      case 'negative':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getIconColor = (changeType: string) => {
    switch (changeType) {
      case 'positive':
        return 'bg-green-500';
      case 'negative':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  if (loading) {
    return (
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div class="animate-pulse">
              <div class="flex items-center justify-between mb-4">
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                <div class="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
              </div>
              <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-2"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <div key={index} class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm font-medium text-gray-600 dark:text-gray-400">
              {stat.label}
            </div>
            <div class={`w-8 h-8 ${getIconColor(stat.changeType)} rounded-lg flex items-center justify-center`}>
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(stat.icon)}></path>
              </svg>
            </div>
          </div>
          
          <div class="mb-2">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">
              {stat.value}
            </div>
          </div>
          
          <div class={`text-sm font-medium ${getChangeColor(stat.changeType)}`}>
            {stat.change}
          </div>
        </div>
      ))}
    </div>
  );
} 