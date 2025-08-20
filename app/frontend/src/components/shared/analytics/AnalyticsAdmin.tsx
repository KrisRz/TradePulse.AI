import { useState, useEffect } from 'preact/hooks';
import { BarChart3, TrendingUp, Brain, Timer, Target, Presentation, Trophy, AlertTriangle } from 'lucide-preact';
import { useAdminData, useAnalyticsOverview } from '../../hooks/admin-hooks';

interface AnalyticsOverview {
  backtesting_summary: {
    total_strategies_tested: number;
    best_performing_strategy: string;
    best_strategy_return: number;
    avg_sharpe_ratio: number;
    total_trades_analyzed: number;
    win_rate: number;
    max_drawdown: number;
    last_backtest: string;
  };
  ai_vs_random: {
    comparison_runs: number;
    ai_wins: number;
    ai_win_rate: number;
    average_ai_advantage: number;
    statistical_significance: boolean;
    p_value: number;
    last_comparison: string;
  };
  model_performance: {
    enhanced_ensemble_r2: number;
    elastic_net_weight: number;
    random_forest_weight: number;
    model_accuracy_mape: number;
    models_in_production: number;
    last_optimization: string;
  };
  live_performance: {
    current_portfolio_value: number;
    daily_return: number;
    ytd_return: number;
    active_positions: number;
    total_predictions_today: number;
    prediction_accuracy: number;
  };
}

interface BacktestingResults {
  strategies: Array<{
    name: string;
    description: string;
    performance: {
      total_return: number;
      sharpe_ratio: number;
      sortino_ratio: number;
      max_drawdown: number;
      win_rate: number;
      profit_factor: number;
      total_trades: number;
    };
    risk_metrics: {
      var_95: number;
      cvar_95: number;
      volatility: number;
      calmar_ratio: number;
    };
    status: string;
  }>;
  historical_performance: Array<{
    date: string;
    enhanced_ensemble: number;
    elastic_net: number;
    random_forest: number;
  }>;
  drawdown_analysis: Array<{
    date: string;
    enhanced_ensemble: number;
    elastic_net: number;
    random_forest: number;
  }>;
}

interface AIVsRandomAnalysis {
  comparison_summary: {
    total_runs: number;
    ai_wins: number;
    ai_win_percentage: number;
    statistical_significance: boolean;
    confidence_level: number;
    p_value: number;
    last_updated: string;
  };
  performance_metrics: {
    ai_strategy: {
      average_return: number;
      return_std: number;
      sharpe_ratio: number;
      sharpe_std: number;
      max_return: number;
      min_return: number;
      volatility: number;
    };
    random_strategy: {
      average_return: number;
      return_std: number;
      sharpe_ratio: number;
      sharpe_std: number;
      max_return: number;
      min_return: number;
      volatility: number;
    };
  };
  individual_runs: Array<{
    run_id: number;
    ai_return: number;
    random_return: number;
    ai_advantage: number;
    ai_sharpe: number;
    random_sharpe: number;
    winner: string;
  }>;
  insights: string[];
}

interface HistoricalPerformance {
  period: string;
  portfolio_performance: Array<{
    date: string;
    value: number;
    return_pct: number;
  }>;
  summary_stats: {
    start_value: number;
    end_value: number;
    total_return: number;
    max_value: number;
    min_value: number;
    volatility: number;
    sharpe_ratio: number;
  };
  trade_distribution: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    avg_trade_duration: number;
    best_trade: number;
    worst_trade: number;
  };
  market_conditions: Array<{
    condition: string;
    trades: number;
    win_rate: number;
    avg_return: number;
  }>;
}

