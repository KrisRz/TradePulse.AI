import { Target, TrendingUp, AlertTriangle, X } from 'lucide-preact';

interface ConfidenceScoreProps {
  score: number; // 0-1 range
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showLabel?: boolean;
  showIcon?: boolean;
}

export function ConfidenceScore({ 
  score, 
  size = 'md', 
  className = '', 
  showLabel = true,
  showIcon = true
}: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);
  
  const getConfidenceLevel = () => {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    if (score >= 0.4) return 'low';
    return 'very-low';
  };

  const getConfidenceColor = () => {
    const level = getConfidenceLevel();
    switch (level) {
      case 'high':
        return 'text-green-600 dark:text-green-400';
      case 'medium':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'low':
        return 'text-orange-600 dark:text-orange-400';
      case 'very-low':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getConfidenceBgColor = () => {
    const level = getConfidenceLevel();
    switch (level) {
      case 'high':
        return 'bg-green-100 dark:bg-green-900/30';
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/30';
      case 'low':
        return 'bg-orange-100 dark:bg-orange-900/30';
      case 'very-low':
        return 'bg-red-100 dark:bg-red-900/30';
      default:
        return 'bg-gray-100 dark:bg-gray-900/30';
    }
  };

  const getProgressBarColor = () => {
    const level = getConfidenceLevel();
    switch (level) {
      case 'high':
        return 'bg-green-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-orange-500';
      case 'very-low':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getConfidenceIcon = () => {
    const level = getConfidenceLevel();
    const iconSize = size === 'sm' ? 12 : size === 'md' ? 16 : 20;
    
    switch (level) {
      case 'high':
        return <Target size={iconSize} />;
      case 'medium':
        return <TrendingUp size={iconSize} />;
      case 'low':
        return <AlertTriangle size={iconSize} />;
      case 'very-low':
        return <X size={iconSize} />;
      default:
        return <Target size={iconSize} />;
    }
  };

  const getConfidenceText = () => {
    const level = getConfidenceLevel();
    switch (level) {
      case 'high':
        return 'High';
      case 'medium':
        return 'Medium';
      case 'low':
        return 'Low';
      case 'very-low':
        return 'Very Low';
      default:
        return 'Unknown';
    }
  };

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base'
  };

  const progressHeightClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {showIcon && (
        <div className={`${getConfidenceColor()}`}>
          {getConfidenceIcon()}
        </div>
      )}
      
      <div className="flex-1">
        {showLabel && (
          <div className={`flex items-center justify-between ${sizeClasses[size]}`}>
            <span className={`font-medium ${getConfidenceColor()}`}>
              {getConfidenceText()}
            </span>
            <span className={`font-bold ${getConfidenceColor()}`}>
              {percentage}%
            </span>
          </div>
        )}
        
        <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full ${progressHeightClasses[size]} 
                        ${showLabel ? 'mt-1' : ''}`}>
          <div 
            className={`${getProgressBarColor()} ${progressHeightClasses[size]} rounded-full 
                        transition-all duration-500 ease-out`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
      
      {!showLabel && (
        <span className={`font-bold ${getConfidenceColor()} ${sizeClasses[size]}`}>
          {percentage}%
        </span>
      )}
    </div>
  );
}

interface ConfidenceScoreSimpleProps {
  score: number;
  className?: string;
}

export function ConfidenceScoreSimple({ score, className = '' }: ConfidenceScoreSimpleProps) {
  const percentage = Math.round(score * 100);
  
  const getColor = () => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400';
    if (score >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 0.4) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <span className={`font-bold ${getColor()} ${className}`}>
      {percentage}%
    </span>
  );
}

interface ConfidenceScoreBadgeProps {
  score: number;
  className?: string;
}

export function ConfidenceScoreBadge({ score, className = '' }: ConfidenceScoreBadgeProps) {
  const percentage = Math.round(score * 100);
  
  const getBadgeColor = () => {
    if (score >= 0.8) return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
    if (score >= 0.6) return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
    if (score >= 0.4) return 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300';
    return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
                     ${getBadgeColor()} ${className}`}>
      {percentage}%
    </span>
  );
} 