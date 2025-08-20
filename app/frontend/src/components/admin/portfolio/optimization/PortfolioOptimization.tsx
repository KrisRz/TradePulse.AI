import { useState, useEffect } from 'preact/hooks';
import { Settings, Target, TrendingUp, BarChart3, Zap, RefreshCw, CheckCircle, AlertCircle } from 'lucide-preact';

interface PortfolioOptimizationProps {
  portfolioData: any;
}

export default function PortfolioOptimization({ portfolioData }: PortfolioOptimizationProps) {
  const [optimizationMode, setOptimizationMode] = useState('sharpe');
  const [rebalanceFrequency, setRebalanceFrequency] = useState('weekly');
  const [isOptimizing, setIsOptimizing] = useState(false);

  const stats = portfolioData?.stats || {};
  const totalValue = stats.total_value || 10000;
  const availableBalance = stats.available_balance || 10000;
  const currentExposure = ((totalValue - availableBalance) / totalValue) * 100;

  // Current portfolio efficiency metrics
  const currentMetrics = {
    sharpeRatio: 1.85,
    efficiency: 78.2,
    diversificationRatio: 0.45,
    riskAdjustedReturn: 24.5,
    informationRatio: 1.32,
    calmarRatio: 2.31,
    maxDrawdown: 8.2,
    volatility: 18.5
  };

  // Optimization recommendations
  const optimizationRecommendations = [
    {
      type: 'Position Sizing',
      current: 'Manual sizing based on signals',
      recommended: 'Kelly Criterion with 0.25 fractional sizing',
      expectedImprovement: '+12.3% Sharpe Ratio',
      priority: 'High',
      status: 'pending'
    },
    {
      type: 'Rebalancing Frequency',
      current: 'Ad-hoc rebalancing',
      recommended: 'Weekly threshold-based rebalancing',
      expectedImprovement: '+8.7% Annual Return',
      priority: 'Medium',
      status: 'pending'
    },
    {
      type: 'Risk Budget Allocation',
      current: 'Equal risk per position',
      recommended: 'Volatility-weighted risk budgeting',
      expectedImprovement: '+15.2% Risk-Adjusted Return',
      priority: 'High',
      status: 'pending'
    },
    {
      type: 'Exit Strategy Optimization',
      current: 'Fixed stop-loss levels',
      recommended: 'ATR-based dynamic stops',
      expectedImprovement: '+6.4% Win Rate',
      priority: 'Medium',
      status: 'pending'
    }
  ];

  // Efficient frontier data
  const efficientFrontierPoints = [
    { risk: 12.5, return: 18.2, label: 'Conservative' },
    { risk: 15.8, return: 22.4, label: 'Moderate' },
    { risk: 18.5, return: 24.5, label: 'Current' },
    { risk: 22.1, return: 28.7, label: 'Aggressive' },
    { risk: 28.3, return: 31.2, label: 'High Risk' }
  ];

  // Rebalancing analysis
  const rebalancingAnalysis = {
    lastRebalance: '5 days ago',
    deviation: 3.2,
    threshold: 5.0,
    recommendedAction: 'Monitor - Within tolerance',
    costEstimate: 0.05,
    taxImpact: 0.0, // Virtual portfolio
    expectedBenefit: 1.8
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
    // Simulate optimization process
    await new Promise(resolve => setTimeout(resolve, 3000));
    setIsOptimizing(false);
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
              onChange={(e) => setOptimizationMode(e.target.value)}
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
              onChange={(e) => setRebalanceFrequency(e.target.value)}
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
              <AlertCircle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
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
                    <AlertCircle className="w-4 h-4 text-yellow-600" />
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
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance Attribution</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">+18.5%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">AI Signal Alpha</div>
            <div className="text-xs text-green-600 dark:text-green-400">Strong contribution</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">+6.2%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Timing Selection</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">Good execution</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">-0.3%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Transaction Costs</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">Minimal impact</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">+24.4%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Total Attribution</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">Excellent</div>
          </div>
        </div>
      </div>
    </div>
  );
}
