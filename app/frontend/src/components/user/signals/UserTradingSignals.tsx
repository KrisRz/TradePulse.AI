import { useState, useEffect } from 'preact/hooks';
import { Activity, TrendingUp, TrendingDown, Clock, Target, Brain } from 'lucide-preact';

interface TradingSignal {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  confidence: number;
  price: number;
  targetPrice: number;
  stopLoss: number;
  timestamp: string;
  status: 'active' | 'executed' | 'expired';
  aiReason: string;
}

export default function UserTradingSignals() {
  const [signals, setSignals] = useState<TradingSignal[]>([
    {
      id: '1',
      symbol: 'BTC/USDT',
      type: 'BUY',
      confidence: 87,
      price: 45250,
      targetPrice: 47000,
      stopLoss: 44000,
      timestamp: '2 min ago',
      status: 'active',
      aiReason: 'Strong bullish momentum detected with RSI oversold recovery'
    },
    {
      id: '2',
      symbol: 'ETH/USDT',
      type: 'SELL',
      confidence: 72,
      price: 2850,
      targetPrice: 2750,
      stopLoss: 2900,
      timestamp: '15 min ago',
      status: 'active',
      aiReason: 'Resistance level reached, profit-taking opportunity'
    },
    {
      id: '3',
      symbol: 'BTC/USDT',
      type: 'BUY',
      confidence: 91,
      price: 44800,
      targetPrice: 46500,
      stopLoss: 43500,
      timestamp: '1h ago',
      status: 'executed',
      aiReason: 'Golden cross formation with high volume confirmation'
    }
  ]);

  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'executed'>('all');

  useEffect(() => {
    // Simulate loading real signals data
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const filteredSignals = signals.filter(signal => 
    filter === 'all' || signal.status === filter
  );

  const activeSignals = signals.filter(s => s.status === 'active').length;
  const avgConfidence = signals.reduce((sum, s) => sum + s.confidence, 0) / signals.length;

  if (loading) {
    return (
      <div class="animate-pulse space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} class="bg-gray-200 dark:bg-gray-700 h-20 rounded-lg"></div>
          ))}
        </div>
        <div class="bg-gray-200 dark:bg-gray-700 h-96 rounded-lg"></div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      {/* Signal Stats */}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Activity class="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <div class="ml-4">
              <div class="text-blue-600 dark:text-blue-400 text-sm font-medium">Active Signals</div>
              <div class="text-2xl font-bold text-blue-900 dark:text-blue-100">
                {activeSignals}
              </div>
            </div>
          </div>
        </div>

        <div class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Brain class="h-8 w-8 text-purple-600 dark:text-purple-400" />
            <div class="ml-4">
              <div class="text-purple-600 dark:text-purple-400 text-sm font-medium">Avg Confidence</div>
              <div class="text-2xl font-bold text-purple-900 dark:text-purple-100">
                {avgConfidence.toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
          <div class="flex items-center">
            <Target class="h-8 w-8 text-green-600 dark:text-green-400" />
            <div class="ml-4">
              <div class="text-green-600 dark:text-green-400 text-sm font-medium">Success Rate</div>
              <div class="text-2xl font-bold text-green-900 dark:text-green-100">
                72.3%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Signal Filters */}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white">AI Trading Signals</h2>
          <div class="flex space-x-2">
            {(['all', 'active', 'executed'] as const).map((filterOption) => (
              <button
                key={filterOption}
                onClick={() => setFilter(filterOption)}
                class={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === filterOption
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Signals List */}
        <div class="space-y-4">
          {filteredSignals.map((signal) => (
            <div key={signal.id} class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-3 mb-2">
                    <div class="flex items-center space-x-2">
                      {signal.type === 'BUY' ? (
                        <TrendingUp class="h-5 w-5 text-green-600" />
                      ) : (
                        <TrendingDown class="h-5 w-5 text-red-600" />
                      )}
                      <span class="font-semibold text-gray-900 dark:text-white">
                        {signal.symbol}
                      </span>
                      <span class={`px-2 py-1 rounded text-xs font-medium ${
                        signal.type === 'BUY'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {signal.type}
                      </span>
                    </div>
                    
                    <div class="flex items-center space-x-2">
                      <span class={`px-2 py-1 rounded text-xs font-medium ${
                        signal.status === 'active'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : signal.status === 'executed'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                      }`}>
                        {signal.status}
                      </span>
                      
                      <div class="flex items-center">
                        <Brain class="h-4 w-4 text-purple-600 mr-1" />
                        <span class="text-sm font-medium text-purple-600 dark:text-purple-400">
                          {signal.confidence}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                    <div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">Entry Price</div>
                      <div class="text-sm font-semibold text-gray-900 dark:text-white">
                        ${signal.price.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">Target</div>
                      <div class="text-sm font-semibold text-green-600 dark:text-green-400">
                        ${signal.targetPrice.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">Stop Loss</div>
                      <div class="text-sm font-semibold text-red-600 dark:text-red-400">
                        ${signal.stopLoss.toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                    <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">AI Analysis</div>
                    <div class="text-sm text-gray-900 dark:text-white">
                      {signal.aiReason}
                    </div>
                  </div>
                </div>

                <div class="ml-4 text-right">
                  <div class="flex items-center text-xs text-gray-500 dark:text-gray-400 mb-2">
                    <Clock class="h-3 w-3 mr-1" />
                    {signal.timestamp}
                  </div>
                  
                  {signal.status === 'active' && (
                    <button class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors">
                      Execute
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredSignals.length === 0 && (
          <div class="text-center py-12">
            <Activity class="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <div class="text-gray-500 dark:text-gray-400">
              No {filter !== 'all' ? filter : ''} signals found
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
