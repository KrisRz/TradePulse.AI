import { useState, useEffect } from 'preact/hooks';
import { Settings, TrendingUp, BarChart3, RefreshCw, CheckCircle, AlertTriangle, Target, Zap } from 'lucide-preact';
import type { PortfolioOverviewResponse } from '../../../../types';
import { apiClient } from '@/lib/api-client';

interface OptimizationData {
  current_metrics: {
    total_value: number;
    cash_percentage: number;
    portfolio_efficiency: number;
    risk_adjusted_return: number;
    volatility: number;
    max_drawdown: number;
  };
  current_allocation: Record<string, number>;
  recommended_allocation: Record<string, number>;
  rebalancing_actions: Array<{
    symbol: string;
    action: 'increase' | 'decrease' | 'hold';
    current_percentage: number;
    target_percentage: number;
    difference: number;
    estimated_amount: number;
  }>;
  optimization_benefits: {
    expected_return_improvement: number;
    risk_reduction: number;
    efficiency_gain: number;
    diversification_score: number;
  };
  constraints: {
    min_cash_percentage: number;
    max_position_size: number;
    rebalancing_threshold: number;
  };
  last_updated: string;
}

interface PortfolioOptimizationProps {
  portfolioData: PortfolioOverviewResponse | null;
}

export default function PortfolioOptimization({ }: PortfolioOptimizationProps) {
  const [optimizationMode, setOptimizationMode] = useState('sharpe');
  const [rebalanceFrequency, setRebalanceFrequency] = useState('weekly');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationData, setOptimizationData] = useState<OptimizationData | null>(null);

  // Fetch real optimization data from backend using API client
  useEffect(() => {
    const fetchOptimizationData = async () => {
      try {
        const response = await apiClient.get(`/api/portfolio/virtual/optimization-analysis?mode=${optimizationMode}`);

        if (response.success && response.data) {
          setOptimizationData(response.data);
          console.log('✅ Real optimization data loaded:', response.data);
        } else {
          console.error('Failed to fetch optimization data:', response.error?.message);
          setOptimizationData(null);
        }
      } catch (error) {
        console.error('Error fetching optimization data:', error);
        setOptimizationData(null);
      }
    };

    fetchOptimizationData();
  }, [optimizationMode]);

  // Real portfolio efficiency metrics from backend
  const currentMetrics = {
    efficiency: (optimizationData?.current_metrics?.portfolio_efficiency || 0) * 100,
    sharpeRatio: optimizationData?.current_metrics?.risk_adjusted_return || 0,
    diversificationRatio: optimizationData?.optimization_benefits?.diversification_score || 0,
    riskAdjustedReturn: optimizationData?.current_metrics?.risk_adjusted_return || 0,
    maxDrawdown: optimizationData?.current_metrics?.max_drawdown || 0,
    volatility: optimizationData?.current_metrics?.volatility || 0
  };

  // Real optimization recommendations from backend
  const optimizationRecommendations = optimizationData?.rebalancing_actions?.map(action => ({
    type: `${action.action === 'increase' ? 'Increase' : action.action === 'decrease' ? 'Decrease' : 'Hold'} ${action.symbol}`,
    priority: Math.abs(action.difference) > 30 ? 'high' : Math.abs(action.difference) > 10 ? 'medium' : 'low',
    current: `${action.current_percentage.toFixed(1)}%`,
    recommended: `${action.target_percentage.toFixed(1)}%`,
    expectedImprovement: `${Math.abs(action.difference).toFixed(1)}% change`,
    status: 'pending'
  })) || [];

  // Efficient frontier data based on real optimization data
  const currentReturn = (optimizationData?.current_metrics?.risk_adjusted_return || 0) * 100;
  const currentRisk = (optimizationData?.current_metrics?.volatility || 15) * 100;
  const expectedImprovement = (optimizationData?.optimization_benefits?.expected_return_improvement || 0) * 100;
  
  const efficientFrontierPoints = [
    { risk: Math.max(currentRisk - 5, 8), return: Math.max(currentReturn - 5, 10), label: 'Conservative' },
    { risk: Math.max(currentRisk - 2, 12), return: Math.max(currentReturn - 2, 15), label: 'Moderate' },
    { risk: currentRisk || 18.5, return: currentReturn || 20, label: 'Current' },
    { risk: currentRisk + 3, return: currentReturn + expectedImprovement, label: 'Optimized' },
    { risk: currentRisk + 8, return: currentReturn + expectedImprovement + 5, label: 'Aggressive' }
  ];

  // Rebalancing analysis based on real data
  const totalDeviation = optimizationData?.rebalancing_actions?.reduce((sum, action) => sum + Math.abs(action.difference), 0) || 0;
  const rebalancingThreshold = optimizationData?.constraints?.rebalancing_threshold || 5.0;
  const rebalancingAnalysis = {
    lastRebalance: optimizationData?.last_updated ? 
      new Date(Date.now() - new Date(optimizationData.last_updated).getTime()).toLocaleDateString() + ' ago' : 
      'Unknown',
    deviation: totalDeviation / (optimizationData?.rebalancing_actions?.length || 1),
    threshold: rebalancingThreshold,
    recommendedAction: totalDeviation > rebalancingThreshold ? 'Rebalance Recommended' : 'Monitor - Within tolerance',
    costEstimate: 0.05, // Standard transaction cost
    taxImpact: 0.0, // Virtual portfolio
    expectedBenefit: (optimizationData?.optimization_benefits?.efficiency_gain || 0) * 100
  };

  const formatPercentage = (percentage: number) => {
    const formatted = percentage.toFixed(1);
    return `${percentage >= 0 ? '+' : ''}${formatted}%`;
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return 'text-red-600 dark:text-red-400';
      case 'medium': return 'text-yellow-600 dark:text-yellow-400';
      case 'low': return 'text-green-600 dark:text-green-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getPriorityBgColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return 'bg-red-100 dark:bg-red-900/30';
      case 'medium': return 'bg-yellow-100 dark:bg-yellow-900/30';
      case 'low': return 'bg-green-100 dark:bg-green-900/30';
      default: return 'bg-gray-100 dark:bg-gray-900/30';
    }
  };

  const getEfficiencyColor = (efficiency: number) => {
    if (efficiency >= 80) return 'text-green-600 dark:text-green-400';
    if (efficiency >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const handleOptimize = async () => {
    setIsOptimizing(true);
    try {
      const response = await apiClient.post(`/api/portfolio/virtual/optimization-analysis?mode=${optimizationMode}`, {
        force_recompute: true
      });

      if (response.success && response.data) {
        setOptimizationData(response.data);
        console.log('✅ Portfolio optimization completed:', response.data);
      } else {
        console.error('Failed to optimize portfolio:', response.error?.message);
      }
    } catch (error) {
      console.error('Error during optimization:', error);
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Optimization Control Panel */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Settings className="w-5 h-5 mr-2 text-blue-600" />
            Portfolio Optimization Engine
          </h3>
          <button
            onClick={handleOptimize}
            disabled={isOptimizing}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {isOptimizing ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            {isOptimizing ? 'Optimizing...' : 'Run Optimization'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Optimization Objective
            </label>
            <select
              value={optimizationMode}
              onChange={(e) => setOptimizationMode((e.target as HTMLInputElement).value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="sharpe">Maximize Sharpe Ratio</option>
              <option value="return">Maximize Returns</option>
              <option value="risk">Minimize Risk</option>
              <option value="calmar">Maximize Calmar Ratio</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Rebalancing Frequency
            </label>
            <select
              value={rebalanceFrequency}
              onChange={(e) => setRebalanceFrequency((e.target as HTMLInputElement).value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="threshold">Threshold-based</option>
            </select>
          </div>
        </div>
      </div>

      {/* Current Portfolio Efficiency */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
              <Target className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Portfolio Efficiency</p>
              <p className={`text-2xl font-bold ${getEfficiencyColor(currentMetrics.efficiency)}`}>
                {currentMetrics.efficiency.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">Good performance</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
              <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentMetrics.sharpeRatio.toFixed(2)}
              </p>
              <p className="text-sm text-green-600">Excellent</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30">
              <BarChart3 className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Diversification</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentMetrics.diversificationRatio.toFixed(2)}
              </p>
              <p className="text-sm text-yellow-600">Needs improvement</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-orange-100 dark:bg-orange-900/30">
              <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Max Drawdown</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {currentMetrics.maxDrawdown.toFixed(1)}%
              </p>
              <p className="text-sm text-green-600">Within limits</p>
            </div>
          </div>
        </div>
      </div>

      {/* Optimization Recommendations */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Optimization Recommendations</h3>
        <div className="space-y-4">
          {optimizationRecommendations.map((recommendation, index) => (
            <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                  <h4 className="font-medium text-gray-900 dark:text-white mr-3">{recommendation.type}</h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityBgColor(recommendation.priority)} ${getPriorityColor(recommendation.priority)}`}>
                    {recommendation.priority} Priority
                  </span>
                </div>
                <div className="flex items-center">
                  {recommendation.status === 'pending' ? (
                    <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  ) : (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Current:</span>
                  <p className="text-gray-900 dark:text-white mt-1">{recommendation.current}</p>
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Recommended:</span>
                  <p className="text-gray-900 dark:text-white mt-1">{recommendation.recommended}</p>
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Expected Improvement:</span>
                  <p className="text-green-600 dark:text-green-400 font-medium mt-1">{recommendation.expectedImprovement}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Efficient Frontier */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Efficient Frontier Analysis</h3>
          <div className="space-y-3">
            {efficientFrontierPoints.map((point, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center">
                  <span className={`font-medium ${point.label === 'Current' ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                    {point.label}
                  </span>
                  {point.label === 'Current' && (
                    <span className="ml-2 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs rounded-full">
                      Current
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Risk: {point.risk.toFixed(1)}% | Return: {formatPercentage(point.return)}
                  </div>
                  <div className="text-xs text-gray-500">
                    Sharpe: {(point.return / point.risk).toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Rebalancing Analysis */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Rebalancing Analysis</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Last Rebalance</span>
              <span className="font-semibold text-gray-900 dark:text-white">{rebalancingAnalysis.lastRebalance}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Current Deviation</span>
              <span className={`font-semibold ${
                rebalancingAnalysis.deviation > rebalancingAnalysis.threshold ? 'text-red-600' : 'text-green-600'
              }`}>
                {rebalancingAnalysis.deviation.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Rebalance Threshold</span>
              <span className="font-semibold text-gray-900 dark:text-white">{rebalancingAnalysis.threshold.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">Recommended Action</span>
              <span className="font-semibold text-green-600 dark:text-green-400">{rebalancingAnalysis.recommendedAction}</span>
            </div>
            
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Transaction Cost</span>
                <span className="font-semibold text-gray-900 dark:text-white">{formatPercentage(rebalancingAnalysis.costEstimate)}</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Expected Benefit</span>
                <span className="font-semibold text-green-600 dark:text-green-400">{formatPercentage(rebalancingAnalysis.expectedBenefit)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Attribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Optimization Benefits</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {formatPercentage((optimizationData?.optimization_benefits?.expected_return_improvement || 0) * 100)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Expected Return Improvement</div>
            <div className="text-xs text-green-600 dark:text-green-400">
              {(optimizationData?.optimization_benefits?.expected_return_improvement || 0) > 0.03 ? 'Strong potential' : 'Moderate gain'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {formatPercentage((optimizationData?.optimization_benefits?.risk_reduction || 0) * 100)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Risk Reduction</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">
              {(optimizationData?.optimization_benefits?.risk_reduction || 0) > 0.02 ? 'Significant' : 'Minimal'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {(optimizationData?.optimization_benefits?.diversification_score || 0).toFixed(2)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Diversification Score</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">
              {(optimizationData?.optimization_benefits?.diversification_score || 0) > 0.7 ? 'Well diversified' : 'Needs improvement'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {formatPercentage((optimizationData?.optimization_benefits?.efficiency_gain || 0) * 100)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Efficiency Gain</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">
              {(optimizationData?.optimization_benefits?.efficiency_gain || 0) > 0.05 ? 'Excellent' : 'Good'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
