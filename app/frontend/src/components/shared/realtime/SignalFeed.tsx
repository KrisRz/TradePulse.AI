import { useState } from 'preact/hooks';
import { Signal, SignalType } from '@/types/signals';
import { SignalCard } from './SignalCard';
import { Play, Pause, Download, Filter, RefreshCw } from 'lucide-preact';

interface SignalFeedProps {
  className?: string;
  maxSignals?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function SignalFeed({ 
  className = '', 
  maxSignals = 50, 
  autoRefresh = true, 
  refreshInterval = 5000 
}: SignalFeedProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState<SignalType | 'ALL'>('ALL');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Mock data - replace with real API calls
  const mockSignals: Signal[] = [
    {
      id: 'sig_001',
      timestamp: new Date(Date.now() - 300000), // 5 minutes ago
      symbol: 'BTCUSDT',
      type: 'BUY',
      confidence: 0.87,
      price: 43567.89,
      aiBreakdown: {
        marketRegime: {
          regime: 'trending_up',
          strength: 0.73,
          confidence: 0.85
        },
        lstmPredictions: {
          lstm_1h: { prediction: 'BUY', confidence: 0.82 },
          lstm_4h: { prediction: 'BUY', confidence: 0.91 },
          lstm_24h: { prediction: 'HOLD', confidence: 0.65 }
        },
        reversalDetection: {
          whaleVolume: { detected: true, confidence: 0.76 },
          rsiExtremes: { detected: false, confidence: 0.45 },
          divergence: { detected: false, confidence: 0.32 },
          momentum: { detected: true, confidence: 0.88 },
          supportResistance: { detected: true, confidence: 0.69 }
        },
        smartFilters: {
          rsiFilter: { passed: true, value: 58.2 },
          volumeFilter: { passed: true, value: 1.34 },
          disagreementFilter: { passed: true, value: 0.23 }
        },
        confidenceScoring: {
          baseScore: 0.75,
          volumeBoost: 0.08,
          consensusBoost: 0.04,
          finalScore: 0.87
        },
        adaptiveHoldTime: {
          minHoldTime: 45,
          maxHoldTime: 90,
          recommendedHoldTime: 67
        }
      }
    },
    {
      id: 'sig_002',
      timestamp: new Date(Date.now() - 600000), // 10 minutes ago
      symbol: 'BTCUSDT',
      type: 'SELL',
      confidence: 0.73,
      price: 43521.45,
      aiBreakdown: {
        marketRegime: {
          regime: 'sideways',
          strength: 0.45,
          confidence: 0.67
        },
        lstmPredictions: {
          lstm_1h: { prediction: 'SELL', confidence: 0.78 },
          lstm_4h: { prediction: 'SELL', confidence: 0.69 },
          lstm_24h: { prediction: 'HOLD', confidence: 0.52 }
        },
        reversalDetection: {
          whaleVolume: { detected: false, confidence: 0.34 },
          rsiExtremes: { detected: true, confidence: 0.87 },
          divergence: { detected: true, confidence: 0.73 },
          momentum: { detected: false, confidence: 0.41 },
          supportResistance: { detected: false, confidence: 0.28 }
        },
        smartFilters: {
          rsiFilter: { passed: true, value: 68.9 },
          volumeFilter: { passed: true, value: 1.12 },
          disagreementFilter: { passed: true, value: 0.19 }
        },
        confidenceScoring: {
          baseScore: 0.69,
          volumeBoost: 0.02,
          consensusBoost: 0.02,
          finalScore: 0.73
        },
        adaptiveHoldTime: {
          minHoldTime: 45,
          maxHoldTime: 90,
          recommendedHoldTime: 52
        }
      }
    },
    {
      id: 'sig_003',
      timestamp: new Date(Date.now() - 900000), // 15 minutes ago
      symbol: 'BTCUSDT',
      type: 'HOLD',
      confidence: 0.45,
      price: 43498.12,
      aiBreakdown: {
        marketRegime: {
          regime: 'sideways',
          strength: 0.23,
          confidence: 0.34
        },
        lstmPredictions: {
          lstm_1h: { prediction: 'HOLD', confidence: 0.52 },
          lstm_4h: { prediction: 'HOLD', confidence: 0.48 },
          lstm_24h: { prediction: 'HOLD', confidence: 0.39 }
        },
        reversalDetection: {
          whaleVolume: { detected: false, confidence: 0.18 },
          rsiExtremes: { detected: false, confidence: 0.23 },
          divergence: { detected: false, confidence: 0.15 },
          momentum: { detected: false, confidence: 0.31 },
          supportResistance: { detected: false, confidence: 0.42 }
        },
        smartFilters: {
          rsiFilter: { passed: true, value: 51.2 },
          volumeFilter: { passed: false, value: 0.78 },
          disagreementFilter: { passed: true, value: 0.08 }
        },
        confidenceScoring: {
          baseScore: 0.46,
          volumeBoost: -0.02,
          consensusBoost: 0.01,
          finalScore: 0.45
        },
        adaptiveHoldTime: {
          minHoldTime: 45,
          maxHoldTime: 90,
          recommendedHoldTime: 45
        }
      }
    }
  ];

  const fetchSignals = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Replace with real API call
      // const response = await fetch('/api/signals');
      // const data = await response.json();
      // setSignals(data);
      
      // Mock delay
      await new Promise(resolve => setTimeout(resolve, 500));
      setSignals(mockSignals);
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to fetch signals');
    } finally {
      setLoading(false);
    }
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  const exportSignals = () => {
    const csv = signals.map(signal => ({
      timestamp: signal.timestamp.toISOString(),
      symbol: signal.symbol,
      type: signal.type,
      confidence: signal.confidence,
      price: signal.price
    }));
    
    const csvString = [
      Object.keys(csv[0]).join(','),
      ...csv.map(row => Object.values(row).join(','))
    ].join('\n');
    
    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `signals_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredSignals = signals.filter(signal => 
    filter === 'ALL' || signal.type === filter
  ).slice(0, maxSignals);

  useEffect(() => {
    fetchSignals();
  }, []);

  useEffect(() => {
    if (!autoRefresh || isPaused) return;

    const interval = setInterval(fetchSignals, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, isPaused, refreshInterval]);

  if (loading && signals.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              AI Trading Signals
            </h2>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Filter */}
            <select
              value={filter}
              onChange={(e) => setFilter((e.target as HTMLInputElement).value as SignalType | 'ALL')}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md 
                         bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Signals</option>
              <option value="BUY">Buy Only</option>
              <option value="SELL">Sell Only</option>
              <option value="HOLD">Hold Only</option>
            </select>
            
            {/* Controls */}
            <button
              onClick={togglePause}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 
                         dark:hover:text-gray-200 transition-colors"
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? <Play size={16} /> : <Pause size={16} />}
            </button>
            
            <button
              onClick={fetchSignals}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 
                         dark:hover:text-gray-200 transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
            
            <button
              onClick={exportSignals}
              disabled={signals.length === 0}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 
                         dark:hover:text-gray-200 transition-colors disabled:opacity-50"
              title="Export CSV"
            >
              <Download size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Signal List */}
      <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 
                          rounded-lg p-4 text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
        
        {filteredSignals.length === 0 ? (
          <div className="text-center py-12">
            <Filter size={48} className="mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500 dark:text-gray-400">
              No signals found matching your filter
            </p>
          </div>
        ) : (
          filteredSignals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              showDetails={true}
              className="hover:shadow-md transition-shadow"
            />
          ))
        )}
      </div>
      
      {/* Status Bar */}
      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 
                      bg-gray-50 dark:bg-gray-800 rounded-b-lg">
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>
            {filteredSignals.length} of {signals.length} signals
            {filter !== 'ALL' && ` (${filter.toLowerCase()} only)`}
          </span>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isPaused ? 'bg-yellow-400' : 'bg-green-400'
            }`}></div>
            <span>
              {isPaused ? 'Paused' : 'Live'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
} 