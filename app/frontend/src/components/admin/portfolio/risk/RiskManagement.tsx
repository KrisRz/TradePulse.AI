import { useState, useEffect } from 'preact/hooks';
import { Shield, AlertTriangle, BarChart3, TrendingDown, Target } from 'lucide-preact';
import type { PortfolioOverviewResponse } from '../../../../types';
import { apiClient } from '@/lib/api-client';

interface RiskData {
  metrics: {
    var_1d: number;
    var_5d: number;
    var_30d: number;
    exposure: number;
    maxDrawdown: number;
    beta: number;
    correlation: number;
    volatility: number;
    sharpeRatio: number;
    leverageRatio: number;
    portfolioHeat: number;
  };
  position_risks: Array<{
    symbol: string;
    risk_score: number;
    value_at_risk: number;
    position_size: number;
    exposure_percentage: number;
  }>;
  scenarios: Array<{
    name: string;
    probability: number;
    impact: number;
    description: string;
  }>;
  last_updated: string;
}

interface RiskManagementProps {
  portfolioData: PortfolioOverviewResponse | null;
}

export default function RiskManagement({ portfolioData }: RiskManagementProps) {
  const [riskTimeframe] = useState('24h');
  const [riskData, setRiskData] = useState<RiskData | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Extract data directly from PortfolioOverviewResponse
  const totalValue = portfolioData?.total_value || 0;
  const availableBalance = portfolioData?.cash_balance || 0;
  const activePositions = portfolioData?.active_positions || 0;

  // Fetch real risk data from backend using API client
  useEffect(() => {
    const fetchRiskData = async () => {
      try {
        const response = await apiClient.get(`/api/portfolio/virtual/risk-metrics?timeframe=${riskTimeframe}`);

        if (response.success && response.data) {
          setRiskData(response.data);
          console.log('✅ Real risk data loaded:', response.data);
          console.log('✅ Risk metrics:', response.data.metrics);
          console.log('✅ Position risks:', response.data.position_risks);
          console.log('✅ Scenarios:', response.data.scenarios);
        } else {
          console.error('❌ Failed to fetch risk data:', response.error?.message);
          setRiskData(null);
        }
      } catch (error) {
        console.error('Error fetching risk data:', error);
        setRiskData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchRiskData();
  }, [riskTimeframe]);

  // Real risk metrics from backend
  const riskMetrics = riskData?.metrics || {
    var_1d: 0,
    var_5d: 0,
    var_30d: 0,
    exposure: totalValue > 0 ? ((totalValue - availableBalance) / totalValue) * 100 : 0,
    maxDrawdown: 0,
    beta: 0,
    correlation: 0,
    volatility: 0,
    sharpeRatio: 0,
    leverageRatio: 1.0,
    portfolioHeat: 0
  };

  // Real position risk distribution from backend
  const positionRisks = riskData?.position_risks || [];

  // Real risk scenarios from backend
  const riskScenarios = riskData?.scenarios || [];

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


  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };


  // Calculate overall risk level
  const getOverallRiskLevel = () => {
    if (riskMetrics.var_1d < 2 && riskMetrics.exposure < 50) return 'Low';
    if (riskMetrics.var_1d < 5 && riskMetrics.exposure < 75) return 'Medium';
    return 'High';
  };

  const overallRisk = getOverallRiskLevel();

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading risk analysis...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (!riskData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Failed to load risk data</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">Check console for details</p>
        </div>
      </div>
    );
  }

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
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${position.risk_score > 0.7 ? 'bg-red-100 text-red-800' : position.risk_score > 0.4 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                    {position.risk_score > 0.7 ? 'High' : position.risk_score > 0.4 ? 'Medium' : 'Low'} Risk
                  </span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600 dark:text-gray-400">Allocation</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{position.exposure_percentage.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 dark:text-gray-400">Value at Risk</span>
                  <span className={`font-semibold ${position.value_at_risk > 0 ? 'text-red-600' : 'text-green-600'}`}>${position.value_at_risk.toFixed(2)}</span>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${Math.min(position.exposure_percentage, 100)}%` }}
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
                    {scenario.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${scenario.impact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {((scenario.impact / totalValue) * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${scenario.impact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(scenario.impact)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      scenario.probability < 0.1 ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' :
                      scenario.probability < 0.2 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100' :
                      'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                    }`}>
                      {(scenario.probability * 100).toFixed(0)}%
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
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {positionRisks.length > 0 ? (positionRisks.filter(p => p.risk_score < 0.5).length / positionRisks.length * 100).toFixed(0) : '0'}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Low Risk Positions</div>
            <div className="text-xs text-green-600 dark:text-green-400">
              {positionRisks.length > 0 && positionRisks.filter(p => p.risk_score < 0.5).length / positionRisks.length > 0.7 ? 'Well Managed' : 'Monitor Closely'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{riskMetrics.leverageRatio.toFixed(1)}x</div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Leverage Ratio</div>
            <div className="text-xs text-blue-600 dark:text-blue-400">
              {riskMetrics.leverageRatio <= 1.2 ? 'Conservative' : riskMetrics.leverageRatio <= 2.0 ? 'Moderate' : 'Aggressive'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {positionRisks.length > 0 ? Math.max(...positionRisks.map(p => p.exposure_percentage)).toFixed(0) : '0'}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Max Position Size</div>
            <div className="text-xs text-purple-600 dark:text-purple-400">
              {positionRisks.length > 0 && Math.max(...positionRisks.map(p => p.exposure_percentage)) < 20 ? 'Risk Limited' : 'High Exposure'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {riskMetrics.portfolioHeat > 0 ? (riskMetrics.portfolioHeat * 10).toFixed(1) : '0.0'}h
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Portfolio Heat</div>
            <div className="text-xs text-orange-600 dark:text-orange-400">
              {riskMetrics.portfolioHeat < 0.3 ? 'Cool' : riskMetrics.portfolioHeat < 0.7 ? 'Warm' : 'Hot'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