export default function AnalyticsAdmin() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedPeriod, setSelectedPeriod] = useState('30d');
  const [autoRefresh, setAutoRefresh] = useState(false);

  console.log('📊 AnalyticsAdmin component mounted');

  const {
    data: analyticsOverview,
    loading: overviewLoading,
    error: overviewError,
    refetch: refetchOverview
  } = useAnalyticsOverview();

  console.log('📊 Analytics Overview Hook State:', {
    data: analyticsOverview,
    loading: overviewLoading,
    error: overviewError
  });

  const {
    data: backtestingResults,
    loading: backtestingLoading,
    error: backtestingError,
    refetch: refetchBacktesting
  } = useAdminData<BacktestingResults>('/api/analytics/admin/backtesting-results');

  const {
    data: aiVsRandomData,
    loading: aiVsRandomLoading,
    error: aiVsRandomError,
    refetch: refetchAiVsRandom
  } = useAdminData<AIVsRandomAnalysis>('/api/analytics/admin/ai-vs-random-analysis');

  const {
    data: historicalData,
    loading: historicalLoading,
    error: historicalError,
    refetch: refetchHistorical
  } = useAdminData<HistoricalPerformance>(`/api/analytics/admin/historical-performance?period=${selectedPeriod}`);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        if (activeTab === 'overview') refetchOverview();
        if (activeTab === 'backtesting') refetchBacktesting();
        if (activeTab === 'ai-vs-random') refetchAiVsRandom();
        if (activeTab === 'historical') refetchHistorical();
      }, 30000); // 30 seconds

      return () => clearInterval(interval);
    }
  }, [autoRefresh, activeTab]);

  const tabs = [
    { id: 'overview', name: 'Overview', icon: Presentation },
    { id: 'backtesting', name: 'Backtesting', icon: BarChart3 },
    { id: 'ai-vs-random', name: 'AI vs Random', icon: Brain },
    { id: 'historical', name: 'Historical', icon: Timer }
  ];

  const MetricCard = ({ title, value, change, icon: Icon, trend = 'neutral' }: any) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <Icon className="h-8 w-8 text-indigo-600" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{title}</dt>
              <dd className="text-2xl font-semibold text-gray-900 dark:text-white">{value}</dd>
            </dl>
          </div>
        </div>
        {change && (
          <div className={`text-sm font-medium ${
            trend === 'up' ? 'text-green-600' : 
            trend === 'down' ? 'text-red-600' : 
            'text-gray-500'
          }`}>
            {change}
          </div>
        )}
      </div>
    </div>
  );

  const OverviewTab = () => {
    if (overviewLoading) return <div className="text-center py-12">Loading analytics overview...</div>;
    if (overviewError) return <div className="text-center py-12 text-red-600">Error loading overview data</div>;
    if (!analyticsOverview || !analyticsOverview.model_performance || !analyticsOverview.live_performance || !analyticsOverview.backtesting_summary) return null;

    return (
      <div className="space-y-6">
        {/* Key Performance Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Best Strategy Return"
            value={`${analyticsOverview.backtesting_summary.best_strategy_return?.toFixed(2) || '0.00'}%`}
            change="+2.1%"
            icon={Trophy}
            trend="up"
          />
          <MetricCard
            title="Portfolio Value"
            value={`$${analyticsOverview.live_performance.current_portfolio_value?.toLocaleString() || '0'}`}
            change={`${analyticsOverview.live_performance.daily_return > 0 ? '+' : ''}${analyticsOverview.live_performance.daily_return?.toFixed(2) || '0.00'}%`}
            icon={TrendingUp}
            trend={analyticsOverview.live_performance.daily_return > 0 ? 'up' : 'down'}
          />
          <MetricCard
            title="Enhanced Ensemble R²"
            value={`${analyticsOverview.model_performance.enhanced_ensemble_r2?.toFixed(2) || '0.00'}%`}
            change="Industry Leading"
            icon={Brain}
            trend="up"
          />
          <MetricCard
            title="Prediction Accuracy"
            value={`${analyticsOverview.live_performance.prediction_accuracy?.toFixed(1) || '0.0'}%`}
            change={`${analyticsOverview.live_performance.total_predictions_today || 0} predictions`}
            icon={Target}
            trend="up"
          />
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Backtesting Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Backtesting Summary</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Best Performer:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.backtesting_summary.best_performing_strategy}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Win Rate:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.backtesting_summary.win_rate.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Sharpe Ratio:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.backtesting_summary.avg_sharpe_ratio.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Max Drawdown:</span>
                <span className="font-semibold text-red-600">
                  {analyticsOverview.backtesting_summary.max_drawdown.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Total Trades:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.backtesting_summary?.total_trades_analyzed?.toLocaleString() || '0'}
                </span>
              </div>
            </div>
          </div>

          {/* AI vs Random Status */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">AI vs Random Analysis</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">AI Wins:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.ai_vs_random.ai_wins} / {analyticsOverview.ai_vs_random.comparison_runs}
                  <span className="text-sm text-gray-500 ml-2">
                    ({analyticsOverview.ai_vs_random.ai_win_rate.toFixed(1)}%)
                  </span>
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Statistical Significance:</span>
                <span className={`flex items-center font-semibold ${
                  analyticsOverview.ai_vs_random.statistical_significance ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {analyticsOverview.ai_vs_random.statistical_significance ? (
                    <>✅ YES</>
                  ) : (
                    <>⚠️ NO</>
                  )}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">P-Value:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {analyticsOverview.ai_vs_random.p_value.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Average Advantage:</span>
                <span className={`font-semibold ${
                  analyticsOverview.ai_vs_random.average_ai_advantage >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {analyticsOverview.ai_vs_random.average_ai_advantage > 0 ? '+' : ''}
                  {analyticsOverview.ai_vs_random.average_ai_advantage.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Model Performance Overview */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Enhanced Ensemble Performance</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-indigo-600">
                  {analyticsOverview.model_performance.enhanced_ensemble_r2.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">R² Score</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">
                  {analyticsOverview.model_performance.elastic_net_weight.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">ElasticNet Weight</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {analyticsOverview.model_performance.model_accuracy_mape.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">MAPE Error</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const BacktestingTab = () => {
    if (backtestingLoading) return <div className="text-center py-12">Loading backtesting results...</div>;
    if (backtestingError) return <div className="text-center py-12 text-red-600">Error loading backtesting data</div>;
    if (!backtestingResults) return null;

    return (
      <div className="space-y-6">
        {/* Strategy Performance Comparison */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Strategy Performance Comparison</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Strategy</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Return</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Sharpe</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Win Rate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Max DD</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Trades</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {backtestingResults.strategies.map((strategy: any, index: number) => (
                  <tr key={index} className={strategy.status === 'active' ? 'bg-green-50 dark:bg-green-900/20' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">{strategy.name}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">{strategy.description}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-sm font-semibold ${
                        strategy.performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {strategy.performance.total_return > 0 ? '+' : ''}{strategy.performance.total_return.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {strategy.performance.sharpe_ratio.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {strategy.performance.win_rate.toFixed(1)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-semibold text-red-600">
                        {strategy.performance.max_drawdown.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {strategy.performance.total_trades}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        strategy.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {strategy.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Performance Charts Placeholder */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Performance Over Time</h4>
            <div className="h-64 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <Presentation className="h-12 w-12 mx-auto mb-2" />
                <p>Performance chart visualization</p>
                <p className="text-sm">Enhanced Ensemble vs ElasticNet vs Random Forest</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Drawdown Analysis</h4>
            <div className="h-64 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <AlertTriangle className="h-12 w-12 mx-auto mb-2" />
                <p>Drawdown chart visualization</p>
                <p className="text-sm">Maximum drawdown periods analysis</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const AIVsRandomTab = () => {
    if (aiVsRandomLoading) return <div className="text-center py-12">Loading AI vs Random analysis...</div>;
    if (aiVsRandomError) return <div className="text-center py-12 text-red-600">Error loading AI vs Random data</div>;
    if (!aiVsRandomData) return null;

    return (
      <div className="space-y-6">
        {/* Comparison Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">AI vs Random Comparison Summary</h3>
              <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                aiVsRandomData.comparison_summary.statistical_significance 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-yellow-100 text-yellow-800'
              }`}>
                {aiVsRandomData.comparison_summary.statistical_significance ? 'Statistically Significant' : 'Not Significant'}
              </span>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-indigo-600">
                  {aiVsRandomData.comparison_summary.ai_win_percentage.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">AI Win Rate</div>
                <div className="text-xs text-gray-500">
                  ({aiVsRandomData.comparison_summary.ai_wins}/{aiVsRandomData.comparison_summary.total_runs} runs)
                </div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {aiVsRandomData.comparison_summary.p_value.toFixed(4)}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">P-Value</div>
                <div className="text-xs text-gray-500">
                  (α = 0.05)
                </div>
              </div>
              <div className="text-center">
                <div className={`text-3xl font-bold ${
                  aiVsRandomData.performance_metrics.ai_strategy.average_return >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {aiVsRandomData.performance_metrics.ai_strategy.average_return > 0 ? '+' : ''}
                  {aiVsRandomData.performance_metrics.ai_strategy.average_return.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">AI Avg Return</div>
                <div className="text-xs text-gray-500">
                  ± {aiVsRandomData.performance_metrics.ai_strategy.return_std.toFixed(2)}%
                </div>
              </div>
              <div className="text-center">
                <div className={`text-3xl font-bold ${
                  aiVsRandomData.performance_metrics.random_strategy.average_return >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {aiVsRandomData.performance_metrics.random_strategy.average_return > 0 ? '+' : ''}
                  {aiVsRandomData.performance_metrics.random_strategy.average_return.toFixed(2)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Random Avg Return</div>
                <div className="text-xs text-gray-500">
                  ± {aiVsRandomData.performance_metrics.random_strategy.return_std.toFixed(2)}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Individual Run Results */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Individual Comparison Runs</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Run</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">AI Return</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Random Return</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Advantage</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">AI Sharpe</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Random Sharpe</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Winner</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {aiVsRandomData.individual_runs.map((run: any) => (
                  <tr key={run.run_id} className={run.winner === 'AI' ? 'bg-green-50 dark:bg-green-900/20' : ''}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      Run {run.run_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-sm font-semibold ${
                        run.ai_return >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {run.ai_return > 0 ? '+' : ''}{run.ai_return.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-sm font-semibold ${
                        run.random_return >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {run.random_return > 0 ? '+' : ''}{run.random_return.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`text-sm font-semibold ${
                        run.ai_advantage >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {run.ai_advantage > 0 ? '+' : ''}{run.ai_advantage.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {run.ai_sharpe.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {run.random_sharpe.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        run.winner === 'AI' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {run.winner}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Key Insights */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Key Insights</h3>
          </div>
          <div className="p-6">
            <ul className="space-y-3">
              {aiVsRandomData.insights.map((insight: string, index: number) => (
                <li key={index} className="flex items-start">
                  <div className="flex-shrink-0 h-6 w-6 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                    <span className="text-xs font-semibold text-indigo-800">{index + 1}</span>
                  </div>
                  <span className="text-sm text-gray-700 dark:text-gray-300">{insight}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  };

  const HistoricalTab = () => {
    if (historicalLoading) return <div className="text-center py-12">Loading historical data...</div>;
    if (historicalError) return <div className="text-center py-12 text-red-600">Error loading historical data</div>;
    if (!historicalData) return null;

    return (
      <div className="space-y-6">
        {/* Period Selector */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Historical Performance Analysis</h3>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod((e.target as HTMLSelectElement).value)}
              className="bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm"
            >
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${
                historicalData.summary_stats.total_return >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {historicalData.summary_stats.total_return > 0 ? '+' : ''}
                {historicalData.summary_stats.total_return.toFixed(2)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Return</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {historicalData.summary_stats.sharpe_ratio.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {historicalData.summary_stats.volatility.toFixed(2)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Volatility</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {historicalData.trade_distribution.total_trades}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Total Trades</div>
            </div>
          </div>
        </div>

        {/* Portfolio Performance Chart Placeholder */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Portfolio Value Over Time</h4>
          <div className="h-80 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <Presentation className="h-16 w-16 mx-auto mb-4" />
              <p className="text-lg">Portfolio performance chart</p>
              <p className="text-sm">
                {historicalData.period.toUpperCase()} view: ${historicalData.summary_stats.start_value.toLocaleString()} → 
                ${historicalData.summary_stats.end_value.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Trade Distribution and Market Conditions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white">Trade Distribution</h4>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Winning Trades:</span>
                <span className="font-semibold text-green-600">
                  {historicalData.trade_distribution.winning_trades} 
                  ({((historicalData.trade_distribution.winning_trades / historicalData.trade_distribution.total_trades) * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Losing Trades:</span>
                <span className="font-semibold text-red-600">
                  {historicalData.trade_distribution.losing_trades}
                  ({((historicalData.trade_distribution.losing_trades / historicalData.trade_distribution.total_trades) * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Avg Duration:</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {historicalData.trade_distribution.avg_trade_duration.toFixed(1)} min
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Best Trade:</span>
                <span className="font-semibold text-green-600">
                  +{historicalData.trade_distribution.best_trade.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Worst Trade:</span>
                <span className="font-semibold text-red-600">
                  {historicalData.trade_distribution.worst_trade.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white">Performance by Market Condition</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Condition</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Trades</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Win Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Avg Return</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {historicalData.market_conditions.map((condition: any, index: number) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {condition.condition}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {condition.trades}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {condition.win_rate.toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`text-sm font-semibold ${
                          condition.avg_return >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {condition.avg_return > 0 ? '+' : ''}{condition.avg_return.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics Dashboard</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Comprehensive backtesting results, AI vs Random comparisons, and historical performance analysis
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Auto-refresh (30s)</span>
          </label>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'backtesting' && <BacktestingTab />}
        {activeTab === 'ai-vs-random' && <AIVsRandomTab />}
        {activeTab === 'historical' && <HistoricalTab />}
      </div>
    </div>
  );
} 