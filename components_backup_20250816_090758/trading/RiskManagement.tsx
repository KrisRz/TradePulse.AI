import { useState, useEffect } from 'preact/hooks';
import { 
  Shield, 
  AlertTriangle, 
  TrendingDown, 
  Target, 
  DollarSign, 
  Percent, 
  Settings, 
  Bell,
  Activity,
  PieChart,
  BarChart3,
  RefreshCw,
  CheckCircle,
  XCircle
} from 'lucide-preact';

interface RiskMetrics {
  portfolioValue: number;
  totalRisk: number;
  riskPercentage: number;
  maxDrawdown: number;
  currentDrawdown: number;
  valueAtRisk: number;
  sharpeRatio: number;
  winRate: number;
  profitFactor: number;
  maxLossStreak: number;
  currentLossStreak: number;
  avgPositionSize: number;
  largestPosition: number;
  totalPositions: number;
  dailyPnl: number;
  weeklyPnl: number;
  monthlyPnl: number;
}

interface RiskLimits {
  maxPositionSize: number;
  maxPortfolioRisk: number;
  maxDailyLoss: number;
  maxDrawdown: number;
  maxLeverage: number;
  maxOpenPositions: number;
  stopLossRequired: boolean;
  takeProfitRequired: boolean;
  riskRewardRatio: number;
}

