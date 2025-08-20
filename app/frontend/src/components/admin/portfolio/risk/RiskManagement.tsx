import { useState, useEffect } from 'preact/hooks';
import { Shield, AlertTriangle, TrendingDown, BarChart3, Activity, Target } from 'lucide-preact';

interface RiskManagementProps {
  portfolioData: any;
}

export default function RiskManagement({ portfolioData }: RiskManagementProps) {
  const [riskTimeframe, setRiskTimeframe] = useState('24h');
  
  const stats = portfolioData?.stats || {};
  const totalValue = stats.total_value || 10000;
  const availableBalance = stats.available_balance || 10000;
  const activePositions = stats.active_positions || 0;
  const dailyPnL = stats.daily_pnl || 0;
  const riskExposure = stats.risk_exposure || 0;

  // Mock risk metrics for enterprise dashboard
  const riskMetrics = {
    var_1d: 2.1,      // 1-day Value at Risk
    var_5d: 4.8,      // 5-day Value at Risk  
    var_30d: 12.3,    // 30-day Value at Risk
    exposure: ((totalValue - availableBalance) / totalValue) * 100,
    maxDrawdown: 8.2,
    beta: 1.15,
    correlation: 0.87,
    volatility: 18.5,
    sharpeRatio: 1.85,
    leverageRatio: 1.0,
    portfolioHeat: 35.2
  };

  // Position risk distribution
  const positionRisks = [
    { symbol: 'BTCUSDT', allocation: 65.2, risk: 'Medium', var: 1.8 },
    { symbol: 'Cash', allocation: 34.8, risk: 'Low', var: 0.0 },
  ];

  // Risk scenarios
  const riskScenarios = [
    { scenario: 'Market Crash (-20%)', portfolioImpact: -18.5, probability: 'Low' },
    { scenario: 'High Volatility (+50%)', portfolioImpact: -8.2, probability: 'Medium' },
    { scenario: 'Bitcoin Flash Crash (-30%)', portfolioImpact: -19.6, probability: 'Low' },
    { scenario: 'Normal Market Stress (-10%)', portfolioImpact: -9.2, probability: 'High' }
  ];

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low': return 'text-green-600 dark:text-green-400';
      case 'medium': return 'text-yellow-600 dark:text-yellow-400';
      case 'high': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getRiskBgColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low': return 'bg-green-100 dark:bg-green-900/30';
      case 'medium': return 'bg-yellow-100 dark:bg-yellow-900/30';
      case 'high': return 'bg-red-100 dark:bg-red-900/30';
      default: return 'bg-gray-100 dark:bg-gray-900/30';
    }
  };

  const getVarColor = (var_value: number) => {
    if (var_value < 2) return 'text-green-600 dark:text-green-400';
    if (var_value < 5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getProbabilityColor = (probability: string) => {
    switch (probability.toLowerCase()) {
      case 'low': return 'text-green-600 dark:text-green-400';
      case 'medium': return 'text-yellow-600 dark:text-yellow-400';
      case 'high': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercentage = (percentage: number) => {
    const formatted = percentage.toFixed(2);
    return `${percentage >= 0 ? '' : ''}${formatted}%`;
  };

  // Calculate overall risk level
  const getOverallRiskLevel = () => {
    if (riskMetrics.var_1d < 2 && riskMetrics.exposure < 50) return 'Low';
    if (riskMetrics.var_1d < 5 && riskMetrics.exposure < 75) return 'Medium';
    return 'High';
  };

  const overallRisk = getOverallRiskLevel();

  return (
    <div className="space-y-6">
      {/* Risk Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Overall Risk Level */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Overall Risk Level</p>
              <p className={`text-2xl font-bold mt-1 ${getRiskColor(overallRisk)}`}>
                {overallRisk}
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <Shield className="w-4 h-4 mr-1" />
                <span className="text-sm">Monitored</span>
              </div>
            </div>
            <div className={`p-3 rounded-full ${getRiskBgColor(overallRisk)}`}>
              <Shield className={`w-6 h-6 ${getRiskColor(overallRisk)}`} />
            </div>
          </div>
        </div>

        {/* Value at Risk (1d) */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Value at Risk (1d)</p>
              <p className={`text-2xl font-bold mt-1 ${getVarColor(riskMetrics.var_1d)}`}>
                {riskMetrics.var_1d.toFixed(1)}%
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <span className="text-sm">{formatCurrency(totalValue * riskMetrics.var_1d / 100)}</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-red-100 dark:bg-red-900/30">
              <TrendingDown className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>

        {/* Portfolio Exposure */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Portfolio Exposure</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {riskMetrics.exposure.toFixed(1)}%
              </p>
              <div className="flex items-center mt-2 text-gray-600 dark:text-gray-400">
                <BarChart3 className="w-4 h-4 mr-1" />
                <span className="text-sm">{activePositions} positions</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
              <BarChart3 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Max Drawdown</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {riskMetrics.maxDrawdown.toFixed(1)}%
              </p>
              <div className="flex items-center mt-2 text-green-600 dark:text-green-400">
                <Target className="w-4 h-4 mr-1" />
                <span className="text-sm">Within limits</span>
              </div>
            </div>
            <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900/30">
              <AlertTriangle className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Risk Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Value at Risk Analysis */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Value at Risk Analysis</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">1-Day VaR (95%)</span>
              <span className={`font-semibold ${getVarColor(riskMetrics.var_1d)}`}>
                {riskMetrics.var_1d.toFixed(2)}% ({formatCurrency(totalValue * riskMetrics.var_1d / 100)})
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">5-Day VaR (95%)</span>
              <span className={`font-semibold ${getVarColor(riskMetrics.var_5d)}`}>
                {riskMetrics.var_5d.toFixed(2)}% ({formatCurrency(totalValue * riskMetrics.var_5d / 100)})
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">30-Day VaR (95%)</span>
              <span className={`font-semibold ${getVarColor(riskMetrics.var_30d)}`}>
                {riskMetrics.var_30d.toFixed(2)}% ({formatCurrency(totalValue * riskMetrics.var_30d / 100)})
              </span>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Portfolio Beta</span>
                <span className="font-semibold text-gray-900 dark:text-white">{riskMetrics.beta.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-gray-600 dark:text-gray-400">Correlation to BTC</span>
                <span className="font-semibold text-gray-900 dark:text-white">{riskMetrics.correlation.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Exposure Breakdown */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Risk Exposure Breakdown</h3>
          <div className="space-y-4">
            {positionRisks.map((position, index) => (
              <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-gray-900 dark:text-white">{position.symbol}</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskBgColor(position.risk)} ${getRiskColor(position.risk)}`}>
                    {position.risk} Risk
                  </span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Allocation</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{position.allocation.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 dark:text-gray-400">VaR Contribution</span>
                  <span className={`font-semibold ${getVarColor(position.var)}`}>{position.var.toFixed(2)}%</span>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${position.allocation}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stress Testing Scenarios */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Stress Testing Scenarios</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Scenario</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Portfolio Impact</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Dollar Impact</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Probability</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {riskScenarios.map((scenario, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {scenario.scenario}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${scenario.portfolioImpact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPercentage(scenario.portfolioImpact)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${scenario.portfolioImpact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(totalValue * scenario.portfolioImpact / 100)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      scenario.probability === 'Low' ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' :
                      scenario.probability === 'Medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100' :
                      'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                    }`}>
                      {scenario.probability}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk Controls & Limits */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Risk Controls & Limits</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">85%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Stop Loss Coverage</div>
            <div className="text-xs text-green-600 dark:text-green-400">Within Limits</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">1.0x</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Leverage Ratio</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">Conservative</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">15%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Max Position Size</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">Risk Limited</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">2.5h</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Avg Hold Time</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">Quick Exits</div>
          </div>
        </div>
      </div>
    </div>
  );
}
