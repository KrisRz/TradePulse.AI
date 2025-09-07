import { useState, useEffect } from 'preact/hooks';
import { DollarSign, TrendingUp, TrendingDown, Clock, BarChart3, Activity, Shield, Award, AlertTriangle, RefreshCw, Info } from 'lucide-preact';

type Icon = typeof DollarSign;

interface MetricData {
  id: string;
  category: 'performance' | 'risk' | 'activity' | 'portfolio';
  name: string;
  value: number;
  displayValue: string;
  change: number;
  changePercent: number;
  trend: 'up' | 'down' | 'neutral';
  status: 'good' | 'warning' | 'danger' | 'neutral';
  description: string;
  icon: string;
  unit: 'currency' | 'percentage' | 'number' | 'ratio';
  benchmark?: number;
  target?: number;
  lastUpdate: Date;
}

interface MetricsGridProps {
  timeRange?: '24h' | '7d' | '30d' | '90d' | '1y';
  categories?: string[];
  showTrends?: boolean;
  showTargets?: boolean;
  onMetricClick?: (metric: MetricData) => void;
  onRefresh?: () => void;
}

export default function MetricsGrid({
  timeRange = '30d',
  categories = ['performance', 'risk', 'activity', 'portfolio'],
  showTrends = true,
  showTargets = true,
  onMetricClick,
  onRefresh
}: MetricsGridProps) {
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    fetchMetrics();
  }, [timeRange]);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // PRODUCTION: Fetch real metrics from professional backend
      const response = await fetch(`http://localhost:9002/api/analytics/metrics?timeRange=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform backend data to MetricData format
      const realMetrics: MetricData[] = data.metrics || [];
      
      setMetrics(realMetrics);
      setLoading(false);
      
    } catch (err) {
      console.error('❌ Failed to fetch real metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      setLoading(false);
      // NO FALLBACK DATA - production ready
      setMetrics([]);
    }
  };

  const getIconComponent = (iconName: string) => {
    const iconMap: { [key: string]: Icon } = {
      DollarSign,
      TrendingUp,
      Clock,
      BarChart3,
      Activity,
      Shield,
      Award,
      AlertTriangle
    };
    return iconMap[iconName] || Activity;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600 dark:text-green-400';
      case 'warning': return 'text-yellow-600 dark:text-yellow-400';
      case 'danger': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'good': return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'warning': return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
      case 'danger': return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      default: return 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return 'text-green-600 dark:text-green-400';
      case 'down': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return TrendingUp;
      case 'down': return TrendingDown;
      default: return Activity;
    }
  };

  const formatChange = (change: number, unit: string) => {
    const sign = change >= 0 ? '+' : '';
    switch (unit) {
      case 'currency': return `${sign}$${Math.abs(change).toFixed(2)}`;
      case 'percentage': return `${sign}${change.toFixed(2)}%`;
      case 'ratio': return `${sign}${change.toFixed(3)}`;
      default: return `${sign}${change.toFixed(0)}`;
    }
  };

  const filteredMetrics = selectedCategory === 'all' 
    ? metrics.filter(metric => categories.includes(metric.category))
    : metrics.filter(metric => metric.category === selectedCategory);

  const categoryOptions = [
    { value: 'all', label: 'All Categories' },
    { value: 'performance', label: 'Performance' },
    { value: 'risk', label: 'Risk' },
    { value: 'activity', label: 'Activity' },
    { value: 'portfolio', label: 'Portfolio' }
  ];

  if (loading) {
    return (
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 animate-pulse"></div>
          <div class="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32 animate-pulse"></div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} class="bg-gray-200 dark:bg-gray-700 h-32 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="text-center py-12">
        <AlertTriangle class="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Failed to Load Metrics
        </h3>
        <p class="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
        <button
          onClick={fetchMetrics}
          class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw class="h-4 w-4 mr-2" />
          Retry
        </button>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div class="text-center py-12">
        <BarChart3 class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          No Metrics Available
        </h3>
        <p class="text-gray-600 dark:text-gray-400">
          No metrics data available for the selected time range.
        </p>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      {/* Header */}
      <div class="flex items-center justify-between">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
          Performance Metrics
        </h2>
        
        <div class="flex items-center space-x-4">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory((e.target as HTMLSelectElement).value)}
            class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
          >
            {categoryOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          
          {/* Refresh Button */}
          <button
            onClick={() => {
              fetchMetrics();
              onRefresh?.();
            }}
            class="inline-flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <RefreshCw class="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredMetrics.map((metric) => {
          const IconComponent = getIconComponent(metric.icon);
          const TrendIcon = getTrendIcon(metric.trend);
          
          return (
            <div
              key={metric.id}
              class={`rounded-lg border p-4 cursor-pointer transition-all hover:shadow-md ${getStatusBgColor(metric.status)}`}
              onClick={() => onMetricClick?.(metric)}
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-2 mb-2">
                    <IconComponent class={`w-5 h-5 ${getStatusColor(metric.status)}`} />
                    <span class="text-sm font-medium text-gray-600 dark:text-gray-400">
                      {metric.name}
                    </span>
                  </div>
                  
                  <div class="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                    {metric.displayValue}
                  </div>
                  
                  {showTrends && (
                    <div class="flex items-center space-x-2">
                      <div class={`flex items-center space-x-1 ${getTrendColor(metric.trend)}`}>
                        <TrendIcon class="w-3 h-3" />
                        <span class="text-sm font-medium">
                          {formatChange(metric.change, metric.unit)}
                        </span>
                      </div>
                      <span class="text-xs text-gray-500 dark:text-gray-400">
                        ({metric.changePercent >= 0 ? '+' : ''}{metric.changePercent.toFixed(1)}%)
                      </span>
                    </div>
                  )}
                </div>
                
                <button
                  class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    // Show metric details or tooltip
                  }}
                >
                  <Info class="h-4 w-4" />
                </button>
              </div>
              
              {/* Target Progress Bar */}
              {showTargets && metric.target && (
                <div class="mt-3">
                  <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span>Progress to Target</span>
                    <span>{((metric.value / metric.target) * 100).toFixed(0)}%</span>
                  </div>
                  <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      class="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min((metric.value / metric.target) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}