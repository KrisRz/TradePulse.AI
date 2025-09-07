import { useState } from 'preact/hooks';
import { Signal, SignalType } from '@/types/signals';
import { ChevronDown, ChevronUp, TrendingUp, Minus, Clock, Brain } from 'lucide-preact';
import { ConfidenceScore } from './ConfidenceScore';

interface SignalCardProps {
  signal: Signal;
  showDetails?: boolean;
  className?: string;
  onSignalClick?: (signal: Signal) => void;
}

export function SignalCard({ 
  signal, 
  showDetails = false, 
  className = '', 
  onSignalClick 
}: SignalCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getSignalColor = (type: SignalType) => {
    switch (type) {
      case 'BUY':
        return 'text-green-600 dark:text-green-400';
      case 'SELL':
        return 'text-red-600 dark:text-red-400';
      case 'HOLD':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getSignalBgColor = (type: SignalType) => {
    switch (type) {
      case 'BUY':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700';
      case 'SELL':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700';
      case 'HOLD':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700';
      default:
        return 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-700';
    }
  };

  const getSignalIcon = (type: SignalType) => {
    switch (type) {
      case 'BUY':
        return <TrendingUp size={16} />;
      case 'SELL':
        return <TrendingDown size={16} />;
      case 'HOLD':
        return <Minus size={16} />;
      default:
        return <Minus size={16} />;
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return `${Math.floor(diffInMinutes / 1440)}d ago`;
  };

  const getLSTMConsensus = () => {
    const predictions = signal.aiBreakdown.lstmPredictions;
    const votes = {
      BUY: 0,
      SELL: 0,
      HOLD: 0
    };
    
    Object.values(predictions).forEach(pred => {
      votes[pred.prediction]++;
    });
    
    const total = Object.values(votes).reduce((a, b) => a + b, 0);
    const consensus = Object.entries(votes).reduce((a, b) => 
      votes[a[0]] > votes[b[0]] ? a : b
    );
    
    return {
      prediction: consensus[0],
      percentage: Math.round((consensus[1] / total) * 100)
    };
  };

  const handleCardClick = () => {
    if (onSignalClick) {
      onSignalClick(signal);
    }
  };

  const consensus = getLSTMConsensus();

  return (
    <div 
      className={`border rounded-lg p-4 ${getSignalBgColor(signal.type)} ${className} 
                  ${onSignalClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
      onClick={handleCardClick}
    >
      {/* Signal Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-full ${getSignalColor(signal.type)} 
                          ${signal.type === 'BUY' ? 'bg-green-100 dark:bg-green-800' : 
                            signal.type === 'SELL' ? 'bg-red-100 dark:bg-red-800' : 
                            'bg-yellow-100 dark:bg-yellow-800'}`}>
            {getSignalIcon(signal.type)}
          </div>
          
          <div>
            <div className="flex items-center space-x-2">
              <span className={`text-lg font-bold ${getSignalColor(signal.type)}`}>
                {signal.type}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {signal.symbol}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
              <Clock size={12} />
              <span>{formatTime(signal.timestamp)}</span>
              <span>•</span>
              <span>{formatTimeAgo(signal.timestamp)}</span>
            </div>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {formatPrice(signal.price)}
          </div>
          <ConfidenceScore 
            score={signal.confidence} 
            size="sm" 
            className="justify-end"
          />
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
        <div className="text-center">
          <div className="text-gray-500 dark:text-gray-400">Confidence</div>
          <div className="font-semibold text-gray-900 dark:text-white">
            {Math.round(signal.confidence * 100)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-gray-500 dark:text-gray-400">LSTM Consensus</div>
          <div className="font-semibold text-gray-900 dark:text-white">
            {consensus.prediction} ({consensus.percentage}%)
          </div>
        </div>
        <div className="text-center">
          <div className="text-gray-500 dark:text-gray-400">Hold Time</div>
          <div className="font-semibold text-gray-900 dark:text-white">
            {signal.aiBreakdown.adaptiveHoldTime.recommendedHoldTime}m
          </div>
        </div>
      </div>

      {/* Expandable Details */}
      {showDetails && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="w-full flex items-center justify-center space-x-2 text-sm text-gray-600 
                     dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <Brain size={14} />
          <span>AI Breakdown</span>
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      )}

      {/* Expanded AI Breakdown */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600 space-y-4">
          {/* Market Regime */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              Market Regime
            </h4>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {signal.aiBreakdown.marketRegime.regime.replace('_', ' ')}
                </span>
                <span className="text-sm font-semibold">
                  {Math.round(signal.aiBreakdown.marketRegime.confidence * 100)}%
                </span>
              </div>
              <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${signal.aiBreakdown.marketRegime.strength * 100}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* LSTM Predictions */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              LSTM Models
            </h4>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(signal.aiBreakdown.lstmPredictions).map(([model, pred]) => (
                <div key={model} className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {model.replace('lstm_', '').toUpperCase()}
                  </div>
                  <div className={`font-semibold ${getSignalColor(pred.prediction as SignalType)}`}>
                    {pred.prediction}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    {Math.round(pred.confidence * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Reversal Detection */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              Reversal Signals
            </h4>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(signal.aiBreakdown.reversalDetection).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span className={`w-2 h-2 rounded-full ${
                        value.detected ? 'bg-green-400' : 'bg-gray-400'
                      }`}></span>
                      <span className="text-xs">
                        {Math.round(value.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Smart Filters */}
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
              Smart Filters
            </h4>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
              <div className="space-y-2 text-sm">
                {Object.entries(signal.aiBreakdown.smartFilters).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-400 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        value.passed 
                          ? 'bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300' 
                          : 'bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300'
                      }`}>
                        {value.passed ? 'PASS' : 'FAIL'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {typeof value.value === 'number' ? value.value.toFixed(2) : value.value}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 