interface RiskAlert {
  id: string;
  type: 'WARNING' | 'DANGER' | 'INFO';
  message: string;
  timestamp: Date;
  acknowledged: boolean;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface RiskManagementProps {
  userId?: string;
  showControls?: boolean;
  showAlerts?: boolean;
  onLimitUpdate?: (limits: RiskLimits) => void;
  onAlertAcknowledge?: (alertId: string) => void;
}

export default function RiskManagement({
  userId,
  showControls = true,
  showAlerts = true,
  onLimitUpdate,
  onAlertAcknowledge
}: RiskManagementProps) {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null);
  const [limits, setLimits] = useState<RiskLimits | null>(null);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedLimits, setEditedLimits] = useState<RiskLimits | null>(null);

  useEffect(() => {
    fetchRiskData();
    
    // Set up real-time updates every 30 seconds
    const interval = setInterval(fetchRiskData, 30000);
    
    return () => clearInterval(interval);
  }, [userId]);

  const fetchRiskData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Mock data for now - will be replaced with API call
      const mockMetrics: RiskMetrics = {
        portfolioValue: 12456.78,
        totalRisk: 1245.67,
        riskPercentage: 10.0,
        maxDrawdown: -8.5,
        currentDrawdown: -2.3,
        valueAtRisk: 623.45,
        sharpeRatio: 1.85,
        winRate: 68.5,
        profitFactor: 2.34,
        maxLossStreak: 3,
        currentLossStreak: 0,
        avgPositionSize: 2000,
        largestPosition: 3500,
        totalPositions: 5,
        dailyPnl: 234.56,
        weeklyPnl: 1245.67,
        monthlyPnl: 3456.78
      };

      const mockLimits: RiskLimits = {
        maxPositionSize: 5000,
        maxPortfolioRisk: 15.0,
        maxDailyLoss: 500,
        maxDrawdown: 10.0,
        maxLeverage: 10,
        maxOpenPositions: 8,
        stopLossRequired: true,
        takeProfitRequired: false,
        riskRewardRatio: 2.0
      };

      const mockAlerts: RiskAlert[] = [
        {
          id: '1',
          type: 'WARNING',
          message: 'Portfolio drawdown approaching 5% threshold',
          timestamp: new Date(Date.now() - 5 * 60 * 1000),
          acknowledged: false,
          severity: 'MEDIUM'
        },
        {
          id: '2',
          type: 'INFO',
          message: 'Daily P&L target achieved (+$200)',
          timestamp: new Date(Date.now() - 30 * 60 * 1000),
          acknowledged: false,
          severity: 'LOW'
        },
        {
          id: '3',
          type: 'DANGER',
          message: 'Large position size detected (28% of portfolio)',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
          acknowledged: true,
          severity: 'HIGH'
        }
      ];

      setTimeout(() => {
        setMetrics(mockMetrics);
        setLimits(mockLimits);
        setAlerts(mockAlerts);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch risk data');
      setLoading(false);
    }
  };

  const handleLimitEdit = () => {
    setIsEditing(true);
    setEditedLimits(limits ? { ...limits } : null);
  };

  const handleLimitSave = async () => {
    if (!editedLimits) return;
    
    try {
      await onLimitUpdate?.(editedLimits);
      setLimits(editedLimits);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update limits:', error);
    }
  };

  const handleLimitCancel = () => {
    setIsEditing(false);
    setEditedLimits(null);
  };

  const handleAlertAcknowledge = async (alertId: string) => {
    try {
      await onAlertAcknowledge?.(alertId);
      setAlerts(prev => 
        prev.map(alert => 
          alert.id === alertId 
            ? { ...alert, acknowledged: true }
            : alert
        )
      );
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const getRiskColor = (percentage: number, threshold: number = 10) => {
    if (percentage >= threshold * 0.8) return 'text-red-600 dark:text-red-400';
    if (percentage >= threshold * 0.6) return 'text-orange-600 dark:text-orange-400';
    if (percentage >= threshold * 0.4) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getRiskBgColor = (percentage: number, threshold: number = 10) => {
    if (percentage >= threshold * 0.8) return 'bg-red-100 dark:bg-red-900/20';
    if (percentage >= threshold * 0.6) return 'bg-orange-100 dark:bg-orange-900/20';
    if (percentage >= threshold * 0.4) return 'bg-yellow-100 dark:bg-yellow-900/20';
    return 'bg-green-100 dark:bg-green-900/20';
  };

  const getAlertIcon = (type: RiskAlert['type']) => {
    switch (type) {
      case 'DANGER': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'WARNING': return <AlertTriangle className="w-4 h-4 text-orange-500" />;
      case 'INFO': return <CheckCircle className="w-4 h-4 text-blue-500" />;
      default: return <Bell className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading risk data...</span>
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
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Risk Management
        </h2>
        <div className="flex items-center space-x-2">
          {showControls && (
            <button
              onClick={handleLimitEdit}
              className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Settings className="w-4 h-4 mr-2" />
              Configure Limits
            </button>
          )}
          <button
            onClick={fetchRiskData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh risk data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Risk Overview */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className={`rounded-lg p-4 ${getRiskBgColor(metrics.riskPercentage, limits?.maxPortfolioRisk || 15)}`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Portfolio Risk
                </div>
                <div className={`text-2xl font-bold ${getRiskColor(metrics.riskPercentage, limits?.maxPortfolioRisk || 15)}`}>
                  {metrics.riskPercentage.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {formatCurrency(metrics.totalRisk)} at risk
                </div>
              </div>
              <Shield className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className={`rounded-lg p-4 ${getRiskBgColor(Math.abs(metrics.currentDrawdown), limits?.maxDrawdown || 10)}`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Current Drawdown
                </div>
                <div className={`text-2xl font-bold ${getRiskColor(Math.abs(metrics.currentDrawdown), limits?.maxDrawdown || 10)}`}>
                  {formatPercent(metrics.currentDrawdown)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Max: {formatPercent(metrics.maxDrawdown)}
                </div>
              </div>
              <TrendingDown className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Value at Risk (95%)
                </div>
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {formatCurrency(metrics.valueAtRisk)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Daily VaR
                </div>
              </div>
              <Target className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Sharpe Ratio
                </div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {metrics.sharpeRatio.toFixed(2)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Risk-adjusted return
                </div>
              </div>
              <BarChart3 className="w-8 h-8 text-gray-400" />
            </div>
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {metrics && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Performance Metrics
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {metrics.winRate.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {metrics.profitFactor.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Max Loss Streak</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {metrics.maxLossStreak}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Avg Position Size</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {formatCurrency(metrics.avgPositionSize)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Largest Position</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {formatCurrency(metrics.largestPosition)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Positions</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {metrics.totalPositions}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Daily P&L</span>
                <span className={`font-medium ${
                  metrics.dailyPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(metrics.dailyPnl)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Weekly P&L</span>
                <span className={`font-medium ${
                  metrics.weeklyPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(metrics.weeklyPnl)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Monthly P&L</span>
                <span className={`font-medium ${
                  metrics.monthlyPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {formatCurrency(metrics.monthlyPnl)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Limits Configuration */}
      {showControls && limits && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Risk Limits
            </h3>
            {isEditing && (
              <div className="flex space-x-2">
                <button
                  onClick={handleLimitSave}
                  className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={handleLimitCancel}
                  className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Position Size
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={editedLimits?.maxPositionSize || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxPositionSize: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {formatCurrency(limits.maxPositionSize)}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Portfolio Risk (%)
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    step="0.1"
                    value={editedLimits?.maxPortfolioRisk || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxPortfolioRisk: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {limits.maxPortfolioRisk.toFixed(1)}%
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Daily Loss
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={editedLimits?.maxDailyLoss || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxDailyLoss: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {formatCurrency(limits.maxDailyLoss)}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Drawdown (%)
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    step="0.1"
                    value={editedLimits?.maxDrawdown || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxDrawdown: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {limits.maxDrawdown.toFixed(1)}%
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Leverage
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={editedLimits?.maxLeverage || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxLeverage: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {limits.maxLeverage}x
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Max Open Positions
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={editedLimits?.maxOpenPositions || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      maxOpenPositions: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    {limits.maxOpenPositions}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Risk-Reward Ratio
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    step="0.1"
                    value={editedLimits?.riskRewardRatio || ''}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      riskRewardRatio: parseFloat(e.currentTarget.value) || 0
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                ) : (
                  <div className="text-gray-900 dark:text-white font-medium">
                    1:{limits.riskRewardRatio.toFixed(1)}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="stopLossRequired"
                    checked={isEditing ? editedLimits?.stopLossRequired : limits.stopLossRequired}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      stopLossRequired: e.currentTarget.checked
                    })}
                    disabled={!isEditing}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="stopLossRequired" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Stop Loss Required
                  </label>
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="takeProfitRequired"
                    checked={isEditing ? editedLimits?.takeProfitRequired : limits.takeProfitRequired}
                    onChange={(e) => editedLimits && setEditedLimits({
                      ...editedLimits,
                      takeProfitRequired: e.currentTarget.checked
                    })}
                    disabled={!isEditing}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="takeProfitRequired" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Take Profit Required
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Alerts */}
      {showAlerts && alerts.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Risk Alerts
          </h3>
          
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`flex items-start justify-between p-4 rounded-lg border ${
                  alert.acknowledged 
                    ? 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 opacity-60'
                    : alert.type === 'DANGER'
                    ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                    : alert.type === 'WARNING'
                    ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800'
                    : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                }`}
              >
                <div className="flex items-start space-x-3">
                  {getAlertIcon(alert.type)}
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {alert.message}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {alert.timestamp.toLocaleString()} • {alert.severity}
                    </div>
                  </div>
                </div>
                
                {!alert.acknowledged && (
                  <button
                    onClick={() => handleAlertAcknowledge(alert.id)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 font-medium"
                  >
                    Acknowledge
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 