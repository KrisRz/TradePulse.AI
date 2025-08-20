import { useState, useEffect } from 'preact/hooks';
import { Brain, TrendingUp, TrendingDown, Eye, AlertTriangle, CheckCircle } from 'lucide-preact';
import { ConfidenceScore } from '../signals/ConfidenceScore';

interface AIConfidenceData {
  currentConfidence: number;
  trend: 'up' | 'down' | 'stable';
  lastUpdate: Date;
  prediction: 'BUY' | 'SELL' | 'HOLD';
  breakdown: {
    marketRegime: number;
    lstmConsensus: number;
    technicalIndicators: number;
    volumeAnalysis: number;
    riskAssessment: number;
  };
  historicalAccuracy: {
    last24h: number;
    last7d: number;
    last30d: number;
  };
  nextPrediction: Date;
}

interface AIConfidenceIndicatorProps {
  className?: string;
  showBreakdown?: boolean;
  refreshInterval?: number;
}

export function AIConfidenceIndicator({ 
  className = '',
  showBreakdown = true,
  refreshInterval = 10000
}: AIConfidenceIndicatorProps) {
  const [confidenceData, setConfidenceData] = useState<AIConfidenceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previousConfidence, setPreviousConfidence] = useState<number | null>(null);

  // Mock AI confidence data
  const mockConfidenceData: AIConfidenceData = {
    currentConfidence: 0.73,
    trend: 'up',
    lastUpdate: new Date(),
    prediction: 'BUY',
    breakdown: {
      marketRegime: 0.78,
      lstmConsensus: 0.82,
      technicalIndicators: 0.65,
      volumeAnalysis: 0.71,
      riskAssessment: 0.69
    },
    historicalAccuracy: {
      last24h: 0.67,
      last7d: 0.71,
      last30d: 0.68
    },
    nextPrediction: new Date(Date.now() + 300000) // 5 minutes from now
  };

  const fetchConfidenceData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Replace with real API call
      // const response = await fetch('/api/ai/confidence');
      // const data = await response.json();
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Add realistic fluctuations
      const previousData = confidenceData || mockConfidenceData;
      const fluctuation = (Math.random() - 0.5) * 0.1; // ±5% fluctuation
      const newConfidence = Math.max(0.1, Math.min(0.95, previousData.currentConfidence + fluctuation));
      
      // Determine trend
      let trend: 'up' | 'down' | 'stable' = 'stable';
      if (previousConfidence !== null) {
        if (newConfidence > previousConfidence + 0.02) trend = 'up';
        else if (newConfidence < previousConfidence - 0.02) trend = 'down';
      }
      
      // Update breakdown with some correlation
      const baseConfidence = newConfidence;
      const variation = 0.15; // Max variation from base
      
      const newData: AIConfidenceData = {
        ...mockConfidenceData,
        currentConfidence: newConfidence,
        trend: trend,
        lastUpdate: new Date(),
        prediction: newConfidence > 0.7 ? 'BUY' : newConfidence < 0.4 ? 'SELL' : 'HOLD',
        breakdown: {
          marketRegime: Math.max(0.1, Math.min(0.95, baseConfidence + (Math.random() - 0.5) * variation)),
          lstmConsensus: Math.max(0.1, Math.min(0.95, baseConfidence + (Math.random() - 0.5) * variation)),
          technicalIndicators: Math.max(0.1, Math.min(0.95, baseConfidence + (Math.random() - 0.5) * variation)),
          volumeAnalysis: Math.max(0.1, Math.min(0.95, baseConfidence + (Math.random() - 0.5) * variation)),
          riskAssessment: Math.max(0.1, Math.min(0.95, baseConfidence + (Math.random() - 0.5) * variation))
        },
        historicalAccuracy: {
          last24h: Math.max(0.5, Math.min(0.8, 0.67 + (Math.random() - 0.5) * 0.1)),
          last7d: Math.max(0.5, Math.min(0.8, 0.71 + (Math.random() - 0.5) * 0.1)),
          last30d: Math.max(0.5, Math.min(0.8, 0.68 + (Math.random() - 0.5) * 0.1))
        },
        nextPrediction: new Date(Date.now() + 300000 - Math.random() * 60000)
      };
      
      setPreviousConfidence(confidenceData?.currentConfidence || null);
      setConfidenceData(newData);
    } catch (err) {
      setError('Failed to fetch AI confidence data');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.8) return 'very-high';
    if (confidence >= 0.6) return 'high';
    if (confidence >= 0.4) return 'medium';
    if (confidence >= 0.2) return 'low';
    return 'very-low';
  };

  const getConfidenceLevelText = (confidence: number) => {
    const level = getConfidenceLevel(confidence);
    switch (level) {
      case 'very-high': return 'Very High';
      case 'high': return 'High';
      case 'medium': return 'Medium';
      case 'low': return 'Low';
      case 'very-low': return 'Very Low';
      default: return 'Unknown';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.6) return 'text-blue-600 dark:text-blue-400';
    if (confidence >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
    if (confidence >= 0.2) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getConfidenceBgColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-50 dark:bg-green-900/20';
    if (confidence >= 0.6) return 'bg-blue-50 dark:bg-blue-900/20';
    if (confidence >= 0.4) return 'bg-yellow-50 dark:bg-yellow-900/20';
    if (confidence >= 0.2) return 'bg-orange-50 dark:bg-orange-900/20';
    return 'bg-red-50 dark:bg-red-900/20';
  };

  const getPredictionColor = (prediction: string) => {
    switch (prediction) {
      case 'BUY': return 'text-green-600 dark:text-green-400';
      case 'SELL': return 'text-red-600 dark:text-red-400';
      case 'HOLD': return 'text-yellow-600 dark:text-yellow-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp size={14} className="text-green-600 dark:text-green-400" />;
      case 'down': return <TrendingDown size={14} className="text-red-600 dark:text-red-400" />;
      default: return <div className="w-3 h-3 rounded-full bg-gray-400"></div>;
    }
  };

  const formatTimeToNext = (nextTime: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((nextTime.getTime() - now.getTime()) / 1000);
    
    if (diffInSeconds <= 0) return 'Now';
    if (diffInSeconds < 60) return `${diffInSeconds}s`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
    return `${Math.floor(diffInSeconds / 3600)}h`;
  };

  useEffect(() => {
    fetchConfidenceData();
  }, []);

  useEffect(() => {
    const interval = setInterval(fetchConfidenceData, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading && !confidenceData) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 ${className}`}>
        <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
          <AlertTriangle size={16} />
          <span className="text-sm">AI Confidence Error</span>
        </div>
      </div>
    );
  }

  if (!confidenceData) return null;

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-full">
              <Brain size={20} className="text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                AI Confidence
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Updated {confidenceData.lastUpdate.toLocaleTimeString()}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {getTrendIcon(confidenceData.trend)}
            <span className="text-sm text-gray-500 dark:text-gray-400 capitalize">
              {confidenceData.trend}
            </span>
          </div>
        </div>
      </div>

      {/* Main Confidence Display */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {Math.round(confidenceData.currentConfidence * 100)}%
            </div>
            <div className="text-left">
              <div className={`text-sm font-medium ${getConfidenceColor(confidenceData.currentConfidence)}`}>
                {getConfidenceLevelText(confidenceData.currentConfidence)}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Confidence Level
              </div>
            </div>
          </div>
          
          <div className="text-right">
            <div className={`text-xl font-bold ${getPredictionColor(confidenceData.prediction)}`}>
              {confidenceData.prediction}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Current Signal
            </div>
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mb-4">
          <ConfidenceScore 
            score={confidenceData.currentConfidence} 
            size="lg" 
            showLabel={false}
            className="w-full"
          />
        </div>

        {/* Next Prediction Timer */}
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-2">
            <Eye size={14} />
            <span>Next update in {formatTimeToNext(confidenceData.nextPrediction)}</span>
          </div>
          <div className="flex items-center space-x-2">
            <CheckCircle size={14} />
            <span>24h Accuracy: {Math.round(confidenceData.historicalAccuracy.last24h * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Detailed Breakdown */}
      {showBreakdown && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">AI Components</h4>
          
          <div className="space-y-3">
            {Object.entries(confidenceData.breakdown).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                  {key.replace(/([A-Z])/g, ' $1').trim()}
                </span>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-500 ${
                        value >= 0.8 ? 'bg-green-500' :
                        value >= 0.6 ? 'bg-blue-500' :
                        value >= 0.4 ? 'bg-yellow-500' :
                        value >= 0.2 ? 'bg-orange-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${value * 100}%` }}
                    />
                  </div>
                  <span className={`text-sm font-medium ${getConfidenceColor(value)}`}>
                    {Math.round(value * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Historical Performance */}
          <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Historical Accuracy</h5>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="text-gray-500 dark:text-gray-400">24h</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {Math.round(confidenceData.historicalAccuracy.last24h * 100)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-500 dark:text-gray-400">7d</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {Math.round(confidenceData.historicalAccuracy.last7d * 100)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-500 dark:text-gray-400">30d</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {Math.round(confidenceData.historicalAccuracy.last30d * 100)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 