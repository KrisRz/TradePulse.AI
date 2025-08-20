import { useState, useEffect } from 'preact/hooks';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Clock, 
  BarChart3,
  PieChart,
  Activity,
  Shield,
  Zap,
  Award,
  AlertTriangle,
  RefreshCw,
  Eye,
  Info
} from 'lucide-preact';

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
      
      // Generate mock metrics data
      const mockMetrics: MetricData[] = [
        // Performance Metrics
        {
          id: 'total-pnl',
          category: 'performance',
          name: 'Total P&L',
          value: 2456.78,
          displayValue: '$2,456.78',
          change: 234.56,
          changePercent: 10.55,
          trend: 'up',
          status: 'good',
          description: 'Total profit/loss across all positions',
          icon: 'DollarSign',
          unit: 'currency',
          benchmark: 2000,
          target: 5000,
          lastUpdate: new Date()
        },
        {
          id: 'win-rate',
          category: 'performance',
          name: 'Win Rate',
          value: 68.5,
          displayValue: '68.5%',
          change: 3.2,
          changePercent: 4.9,
          trend: 'up',
          status: 'good',
          description: 'Percentage of winning trades',
          icon: 'Target',
          unit: 'percentage',
          benchmark: 60,
          target: 70,
          lastUpdate: new Date()
        },
        {
          id: 'profit-factor',
          category: 'performance',
          name: 'Profit Factor',
          value: 2.34,
          displayValue: '2.34',
          change: 0.12,
          changePercent: 5.4,
          trend: 'up',
          status: 'good',
          description: 'Ratio of gross profit to gross loss',
          icon: 'Award',
          unit: 'ratio',
          benchmark: 1.5,
          target: 2.0,
          lastUpdate: new Date()
        },
        {
          id: 'sharpe-ratio',
          category: 'performance',
          name: 'Sharpe Ratio',
          value: 1.85,
          displayValue: '1.85',
          change: -0.05,
          changePercent: -2.6,
          trend: 'down',
          status: 'warning',
          description: 'Risk-adjusted return measure',
          icon: 'BarChart3',
          unit: 'ratio',
          benchmark: 1.0,
          target: 2.0,
          lastUpdate: new Date()
        },
        {
          id: 'roi',
          category: 'performance',
          name: 'ROI',
          value: 24.57,
          displayValue: '24.57%',
          change: 2.1,
          changePercent: 9.3,
          trend: 'up',
          status: 'good',
          description: 'Return on investment',
          icon: 'TrendingUp',
          unit: 'percentage',
          benchmark: 15,
          target: 25,
          lastUpdate: new Date()
        },
        {
          id: 'alpha',
          category: 'performance',
          name: 'Alpha',
          value: 3.2,
          displayValue: '3.2%',
          change: 0.8,
          changePercent: 33.3,
          trend: 'up',
          status: 'good',
          description: 'Excess return over benchmark',
          icon: 'Zap',
          unit: 'percentage',
          benchmark: 0,
          target: 2,
          lastUpdate: new Date()
        },

        // Risk Metrics
        {
          id: 'max-drawdown',
          category: 'risk',
          name: 'Max Drawdown',
          value: -8.5,
          displayValue: '-8.5%',
          change: -1.2,
          changePercent: -16.5,
          trend: 'down',
          status: 'warning',
          description: 'Maximum peak-to-trough decline',
          icon: 'TrendingDown',
          unit: 'percentage',
          benchmark: -10,
          target: -5,
          lastUpdate: new Date()
        },
        {
          id: 'var-95',
          category: 'risk',
          name: 'VaR (95%)',
          value: 450.23,
          displayValue: '$450.23',
          change: 25.45,
          changePercent: 6.0,
          trend: 'up',
          status: 'warning',
          description: 'Value at Risk at 95% confidence level',
          icon: 'Shield',
          unit: 'currency',
          benchmark: 500,
          target: 300,
          lastUpdate: new Date()
        },
        {
          id: 'volatility',
          category: 'risk',
          name: 'Volatility',
          value: 15.8,
          displayValue: '15.8%',
          change: -0.7,
          changePercent: -4.2,
          trend: 'down',
          status: 'good',
          description: 'Standard deviation of returns',
          icon: 'Activity',
          unit: 'percentage',
          benchmark: 20,
          target: 12,
          lastUpdate: new Date()
        },
        {
          id: 'beta',
          category: 'risk',
          name: 'Beta',
          value: 1.12,
          displayValue: '1.12',
          change: 0.03,
          changePercent: 2.8,
          trend: 'up',
          status: 'neutral',
          description: 'Sensitivity to market movements',
          icon: 'BarChart3',
          unit: 'ratio',
          benchmark: 1.0,
          target: 0.8,
          lastUpdate: new Date()
        },
        {
          id: 'correlation',
          category: 'risk',
          name: 'Correlation',
          value: 0.45,
          displayValue: '0.45',
          change: -0.02,
          changePercent: -4.3,
          trend: 'down',
          status: 'good',
          description: 'Correlation with market index',
          icon: 'PieChart',
          unit: 'ratio',
          benchmark: 0.7,
          target: 0.3,
          lastUpdate: new Date()
        },

        // Activity Metrics
        {
          id: 'total-trades',
          category: 'activity',
          name: 'Total Trades',
          value: 247,
          displayValue: '247',
          change: 18,
          changePercent: 7.9,
          trend: 'up',
          status: 'good',
          description: 'Number of completed trades',
          icon: 'Activity',
          unit: 'number',
          benchmark: 200,
          target: 300,
          lastUpdate: new Date()
        },
        {
          id: 'avg-trade-duration',
          category: 'activity',
          name: 'Avg Duration',
          value: 78,
          displayValue: '78 min',
          change: -5,
          changePercent: -6.0,
          trend: 'down',
          status: 'good',
          description: 'Average trade duration in minutes',
          icon: 'Clock',
          unit: 'number',
          benchmark: 90,
          target: 60,
          lastUpdate: new Date()
        },
        {
          id: 'trading-frequency',
          category: 'activity',
          name: 'Trading Frequency',
          value: 8.2,
          displayValue: '8.2/day',
          change: 0.5,
          changePercent: 6.5,
          trend: 'up',
          status: 'good',
          description: 'Average trades per day',
          icon: 'Zap',
          unit: 'number',
          benchmark: 5,
          target: 10,
          lastUpdate: new Date()
        },
        {
          id: 'volume-traded',
          category: 'activity',
          name: 'Volume Traded',
          value: 125000,
          displayValue: '$125K',
          change: 12000,
          changePercent: 10.6,
          trend: 'up',
          status: 'good',
          description: 'Total trading volume',
          icon: 'BarChart3',
          unit: 'currency',
          benchmark: 100000,
          target: 150000,
          lastUpdate: new Date()
        },

        // Portfolio Metrics
        {
          id: 'portfolio-value',
          category: 'portfolio',
          name: 'Portfolio Value',
          value: 12456.78,
          displayValue: '$12,456.78',
          change: 456.78,
          changePercent: 3.8,
          trend: 'up',
          status: 'good',
          description: 'Total portfolio value',
          icon: 'DollarSign',
          unit: 'currency',
          benchmark: 10000,
          target: 15000,
          lastUpdate: new Date()
        },
        {
          id: 'cash-balance',
          category: 'portfolio',
          name: 'Cash Balance',
          value: 3456.78,
          displayValue: '$3,456.78',
          change: -234.56,
          changePercent: -6.4,
          trend: 'down',
          status: 'neutral',
          description: 'Available cash balance',
          icon: 'DollarSign',
          unit: 'currency',
          benchmark: 2000,
          target: 5000,
          lastUpdate: new Date()
        },
        {
          id: 'positions-open',
          category: 'portfolio',
          name: 'Open Positions',
          value: 5,
          displayValue: '5',
          change: 1,
          changePercent: 25.0,
          trend: 'up',
          status: 'neutral',
          description: 'Number of open positions',
          icon: 'PieChart',
          unit: 'number',
          benchmark: 3,
          target: 8,
          lastUpdate: new Date()
        },
        {
          id: 'portfolio-diversification',
          category: 'portfolio',
          name: 'Diversification',
          value: 0.72,
          displayValue: '0.72',
          change: 0.05,
          changePercent: 7.5,
          trend: 'up',
          status: 'good',
          description: 'Portfolio diversification index',
          icon: 'PieChart',
          unit: 'ratio',
          benchmark: 0.6,
          target: 0.8,
          lastUpdate: new Date()
        }
      ];
      
      setTimeout(() => {
        setMetrics(mockMetrics);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      setLoading(false);
    }
  };

  const getIconComponent = (iconName: string) => {
    const iconMap: { [key: string]: any } = {
      DollarSign,
      TrendingUp,
      TrendingDown,
      Target,
      Clock,
      BarChart3,
      PieChart,
      Activity,
      Shield,
      Zap,
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
    const prefix = change >= 0 ? '+' : '';
    switch (unit) {
      case 'currency': return `${prefix}$${Math.abs(change).toFixed(2)}`;
      case 'percentage': return `${prefix}${change.toFixed(1)}%`;
      case 'ratio': return `${prefix}${change.toFixed(2)}`;
      default: return `${prefix}${change}`;
    }
  };

  const filteredMetrics = selectedCategory === 'all' 
    ? metrics.filter(m => categories.includes(m.category))
    : metrics.filter(m => m.category === selectedCategory);

  const categoryNames = {
    all: 'All Metrics',
    performance: 'Performance',
    risk: 'Risk',
    activity: 'Activity',
    portfolio: 'Portfolio'
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading metrics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
        <span className="text-red-600 dark:text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Performance Metrics
        </h2>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              onRefresh?.();
              fetchMetrics();
            }}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        {['all', ...categories].map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === category
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {categoryNames[category as keyof typeof categoryNames]}
          </button>
        ))}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredMetrics.map((metric) => {
          const IconComponent = getIconComponent(metric.icon);
          const TrendIcon = getTrendIcon(metric.trend);
          
          return (
            <div
              key={metric.id}
              className={`rounded-lg border p-4 cursor-pointer transition-all hover:shadow-md ${getStatusBgColor(metric.status)}`}
              onClick={() => onMetricClick?.(metric)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <IconComponent className={`w-5 h-5 ${getStatusColor(metric.status)}`} />
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      {metric.name}
                    </span>
                  </div>
                  
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                    {metric.displayValue}
                  </div>
                  
                  {showTrends && (
                    <div className="flex items-center space-x-2">
                      <div className={`flex items-center space-x-1 ${getTrendColor(metric.trend)}`}>
                        <TrendIcon className="w-3 h-3" />
                        <span className="text-sm font-medium">
                          {formatChange(metric.change, metric.unit)}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ({metric.changePercent >= 0 ? '+' : ''}{metric.changePercent.toFixed(1)}%)
                      </span>
                    </div>
                  )}
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Show metric details
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  title="View details"
                >
                  <Eye className="w-4 h-4" />
                </button>
              </div>
              
              {/* Progress Bar for Target */}
              {showTargets && metric.target && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span>Target: {metric.unit === 'currency' ? '$' : ''}{metric.target}{metric.unit === 'percentage' ? '%' : ''}</span>
                    <span>
                      {((metric.value / metric.target) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        metric.value >= metric.target
                          ? 'bg-green-500'
                          : metric.value >= metric.target * 0.8
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(100, (metric.value / metric.target) * 100)}%` }}
                    />
                  </div>
                </div>
              )}
              
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {metric.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {filteredMetrics.filter(m => m.status === 'good').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Good Performance</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {filteredMetrics.filter(m => m.status === 'warning').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Needs Attention</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {filteredMetrics.filter(m => m.status === 'danger').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Critical Issues</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {filteredMetrics.filter(m => m.trend === 'up').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Improving</div>
          </div>
        </div>
      </div>

      {/* Insights */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3" />
          <div>
            <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
              Key Insights
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
              <li>• Portfolio showing strong performance with {filteredMetrics.filter(m => m.status === 'good').length} healthy metrics</li>
              <li>• {filteredMetrics.filter(m => m.trend === 'up').length} metrics are improving, indicating positive momentum</li>
              <li>• Risk metrics are within acceptable ranges with controlled volatility</li>
              <li>• Trading activity remains consistent with good execution efficiency</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 